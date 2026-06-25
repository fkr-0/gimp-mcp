"""PDB discovery and raw execution tools for GIMP MCP Pro.

The PDB (Procedure Database) is GIMP's registry of all available operations.
These tools let AI assistants discover what's available and use advanced
operations that don't have dedicated typed tools yet.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from gimp_mcp_pro.bridge import LONG_TIMEOUT
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.roadmap_tools import _execute_json_tool
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.pdb")

PDB_CALL_ALLOWLIST: dict[str, set[str]] = {
    "gimp-image-get-width": {"image"},
    "gimp-image-get-height": {"image"},
    "file-png-export": {"run-mode", "image", "file", "drawables"},
}


def _execute_pdb_call_code(
    procedure: str, arguments: dict[str, Any], allow_deprecated: bool, dry_run: bool
) -> list[str]:
    """Return generated code for an allowlisted typed PDB call."""
    return [
        "import json",
        "# __gimp_mcp_execute_pdb_call__",
        f"procedure = {procedure!r}",
        f"arguments = {arguments!r}",
        f"allow_deprecated = {allow_deprecated!r}",
        f"dry_run = {dry_run!r}",
        f"ALLOWED_PDB_PROCEDURES = allowed_procedures = {sorted(PDB_CALL_ALLOWLIST)!r}",
        "argument_schema_errors = []",
        "pdb = Gimp.get_pdb()",
        "if pdb is None: raise RuntimeError('PDB not available')",
        "proc = pdb.lookup_procedure(procedure)",
        "if proc is None: raise RuntimeError(f'PDB procedure not found: {procedure}')",
        "if not allow_deprecated and hasattr(proc, 'get_deprecated') and proc.get_deprecated():\n"
        "    raise RuntimeError(f'PDB procedure is deprecated: {procedure}')",
        "config = proc.create_config()",
        "for key, value in arguments.items():\n"
        "    try:\n"
        "        if value == '$active_image':\n"
        "            images = Gimp.get_images()\n"
        "            if not images: raise RuntimeError('No active image')\n"
        "            value = images[0]\n"
        "        config.set_property(key, value)\n"
        "    except Exception as exc:\n"
        "        argument_schema_errors.append({'argument': key, 'error': str(exc)})",
        "if argument_schema_errors: raise RuntimeError(json.dumps({'argument_schema_errors': argument_schema_errors}))",
        "result = {'procedure': procedure, 'arguments': list(arguments), 'allow_deprecated': allow_deprecated, 'dry_run': dry_run, 'argument_schema_errors': argument_schema_errors, 'executed': False, 'return_values': None}",
        "if not dry_run:\n"
        "    pdb_result = proc.run(config)\n"
        "    result['executed'] = True\n"
        "    result['return_values'] = str(pdb_result)",
        "print(json.dumps(result, sort_keys=True))",
    ]


def _json_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the last JSON object from bridge output."""
    for item in reversed(result.get("results", []) or []):
        if isinstance(item, dict):
            return item
        if isinstance(item, str):
            try:
                parsed = json.loads(item.strip())
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
    return {}


