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

MAX_OPEN_TRANSACTIONS = 32


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


def _transaction_image_selector_code(image_id: Any | None) -> list[str]:
    """Build GIMP-side code selecting the image that owns a transaction."""
    if image_id is None:
        return _active_image_selector_code()
    return [
        "from gi.repository import Gimp",
        f"target_image_id = {json.dumps(image_id)}",
        "images = list(Gimp.get_images())",
        "image = next((candidate for candidate in images if (candidate.get_id() if hasattr(candidate, 'get_id') else id(candidate)) == target_image_id), None)",
        "if image is None: raise RuntimeError(f'Transaction image {target_image_id} is no longer open')",
    ]


def _rollback_code(image_id: Any | None) -> list[str]:
    """Build one image-targeted rollback snippet."""
    return [
        "# gimp-mcp-pro:agent:rollback_transaction",
        "import json",
        *_transaction_image_selector_code(image_id),
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
        "print(json.dumps({'undo_group_ended': ended, 'rolled_back': rolled_back, 'image_id': target_image_id if 'target_image_id' in globals() else (image.get_id() if hasattr(image, 'get_id') else id(image))}))",
    ]


def register_agent_tools(
    mcp: MCPToolRegistrar,
    bridge: AsyncToolBridge,
    *,
    max_open_transactions: int = MAX_OPEN_TRANSACTIONS,
) -> None:
    """Register agent-oriented transaction tools with the MCP server."""
    if max_open_transactions < 1:
        raise ValueError("max_open_transactions must be at least 1")
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
        active_count = sum(txn.get("status") == "active" for txn in transactions.values())
        if active_count >= max_open_transactions:
            return OperationResult.fail(
                operation="begin_edit_transaction",
                error=(
                    "too many open edit transactions; close one or call "
                    "rollback_transaction(recover_all=true)"
                ),
                data={
                    "open_transaction_count": active_count,
                    "max_open_transactions": max_open_transactions,
                },
            ).model_dump()
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
                "started_order": len(transactions),
            }
            return OperationResult.ok(
                operation="begin_edit_transaction",
                message=f"Edit transaction '{label}' started",
                data={
                    "transaction_id": transaction_id,
                    "label": label,
                    "tracked": True,
                    "open_transaction_count": active_count + 1,
                    "max_open_transactions": max_open_transactions,
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
            *_transaction_image_selector_code(txn.get("image_id") if txn else None),
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
                transactions.pop(transaction_id or "", None)
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
        recover_all: bool = False,
    ) -> ToolResult:
        """Rollback a transaction using GIMP undo where available.

        Args:
            transaction_id: Optional ID returned by begin_edit_transaction.
            require_known: Fail before touching GIMP when the transaction ID is not tracked.
            recover_all: Roll back and clear all tracked open transactions in LIFO order.

        Returns:
            Operation result with tracking, undo-group, and rollback metadata.
        """
        requested_recovery_ids: list[str] = []
        if recover_all:
            requested_recovery_ids = [
                item[0]
                for item in sorted(
                    transactions.items(),
                    key=lambda pair: int(pair[1].get("started_order", 0)),
                    reverse=True,
                )
                if item[1].get("status") == "active"
            ]
            if not requested_recovery_ids:
                return OperationResult.ok(
                    operation="rollback_transaction",
                    message="No open edit transactions to recover",
                    data={
                        "transaction_id": None,
                        "tracked": False,
                        "recovered_transaction_ids": [],
                        "failed_transaction_ids": [],
                        "open_transaction_count": len(transactions),
                        "feature_id": "FEAT-012",
                        "rolled_back": False,
                    },
                ).model_dump()
            recovered_transaction_ids: list[str] = []
            failures: list[dict[str, str]] = []
            last_data: dict[str, Any] = {}
            for recovered_id in requested_recovery_ids:
                recovered_txn = transactions[recovered_id]
                try:
                    last_data = _json_from_result(
                        await bridge.async_execute_python(
                            _rollback_code(recovered_txn.get("image_id"))
                        ),
                        operation="rollback_transaction",
                    )
                except (GimpCommandError, json.JSONDecodeError, ValueError, TypeError) as e:
                    failures.append({"transaction_id": recovered_id, "error": str(e)})
                    break
                recovered_transaction_ids.append(recovered_id)
                transactions.pop(recovered_id, None)

            recovery_data = {
                "transaction_id": requested_recovery_ids[0],
                "tracked": bool(recovered_transaction_ids),
                "recovered_transaction_ids": recovered_transaction_ids,
                "failed_transaction_ids": [failure["transaction_id"] for failure in failures],
                "failures": failures,
                "open_transaction_count": len(transactions),
                "feature_id": "FEAT-012",
                **last_data,
            }
            if failures:
                return OperationResult.fail(
                    operation="rollback_transaction",
                    error="failed to recover all open edit transactions",
                    data=recovery_data,
                ).model_dump()
            return OperationResult.ok(
                operation="rollback_transaction",
                message="Open edit transactions recovered",
                data=recovery_data,
            ).model_dump()

        txn = transactions.get(transaction_id or "")
        if require_known and txn is None:
            return OperationResult.fail(
                operation="rollback_transaction",
                error="transaction_id is unknown",
                data={"transaction_id": transaction_id},
            ).model_dump()
        code = _rollback_code(txn.get("image_id") if txn else None)
        try:
            data = _json_from_result(
                await bridge.async_execute_python(code),
                operation="rollback_transaction",
            )
            if txn is not None:
                txn["status"] = "rolled_back"
                transactions.pop(transaction_id or "", None)
            return OperationResult.ok(
                operation="rollback_transaction",
                message="Edit transaction rolled back"
                if not recover_all
                else "Open edit transactions recovered",
                data={
                    "transaction_id": transaction_id,
                    "tracked": txn is not None,
                    "recovered_transaction_ids": [transaction_id] if txn is not None else [],
                    "failed_transaction_ids": [],
                    "open_transaction_count": len(transactions),
                    "feature_id": "FEAT-012",
                    **data,
                },
            ).model_dump()
        except (GimpCommandError, json.JSONDecodeError) as e:
            return OperationResult.fail(operation="rollback_transaction", error=str(e)).model_dump()
