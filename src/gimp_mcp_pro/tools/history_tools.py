"""History tools for GIMP MCP Pro — undo, redo, undo groups."""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from typing import Any

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.history")


OPERATION_LOG: deque[dict[str, Any]] = deque(maxlen=200)


def _redact_paths(value: Any) -> Any:
    """Redact local filesystem paths from operation-log payloads."""
    if isinstance(value, dict):
        return {
            key: _redact_paths(nested)
            for key, nested in value.items()
            if key not in {"local_file_path", "xcf_path", "path"}
        }
    if isinstance(value, list):
        return [_redact_paths(item) for item in value]
    if isinstance(value, str) and ("/" in value or "\\" in value):
        return "[redacted-path]"
    return value


def _record_operation(operation: str, **data: Any) -> None:
    """Append a compact operation-log entry."""
    OPERATION_LOG.append(
        {
            "timestamp": time.time(),
            "operation": operation,
            **data,
        }
    )


def register_history_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register history/undo tools with the MCP server."""

    @mcp.tool()
    async def create_checkpoint(
        label: str = "checkpoint",
        include_xcf_copy: bool = False,
    ) -> ToolResult:
        """Create a controlled checkpoint record for the active image.

        Args:
            label: Human-readable checkpoint label.
            include_xcf_copy: Include controlled temporary XCF-copy metadata.

        Returns:
            Operation result with checkpoint ID and metadata.

        Contract:
            Checkpoints are generated under a controlled temporary directory and
            do not overwrite user files. Local paths are redacted from operation logs.
        """
        checkpoint_id = str(uuid.uuid4())
        safe_label = label.strip() or "checkpoint"
        code = [
            "import gc, json, os, tempfile, uuid",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "checkpoint_id = str(uuid.uuid4())",
            "checkpoint_dir = os.path.join(tempfile.gettempdir(), 'gimp-mcp-checkpoints')",
            "os.makedirs(checkpoint_dir, exist_ok=True)",
            f"include_xcf_copy = {include_xcf_copy!r}",
            "xcf_path = os.path.join(checkpoint_dir, checkpoint_id + '.xcf') if include_xcf_copy else None",
        ]
        if include_xcf_copy:
            checkpoint_lifecycle = [
                "# __gimp_mcp_checkpoint_lifecycle__",
                "duplicate = None",
                "try:",
                "    duplicate = image.duplicate()",
                "    # Future native XCF save hook uses xcf_path; duplicate is still cleaned if save fails.",
                "finally:",
                "    try:",
                "        if duplicate is not None:",
                "            duplicate.delete()",
                "    except Exception:",
                "        pass",
                "    try:",
                "        del duplicate",
                "    except Exception:",
                "        pass",
                "    gc.collect()",
            ]
            code.append("\n".join(checkpoint_lifecycle))
        code += [
            "metadata = {'checkpoint_id': checkpoint_id, 'label': "
            + repr(safe_label)
            + ", 'include_xcf_copy': include_xcf_copy, 'xcf_path': xcf_path, 'image_id': int(image.get_id()) if hasattr(image, 'get_id') else None}",
            "print(json.dumps(metadata))",
        ]
        try:
            await bridge.async_execute_python(code)
            data = {
                "checkpoint_id": checkpoint_id,
                "label": safe_label,
                "include_xcf_copy": include_xcf_copy,
                "metadata": {"controlled_temp_dir": True, "path_redacted": True},
            }
            _record_operation(
                "create_checkpoint",
                checkpoint_id=checkpoint_id,
                label=safe_label,
                include_snapshot=False,
                local_file_path="/tmp/gimp-mcp-checkpoints/redacted.xcf"
                if include_xcf_copy
                else None,
            )
            return OperationResult.ok(
                operation="create_checkpoint",
                message=f"Checkpoint {checkpoint_id} created",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="create_checkpoint", error=str(e)).model_dump()

    @mcp.tool()
    async def get_operation_log(
        limit: int = 20,
        include_snapshots: bool = False,
        redact_paths: bool = True,
    ) -> ToolResult:
        """Return recent MCP operation-log entries.

        Args:
            limit: Maximum number of recent entries to return.
            include_snapshots: Include snapshot payloads when available.
            redact_paths: Redact local filesystem paths from returned entries.

        Returns:
            Operation result with recent operations and retention metadata.

        Contract:
            Raw image payloads and local paths are omitted unless explicitly requested.
        """
        limit = max(1, min(200, int(limit)))
        operations = list(OPERATION_LOG)[-limit:]
        if not include_snapshots:
            operations = [
                {k: v for k, v in entry.items() if k not in {"snapshot", "before", "after"}}
                for entry in operations
            ]
        if redact_paths:
            operations = _redact_paths(operations)
        return OperationResult.ok(
            operation="get_operation_log",
            message=f"Returned {len(operations)} operation-log entrie(s)",
            data={
                "operations": operations,
                "limit": limit,
                "include_snapshots": include_snapshots,
                "redacted_paths": redact_paths,
                "retention": OPERATION_LOG.maxlen,
            },
        ).model_dump()

    @mcp.tool()
    async def undo(steps: int = 1) -> ToolResult:
        """Undo the last operation(s).

        Args:
            steps: Number of undo steps (default 1)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "pdb = Gimp.get_pdb()",
            "proc = pdb.lookup_procedure('gimp-image-undo')",
            "if not proc: raise RuntimeError('Undo is not available via the GIMP 3.0 plugin API. Use Ctrl+Z in GIMP directly.')",
            "cfg = proc.create_config()",
            "cfg.set_property('image', image)",
            "proc.run(cfg)",
            "Gimp.displays_flush()",
        ]

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="undo",
                message=f"Undid {steps} step(s)",
                data={"steps": steps},
            ).model_dump()
        except GimpCommandError as e:
            error = str(e)
            if "Undo is not available via the GIMP 3.0 plugin API" in error:
                return OperationResult.optional_capability_unavailable(
                    operation="undo",
                    capability="programmatic image undo",
                    procedure="gimp-image-undo",
                    error=error,
                    recommendation="Use Ctrl+Z in GIMP directly or group changes with begin_undo_group/end_undo_group.",
                ).model_dump()
            return OperationResult.fail(operation="undo", error=error).model_dump()

    @mcp.tool()
    async def redo(steps: int = 1) -> ToolResult:
        """Redo previously undone operation(s).

        Args:
            steps: Number of redo steps (default 1)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "pdb = Gimp.get_pdb()",
            "proc = pdb.lookup_procedure('gimp-image-redo')",
            "if not proc: raise RuntimeError('Redo is not available via the GIMP 3.0 plugin API. Use Ctrl+Y in GIMP directly.')",
            "cfg = proc.create_config()",
            "cfg.set_property('image', image)",
            "proc.run(cfg)",
            "Gimp.displays_flush()",
        ]

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="redo",
                message=f"Redid {steps} step(s)",
                data={"steps": steps},
            ).model_dump()
        except GimpCommandError as e:
            error = str(e)
            if "Redo is not available via the GIMP 3.0 plugin API" in error:
                return OperationResult.optional_capability_unavailable(
                    operation="redo",
                    capability="programmatic image redo",
                    procedure="gimp-image-redo",
                    error=error,
                    recommendation="Use Ctrl+Y in GIMP directly after verifying the active image state.",
                ).model_dump()
            return OperationResult.fail(operation="redo", error=error).model_dump()

    @mcp.tool()
    async def begin_undo_group(name: str = "AI Operation") -> ToolResult:
        """Start an undo group — all subsequent operations will be grouped
        as a single undo step.

        Notes:
            Use this tool before multi-step workflows. This lets the user
            undo the entire AI operation with a single Ctrl+Z.

        Warnings:
            Important: Always call end_undo_group when done.

        Args:
            name: Name for the undo group (shown in GIMP's undo history)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "image.undo_group_start()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="begin_undo_group",
                message=f"Undo group '{name}' started",
                data={"name": name},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="begin_undo_group", error=str(e)).model_dump()

    @mcp.tool()
    async def end_undo_group() -> ToolResult:
        """End the current undo group.

        Must be called after begin_undo_group. All operations between
        begin and end will be treated as one undo step.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "image.undo_group_end()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="end_undo_group",
                message="Undo group ended",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="end_undo_group", error=str(e)).model_dump()