def register_pdb_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register PDB discovery and raw execution tools."""

    @mcp.tool()
    async def search_pdb(query: str, max_results: int = 20) -> ToolResult:
        """Search GIMP's Procedure Database for available operations.

        GIMP has thousands of procedures (filters, file operations, etc.).
        Use this to discover what's available.

        Args:
            query: Search term (e.g., "blur", "sharpen", "file-png", "color")
            max_results: Maximum results to return (default 20)

        Returns:
            List of matching procedure names.
        """
        code = [
            "import json",
            "pdb = Gimp.get_pdb()",
            "if not pdb: raise RuntimeError('PDB not available')",
            f"query = {query!r}.lower()",
            f"max_r = {max_results}",
            "names = []",
            "for probe in (query, '',):\n"
            "    try:\n"
            "        names = list(pdb.query_procedures(probe, '', '', '', '', '', '', ''))\n"
            "    except Exception:\n"
            "        names = []\n"
            "    if names:\n"
            "        break",
            "results = []",
            "for name in names:\n"
            "    if query in name.lower() and name not in results:\n"
            "        results.append(name)\n"
            "        if len(results) >= max_r: break",
            "print(json.dumps(results))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            procedures = []
            for out in result.get("results", []):
                if out and out.strip():
                    try:
                        procedures = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue

            return OperationResult.ok(
                operation="search_pdb",
                message=f"Found {len(procedures)} procedure(s) matching '{query}'",
                data={"query": query, "procedures": procedures},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="search_pdb", error=str(e)).model_dump()

    @mcp.tool()
    async def execute_pdb_call(
        procedure: str,
        arguments: dict[str, Any] | None = None,
        allow_deprecated: bool = False,
        dry_run: bool = True,
        timeout: float = 30.0,
    ) -> ToolResult:
        """Validate and optionally execute an allowlisted typed PDB procedure call.

        Args:
            procedure: PDB procedure name. Must be in the local allowlist.
            arguments: Procedure arguments keyed by property name.
            allow_deprecated: Whether deprecated procedures are allowed.
            dry_run: Validate without calling proc.run when true.
            timeout: Bridge timeout in seconds.

        Returns:
            Operation result with validation metadata and optional return values.
        """
        procedure_name = procedure.strip()
        if not procedure_name:
            return OperationResult.fail(
                operation="execute_pdb_call", error="procedure is required"
            ).model_dump()
        allowed_arguments = PDB_CALL_ALLOWLIST.get(procedure_name)
        if allowed_arguments is None:
            return OperationResult.fail(
                operation="execute_pdb_call",
                error=f"procedure is not in execute_pdb_call allowlist: {procedure_name}",
            ).model_dump()
        supplied_arguments = arguments or {}
        unknown = sorted(set(supplied_arguments) - allowed_arguments)
        if unknown:
            return OperationResult.fail(
                operation="execute_pdb_call",
                error=f"unsupported PDB argument(s): {', '.join(unknown)}",
            ).model_dump()
        try:
            response = await bridge.async_execute_python(
                _execute_pdb_call_code(
                    procedure_name, supplied_arguments, allow_deprecated, dry_run
                ),
                timeout=min(float(timeout), LONG_TIMEOUT),
            )
            data = _json_payload(response) or {
                "procedure": procedure_name,
                "arguments": list(supplied_arguments),
                "dry_run": dry_run,
                "executed": not dry_run,
            }
            return OperationResult.ok(
                operation="execute_pdb_call",
                message="PDB call validated" if dry_run else "PDB call executed",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="execute_pdb_call", error=str(e)).model_dump()

    @mcp.tool()
    async def execute_python(
        code: list[str],
        timeout_seconds: float = 30.0,
    ) -> ToolResult:
        """Execute raw Python code in GIMP's PyGObject console.

        This is the ESCAPE HATCH for operations that don't have a dedicated
        typed tool. Use typed tools whenever possible — they have better
        error handling and validation.

        The code runs in GIMP's persistent Python context:
        - Imports persist between calls
        - Variables persist between calls
        - Gimp and Gegl modules are pre-imported

        Warnings:
            Important: Always call Gimp.displays_flush() after drawing operations.
            Always call Gimp.Selection.none(image) after selection-based operations.

        Args:
            code: List of Python code strings to execute sequentially.
                  Example: ["x = 5", "print(x + 1)"]
            timeout_seconds: Timeout for execution (default 30, use longer for
                            heavy operations like filters)

        Returns:
            Result with stdout output from each line.
        """
        if not code:
            return OperationResult.fail(
                operation="execute_python", error="No code provided"
            ).model_dump()

        timeout = min(timeout_seconds, LONG_TIMEOUT)

        try:
            result = await bridge.async_execute_python(code, timeout=timeout)
            return OperationResult.ok(
                operation="execute_python",
                message="Code executed successfully",
                data={
                    "outputs": result.get("results", []),
                    "lines_executed": len(code),
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="execute_python",
                error=str(e),
                data={"gimp_traceback": e.gimp_traceback} if hasattr(e, "gimp_traceback") else None,
            ).model_dump()

    @mcp.tool()
    async def pdb_introspect_typed(
        query: str,
        include_deprecated: bool = False,
        max_results: int = 25,
    ) -> ToolResult:
        """Return typed PDB procedure metadata for safer wrapper generation.

        Args:
            query: Procedure-name search string.
            include_deprecated: Include deprecated procedures where detectable.
            max_results: Maximum procedures to return.

        Returns:
            Operation result with procedure signatures and deprecation notes.
        """
        payload = {
            "query": query,
            "include_deprecated": include_deprecated,
            "max_results": max(1, min(100, int(max_results))),
            "procedures": [],
            "signatures": [],
            "deprecation_notes": [],
        }
        return await _execute_json_tool(
            bridge,
            operation="pdb_introspect_typed",
            marker="__gimp_mcp_pdb_introspect_typed__",
            payload=payload,
            message="Typed PDB metadata inspected",
        )

    @mcp.tool()
    async def safe_python_eval(
        code: str,
        mode: str = "expression",
        timeout: float = 1.0,
        require_debug_enabled: bool = False,
    ) -> ToolResult:
        """Run restricted diagnostic Python only when explicitly debug-enabled.

        Args:
            code: Python expression or statement.
            mode: expression or statement.
            timeout: Timeout in seconds.
            require_debug_enabled: Must be true to execute this diagnostic escape hatch.

        Returns:
            Operation result with stdout/stderr/result metadata.
        """
        if not require_debug_enabled:
            return OperationResult.fail(
                operation="safe_python_eval",
                error="safe_python_eval is disabled by default; set require_debug_enabled=true",
            ).model_dump()
        normalized = mode.strip().lower()
        if normalized not in {"expression", "statement"}:
            return OperationResult.fail(
                operation="safe_python_eval", error="mode must be expression or statement"
            ).model_dump()
        payload = {
            "code": code,
            "mode": normalized,
            "timeout": timeout,
            "stdout": "",
            "stderr": "",
            "result": None,
        }
        return await _execute_json_tool(
            bridge,
            operation="safe_python_eval",
            marker="__gimp_mcp_safe_python_eval__",
            payload=payload,
            message="Safe diagnostic Python evaluated",
        )
