"""Agent-oriented async transaction tools for safe GIMP operation.

Observation, target-resolution, and capability first-wave tools live in
``inspect_tools`` and ``target_tools``. This module contributes the missing
transaction primitives from the first-wave roadmap.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

IMPLEMENTED_AGENT_FEATURES: tuple[dict[str, str], ...] = (
    {
        "id": "FEAT-001",
        "name": "observe_document_state",
        "status": "in_progress",
        "module": "inspect_tools",
    },
    {
        "id": "FEAT-002",
        "name": "get_layer_tree_detailed",
        "status": "in_progress",
        "module": "inspect_tools",
    },
    {"id": "FEAT-007", "name": "resolve_target", "status": "in_progress", "module": "target_tools"},
    {
        "id": "FEAT-008",
        "name": "validate_targets",
        "status": "in_progress",
        "module": "target_tools",
    },
    {
        "id": "FEAT-010",
        "name": "begin_edit_transaction",
        "status": "in_progress",
        "module": "agent_tools",
    },
    {
        "id": "FEAT-011",
        "name": "end_edit_transaction",
        "status": "in_progress",
        "module": "agent_tools",
    },
    {
        "id": "FEAT-012",
        "name": "rollback_transaction",
        "status": "in_progress",
        "module": "agent_tools",
    },
    {
        "id": "FEAT-045",
        "name": "session_capabilities",
        "status": "in_progress",
        "module": "inspect_tools",
    },
)


def _success_payload(result: dict[str, Any], default: Any) -> Any:
    """Return a plug-in success payload or raise a bridge-style error."""
    if result.get("status") != "success":
        raise GimpCommandError(result.get("error", "GIMP command failed"), command="agent_tool")
    return result.get("results", default)


def _json_from_result(result: dict[str, Any], *, operation: str) -> dict[str, Any]:
    """Decode a JSON object printed by a generated GIMP-side snippet."""
    payload = _success_payload(result, [])
    if isinstance(payload, dict):
        return payload
    raw = payload[-1] if isinstance(payload, list) and payload else payload
    if not isinstance(raw, str):
        raise GimpCommandError(f"{operation} returned non-JSON payload: {raw!r}", command=operation)
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise GimpCommandError(
            f"{operation} returned JSON {type(decoded).__name__}, expected object",
            command=operation,
        )
    return decoded


def _active_image_selector_code() -> list[str]:
    """Build GIMP-side code that selects the current active image."""
    return [
        "from gi.repository import Gimp",
        "images = list(Gimp.get_images())",
        "if not images: raise RuntimeError('No images are open in GIMP')",
        "image = images[0]",
    ]


def register_agent_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register agent-oriented transaction tools with the MCP server."""
    transactions: dict[str, dict[str, Any]] = {}

    @mcp.tool()
    async def begin_edit_transaction(
        label: str = "AI edit transaction",
        capture_before_state: bool = False,
    ) -> ToolResult:
        """Begin a reversible edit transaction backed by a GIMP undo group.

        The returned transaction ID can be passed to ``end_edit_transaction`` or
        ``rollback_transaction``. The transaction is also useful audit metadata
        for an LLM agent planning multi-step edits.

        Args:
            label: Human-readable transaction label for logs and result metadata.
            capture_before_state: Include active image metadata in the result.

        Returns:
            Operation result with transaction ID, undo-group state, and optional before-state metadata.
        """
        transaction_id = f"txn-{uuid.uuid4().hex[:12]}"
        code = [
            "# gimp-mcp-pro:agent:begin_edit_transaction",
            "import json",
            *_active_image_selector_code(),
            "image.undo_group_start()",
            "result = {'image_id': image.get_id() if hasattr(image, 'get_id') else id(image), 'undo_group_started': True}",
            "print(json.dumps(result))",
        ]
        try:
            data = _json_from_result(
                await bridge.async_execute_python(code),
                operation="begin_edit_transaction",
            )
            before_state = None
            if capture_before_state:
                before_state = _success_payload(await bridge.async_get_image_metadata(), {})
            transactions[transaction_id] = {
                "label": label,
                "status": "active",
                "image_id": data.get("image_id"),
                "before_state": before_state,
            }
            return OperationResult.ok(
                operation="begin_edit_transaction",
                message=f"Edit transaction '{label}' started",
                data={
                    "transaction_id": transaction_id,
                    "label": label,
                    "tracked": True,
                    "before_state": before_state,
                    "feature_id": "FEAT-010",
                    **data,
                },
            ).model_dump()
        except (GimpCommandError, json.JSONDecodeError) as e:
            return OperationResult.fail(
                operation="begin_edit_transaction", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def end_edit_transaction(
        transaction_id: str | None = None,
        require_known: bool = False,
    ) -> ToolResult:
        """End a tracked or best-effort GIMP undo transaction.

        Args:
            transaction_id: Optional ID returned by begin_edit_transaction.
            require_known: Fail before touching GIMP when the transaction ID is not tracked.

        Returns:
            Operation result with tracking and undo-group closure metadata.
        """
        txn = transactions.get(transaction_id or "")
        if require_known and txn is None:
            return OperationResult.fail(
                operation="end_edit_transaction",
                error="transaction_id is unknown",
                data={"transaction_id": transaction_id},
            ).model_dump()
        code = [
            "# gimp-mcp-pro:agent:end_edit_transaction",
            "import json",
            *_active_image_selector_code(),
            "image.undo_group_end()",
            "print(json.dumps({'undo_group_ended': True}))",
        ]
        try:
            data = _json_from_result(
                await bridge.async_execute_python(code),
                operation="end_edit_transaction",
            )
            if txn is not None:
                txn["status"] = "committed"
            return OperationResult.ok(
                operation="end_edit_transaction",
                message="Edit transaction ended",
                data={
                    "transaction_id": transaction_id,
                    "tracked": txn is not None,
                    "feature_id": "FEAT-011",
                    **data,
                },
            ).model_dump()
        except (GimpCommandError, json.JSONDecodeError) as e:
            return OperationResult.fail(operation="end_edit_transaction", error=str(e)).model_dump()

    @mcp.tool()
    async def rollback_transaction(
        transaction_id: str | None = None,
        require_known: bool = False,
    ) -> ToolResult:
        """Rollback a transaction using GIMP undo where available.

        Args:
            transaction_id: Optional ID returned by begin_edit_transaction.
            require_known: Fail before touching GIMP when the transaction ID is not tracked.

        Returns:
            Operation result with tracking, undo-group, and rollback metadata.
        """
        txn = transactions.get(transaction_id or "")
        if require_known and txn is None:
            return OperationResult.fail(
                operation="rollback_transaction",
                error="transaction_id is unknown",
                data={"transaction_id": transaction_id},
            ).model_dump()
        code = [
            "# gimp-mcp-pro:agent:rollback_transaction",
            "import json",
            *_active_image_selector_code(),
            "ended = False",
            "try:",
            "    image.undo_group_end(); ended = True",
            "except Exception:",
            "    ended = False",
            "rolled_back = False",
            "if hasattr(image, 'undo'):",
            "    image.undo(); rolled_back = True",
            "else:",
            "    pdb = Gimp.get_pdb()",
            "    proc = pdb.lookup_procedure('gimp-image-undo') if pdb else None",
            "    if proc:",
            "        cfg = proc.create_config(); cfg.set_property('image', image); proc.run(cfg); rolled_back = True",
            "if not rolled_back: raise RuntimeError('Programmatic rollback is unavailable in this GIMP profile')",
            "Gimp.displays_flush()",
            "print(json.dumps({'undo_group_ended': ended, 'rolled_back': rolled_back}))",
        ]
        try:
            data = _json_from_result(
                await bridge.async_execute_python(code),
                operation="rollback_transaction",
            )
            if txn is not None:
                txn["status"] = "rolled_back"
            return OperationResult.ok(
                operation="rollback_transaction",
                message="Edit transaction rolled back",
                data={
                    "transaction_id": transaction_id,
                    "tracked": txn is not None,
                    "feature_id": "FEAT-012",
                    **data,
                },
            ).model_dump()
        except (GimpCommandError, json.JSONDecodeError) as e:
            return OperationResult.fail(operation="rollback_transaction", error=str(e)).model_dump()
