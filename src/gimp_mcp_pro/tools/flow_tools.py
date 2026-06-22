"""MCP lifecycle and execution tools for repeatable flows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from gimp_mcp_pro.flows.models import FlowDefinition
from gimp_mcp_pro.flows.operations import OperationRegistry, build_operation_registry
from gimp_mcp_pro.flows.runner import UNSAFE_CAPABILITIES, FlowRunner
from gimp_mcp_pro.flows.store import FlowStore
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult


def register_flow_tools(
    mcp: MCPToolRegistrar,
    bridge: AsyncToolBridge,
    *,
    store: FlowStore | None = None,
    registry_factory: Callable[[Any], OperationRegistry] = build_operation_registry,
) -> None:
    """Register explicit draft, validation, lifecycle, and execution tools."""
    flow_store = store or FlowStore()

    def runner() -> FlowRunner:
        return FlowRunner(registry_factory(bridge))

    @mcp.tool()
    async def propose_flow(definition: dict[str, Any]) -> ToolResult:
        """Save an agent-authored flow proposal as an inactive draft.

        Args:
            definition: Flow definition payload to validate and save as an inactive draft.

        Returns:
            Operation result dictionary with the stored draft flow or validation errors.
        """
        try:
            payload = dict(definition)
            payload["state"] = "draft"
            ui = dict(payload.get("ui") or {})
            ui["pinned"] = False
            payload["ui"] = ui
            flow = flow_store.save(FlowDefinition.model_validate(payload))
            return OperationResult.ok(
                operation="propose_flow",
                message=f"Flow '{flow.title}' saved as draft",
                data={"flow": flow.model_dump(mode="json")},
            ).model_dump()
        except (ValidationError, ValueError) as exc:
            return OperationResult.fail(operation="propose_flow", error=str(exc)).model_dump()

    @mcp.tool()
    async def list_flows(state: str | None = None) -> ToolResult:
        """List user-local flows, optionally filtered by lifecycle state.

        Args:
            state: Optional lifecycle state filter such as draft, validated, or active.

        Returns:
            Operation result dictionary with flow summaries and total count.
        """
        flows = [flow for flow in flow_store.list() if state is None or flow.state == state]
        summaries = [
            {
                "id": flow.id,
                "title": flow.title,
                "state": flow.state,
                "pinned": flow.ui.pinned,
                "capabilities": flow.capabilities,
            }
            for flow in flows
        ]
        return OperationResult.ok(
            operation="list_flows", data={"flows": summaries, "count": len(summaries)}
        ).model_dump()

    @mcp.tool()
    async def get_flow(flow_id: str) -> ToolResult:
        """Return one complete flow definition.

        Args:
            flow_id: Identifier of the flow to return.

        Returns:
            Operation result dictionary with the complete flow definition or an error.
        """
        try:
            flow = flow_store.get(flow_id)
            return OperationResult.ok(
                operation="get_flow", data={"flow": flow.model_dump(mode="json")}
            ).model_dump()
        except KeyError as exc:
            return OperationResult.fail(operation="get_flow", error=str(exc)).model_dump()

    @mcp.tool()
    async def validate_flow(flow_id: str) -> ToolResult:
        """Statically validate operation names and arguments, then mark valid drafts.

        Args:
            flow_id: Identifier of the flow to validate.

        Returns:
            Operation result dictionary with validation status, errors, and updated flow metadata.
        """
        try:
            flow = flow_store.get(flow_id)
            errors = runner().validate(flow)
            if errors:
                return OperationResult.fail(
                    operation="validate_flow",
                    error="; ".join(errors),
                    data={"valid": False, "errors": errors},
                ).model_dump()
            if flow.state == "draft":
                flow = flow_store.set_state(flow.id, "validated")
            return OperationResult.ok(
                operation="validate_flow",
                message="Flow is valid",
                data={"valid": True, "flow": flow.model_dump(mode="json")},
            ).model_dump()
        except KeyError as exc:
            return OperationResult.fail(operation="validate_flow", error=str(exc)).model_dump()

    @mcp.tool()
    async def activate_flow(flow_id: str, confirm_unsafe: bool = False) -> ToolResult:
        """Explicitly activate a validated flow.

        Args:
            flow_id: Identifier of the validated flow to activate.
            confirm_unsafe: True confirms activation of flows with unsafe capabilities.

        Returns:
            Operation result dictionary with the activated flow or safety/validation errors.
        """
        try:
            flow = flow_store.get(flow_id)
            unsafe = bool(set(flow.capabilities) & UNSAFE_CAPABILITIES)
            if unsafe and not confirm_unsafe:
                return OperationResult.fail(
                    operation="activate_flow",
                    error="unsafe flow activation requires confirm_unsafe=true",
                    data={"capabilities": flow.capabilities},
                ).model_dump()
            flow = flow_store.set_state(flow_id, "active")
            return OperationResult.ok(
                operation="activate_flow", data={"flow": flow.model_dump(mode="json")}
            ).model_dump()
        except (KeyError, ValueError) as exc:
            return OperationResult.fail(operation="activate_flow", error=str(exc)).model_dump()

    @mcp.tool()
    async def deactivate_flow(flow_id: str) -> ToolResult:
        """Return an active flow to validated state and unpin it.

        Args:
            flow_id: Identifier of the active flow to deactivate.

        Returns:
            Operation result dictionary with the deactivated flow or an error.
        """
        try:
            flow_store.set_pinned(flow_id, False)
            flow = flow_store.set_state(flow_id, "validated")
            return OperationResult.ok(
                operation="deactivate_flow", data={"flow": flow.model_dump(mode="json")}
            ).model_dump()
        except (KeyError, ValueError) as exc:
            return OperationResult.fail(operation="deactivate_flow", error=str(exc)).model_dump()

    @mcp.tool()
    async def pin_flow(flow_id: str) -> ToolResult:
        """Pin an active flow into GIMP's Repeatable Flows menu.

        Args:
            flow_id: Identifier of the active flow to pin.

        Returns:
            Operation result dictionary with the pinned flow or an error.
        """
        try:
            flow = flow_store.set_pinned(flow_id, True)
            return OperationResult.ok(
                operation="pin_flow", data={"flow": flow.model_dump(mode="json")}
            ).model_dump()
        except (KeyError, ValueError) as exc:
            return OperationResult.fail(operation="pin_flow", error=str(exc)).model_dump()

    @mcp.tool()
    async def unpin_flow(flow_id: str) -> ToolResult:
        """Remove a flow's direct GIMP menu entry.

        Args:
            flow_id: Identifier of the flow to unpin.

        Returns:
            Operation result dictionary with the unpinned flow or an error.
        """
        try:
            flow = flow_store.set_pinned(flow_id, False)
            return OperationResult.ok(
                operation="unpin_flow", data={"flow": flow.model_dump(mode="json")}
            ).model_dump()
        except (KeyError, ValueError) as exc:
            return OperationResult.fail(operation="unpin_flow", error=str(exc)).model_dump()

    @mcp.tool()
    async def run_flow(
        flow_id: str,
        parameters: dict[str, Any] | None = None,
        confirm_unsafe: bool = False,
        checkpoint_decision: str = "commit",
    ) -> ToolResult:
        """Execute a validated or active flow through the shared operation registry.

        Args:
            flow_id: Identifier of the validated or active flow to execute.
            parameters: Optional runtime parameter values for the flow.
            confirm_unsafe: True confirms execution of flows with unsafe capabilities.
            checkpoint_decision: Transaction checkpoint decision, usually commit or rollback.

        Returns:
            Operation result dictionary with the flow run payload or execution error.
        """
        try:
            flow = flow_store.get(flow_id)
            if flow.state == "draft":
                return OperationResult.fail(
                    operation="run_flow", error="flow must be validated before execution"
                ).model_dump()
            run = await runner().run(
                flow,
                parameters or {},
                confirm_unsafe=confirm_unsafe,
                checkpoint_decision=checkpoint_decision,
            )
            if run["status"] == "error":
                return OperationResult.fail(
                    operation="run_flow", error=run.get("error", "flow failed"), data={"run": run}
                ).model_dump()
            return OperationResult.ok(
                operation="run_flow", message=f"Flow '{flow.title}' completed", data={"run": run}
            ).model_dump()
        except (KeyError, ValueError, PermissionError) as exc:
            return OperationResult.fail(operation="run_flow", error=str(exc)).model_dump()
