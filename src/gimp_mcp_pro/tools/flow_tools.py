"""MCP lifecycle and execution tools for repeatable flows."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from gimp_mcp_pro.flows.models import FlowDefinition
from gimp_mcp_pro.flows.operations import OperationRegistry, build_operation_registry
from gimp_mcp_pro.flows.runner import UNSAFE_CAPABILITIES, FlowRunner
from gimp_mcp_pro.flows.store import FlowStore
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult

MACRO_BLOCKED_TOOLS = {
    "execute_python",
    "dry_run_macro",
    "run_macro_transaction",
    "run_flow",
}


def _macro_flow(steps: list[dict[str, Any]], title: str) -> FlowDefinition:
    return FlowDefinition.model_validate(
        {
            "id": "macro-transaction",
            "title": title.strip() or "MCP Macro Transaction",
            "review_policy": "none",
            "phases": [{"id": "main", "steps": steps}],
        }
    )


def _macro_policy_failures(flow: FlowDefinition) -> list[str]:
    failures: list[str] = []
    for phase in flow.phases:
        for _index, step in enumerate(phase.steps):
            if step.tool in MACRO_BLOCKED_TOOLS:
                failures.append(f"unsafe tool {step.tool} requires confirm_unsafe=true")
    return failures


def _validate_required_arguments(flow: FlowDefinition, operations: OperationRegistry) -> list[str]:
    failures: list[str] = []
    for phase in flow.phases:
        for index, step in enumerate(phase.steps):
            try:
                operation = operations.get(step.tool)
            except KeyError:
                continue
            signature = inspect.signature(operation)
            for name, parameter in signature.parameters.items():
                if parameter.kind in {
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                }:
                    continue
                if parameter.default is not inspect.Parameter.empty:
                    continue
                if name not in step.arguments:
                    failures.append(
                        f"step {index} tool {step.tool} missing required argument {name}"
                    )
    return failures


def _macro_failures(flow: FlowDefinition, operations: OperationRegistry) -> list[str]:
    policy = _macro_policy_failures(flow)
    return (
        FlowRunner(operations).validate(flow)
        + policy
        + _validate_required_arguments(flow, operations)
    )


def _macro_failure_objects(failures: list[str]) -> list[dict[str, Any]]:
    return [{"error": failure} for failure in failures]


def _macro_predicted_changes(flow: FlowDefinition) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for phase in flow.phases:
        for index, step in enumerate(phase.steps):
            changes.append({"step": index, "tool": step.tool, "arguments": step.arguments})
    return changes


def _macro_resolved_targets(flow: FlowDefinition) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for phase in flow.phases:
        for index, step in enumerate(phase.steps):
            for key, target_type in (
                ("layer_index", "layer"),
                ("layer_id", "layer"),
                ("path_name", "path"),
                ("channel_name", "channel"),
            ):
                if key in step.arguments:
                    targets.append(
                        {
                            "step": index,
                            "tool": step.tool,
                            "target_type": target_type,
                            "selector": {key: step.arguments[key]},
                        }
                    )
    return targets


def _macro_transaction_id(run: dict[str, Any]) -> str | None:
    phases = run.get("phases")
    if isinstance(phases, list) and phases:
        first = phases[0]
        if isinstance(first, dict):
            value = first.get("transaction_id")
            return str(value) if value is not None else None
    return None


def _macro_step_results(run: dict[str, Any]) -> list[dict[str, Any]]:
    steps = run.get("steps")
    if not isinstance(steps, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in steps:
        if not isinstance(item, dict) or item.get("status") == "skipped":
            continue
        normalized.append(
            {
                "step": item.get("index", item.get("step")),
                "tool": item.get("tool"),
                "arguments": item.get("arguments", {}),
                "status": item.get("status"),
                "result": item.get("result"),
            }
        )
    return normalized


def _macro_rolled_back(run: dict[str, Any]) -> bool:
    phases = run.get("phases")
    if isinstance(phases, list):
        return any(
            isinstance(phase, dict) and phase.get("status") == "rolled-back" for phase in phases
        )
    return run.get("status") == "rolled-back"


def _tool_succeeded(result: dict[str, Any]) -> bool:
    if "success" in result:
        return bool(result["success"])
    return result.get("status", "success") in {"success", "ok"}


async def _capture_macro_state(operations: OperationRegistry) -> dict[str, Any] | None:
    if "observe_document_state" not in operations.names():
        return None
    result = await operations.get("observe_document_state")(
        include_thumbnail=True, include_layer_previews=False, max_preview_size=256
    )
    return result if isinstance(result, dict) else {"result": result}


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

    @mcp.tool()
    async def dry_run_macro(steps: list[dict[str, Any]]) -> ToolResult:
        """Validate a typed multi-step macro without mutating GIMP state.

        Args:
            steps: Ordered MCP tool steps with tool names and argument dictionaries.

        Returns:
            Operation result dictionary with validity, predicted changes, resolved targets, and failures.
        """
        try:
            flow = _macro_flow(steps, "Dry Run Macro")
            operations = registry_factory(bridge)
            failures = _macro_failures(flow, operations)
            data = {
                "valid": not failures,
                "resolved_targets": _macro_resolved_targets(flow) if not failures else [],
                "predicted_changes": _macro_predicted_changes(flow) if not failures else [],
                "failures": _macro_failure_objects(failures),
            }
            return OperationResult.ok(
                operation="dry_run_macro",
                message="Macro is valid" if not failures else "Macro validation failed",
                data=data,
            ).model_dump()
        except (ValidationError, ValueError) as exc:
            return OperationResult.fail(
                operation="dry_run_macro",
                error=str(exc),
                data={
                    "valid": False,
                    "resolved_targets": [],
                    "predicted_changes": [],
                    "failures": [{"error": str(exc)}],
                },
            ).model_dump()

    @mcp.tool()
    async def run_macro_transaction(
        steps: list[dict[str, Any]],
        transaction_label: str = "MCP Macro Transaction",
        rollback_on_failure: bool = True,
        capture_before_after: bool = False,
        preconditions: list[dict[str, Any]] | None = None,
        postconditions: list[dict[str, Any]] | None = None,
    ) -> ToolResult:
        """Execute a typed multi-step macro as one fail-safe transaction.

        Args:
            steps: Ordered MCP tool steps with tool names and argument dictionaries.
            transaction_label: Human-readable label for the undo/transaction phase.
            rollback_on_failure: Must remain true so macro execution is atomic.
            capture_before_after: Capture document observations before and after execution when available.
            preconditions: Optional image-state assertions checked before opening the transaction.
            postconditions: Optional image-state assertions executed as the final transactional step; failure rolls back all edits.

        Returns:
            Operation result dictionary with transaction id, step results, rollback status, and evidence.
        """
        if not rollback_on_failure:
            return OperationResult.fail(
                operation="run_macro_transaction",
                error="rollback_on_failure=false is not supported; macro transactions are fail-safe",
                data={"rolled_back": False, "step_results": []},
            ).model_dump()
        try:
            operations = registry_factory(bridge)
            precondition_result = None
            if preconditions:
                if "assert_image_state" not in operations.names():
                    return OperationResult.fail(
                        operation="run_macro_transaction",
                        error="preconditions require assert_image_state",
                        data={"validation_stage": "preconditions", "rolled_back": False},
                    ).model_dump()
                precondition_result = await operations.get("assert_image_state")(
                    assertions=preconditions
                )
                if not _tool_succeeded(precondition_result):
                    return OperationResult.fail(
                        operation="run_macro_transaction",
                        error=precondition_result.get("error", "macro preconditions failed"),
                        data={
                            "validation_stage": "preconditions",
                            "precondition_result": precondition_result,
                            "transaction_id": None,
                            "step_results": [],
                            "rolled_back": False,
                        },
                    ).model_dump()

            guarded_steps = list(steps)
            if postconditions:
                guarded_steps.append(
                    {
                        "tool": "assert_image_state",
                        "arguments": {"assertions": postconditions},
                    }
                )
            flow = _macro_flow(guarded_steps, transaction_label)
            failures = _macro_failures(flow, operations)
            if failures:
                return OperationResult.fail(
                    operation="run_macro_transaction",
                    error="macro validation failed",
                    data={
                        "valid": False,
                        "failures": _macro_failure_objects(failures),
                        "transaction_id": None,
                        "step_results": [],
                        "rolled_back": False,
                    },
                ).model_dump()

            before = await _capture_macro_state(operations) if capture_before_after else None
            run = await FlowRunner(operations).run(flow, {}, confirm_unsafe=False)
            after = await _capture_macro_state(operations) if capture_before_after else None
            rolled_back = _macro_rolled_back(run)
            data = {
                "transaction_id": _macro_transaction_id(run),
                "step_results": _macro_step_results(run),
                "rolled_back": rolled_back,
                "run": run,
                "precondition_result": precondition_result,
                "postconditions_requested": len(postconditions or []),
            }
            if capture_before_after:
                data["evidence"] = {
                    "captured": before is not None or after is not None,
                    "before": before,
                    "after": after,
                }
            if run.get("status") == "error":
                return OperationResult.fail(
                    operation="run_macro_transaction",
                    error=run.get("error", "macro transaction failed"),
                    data=data,
                ).model_dump()
            return OperationResult.ok(
                operation="run_macro_transaction",
                message="Macro transaction completed",
                data=data,
            ).model_dump()
        except (ValidationError, ValueError, PermissionError) as exc:
            return OperationResult.fail(
                operation="run_macro_transaction",
                error=str(exc),
                data={"transaction_id": None, "step_results": [], "rolled_back": False},
            ).model_dump()
