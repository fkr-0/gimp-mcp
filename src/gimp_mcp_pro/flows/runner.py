"""Validated execution of declarative repeatable flows."""

from __future__ import annotations

import inspect
import re
import time
from typing import Any

from gimp_mcp_pro.flows.models import FlowDefinition, content_hash
from gimp_mcp_pro.flows.operations import OperationRegistry

EXACT_REFERENCE_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
REFERENCE_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
UNSAFE_CAPABILITIES = {"arbitrary-code", "pdb"}


class FlowRunner:
    """Execute flow steps through a captured operation registry."""

    def __init__(self, operations: OperationRegistry) -> None:
        self.operations = operations

    def validate(self, flow: FlowDefinition) -> list[str]:
        errors: list[str] = []
        for phase in flow.phases:
            for step in phase.steps:
                try:
                    operation = self.operations.get(step.tool)
                except KeyError:
                    errors.append(f"unknown tool: {step.tool}")
                    continue
                signature = inspect.signature(operation)
                accepts_kwargs = any(
                    parameter.kind == inspect.Parameter.VAR_KEYWORD
                    for parameter in signature.parameters.values()
                )
                if not accepts_kwargs:
                    for argument in step.arguments:
                        if argument not in signature.parameters:
                            errors.append(f"tool {step.tool} has no argument {argument}")
        return errors

    async def run(
        self,
        flow: FlowDefinition,
        parameters: dict[str, Any] | None = None,
        *,
        confirm_unsafe: bool = False,
        checkpoint_decision: str = "commit",
    ) -> dict[str, Any]:
        errors = self.validate(flow)
        if errors:
            return {"status": "error", "error": "; ".join(errors), "steps": []}
        values = self._parameter_values(flow, parameters or {})
        unsafe = bool(set(flow.capabilities) & UNSAFE_CAPABILITIES)
        trusted = flow.trusted_hash == content_hash(flow)
        if unsafe and not (confirm_unsafe or trusted):
            raise PermissionError("unsafe flow requires explicit confirmation")

        started = time.monotonic()
        log: dict[str, Any] = {
            "flow_id": flow.id,
            "status": "success",
            "parameters": values,
            "steps": [],
            "phases": [],
            "capabilities": flow.capabilities,
        }
        for phase in flow.phases:
            transaction_id = await self._begin_transaction(flow, phase.id)
            phase_log = {"id": phase.id, "transaction_id": transaction_id, "status": "active"}
            log["phases"].append(phase_log)
            for index, step in enumerate(phase.steps):
                if not _condition_matches(step.when, values):
                    log["steps"].append(
                        {"phase": phase.id, "index": index, "tool": step.tool, "status": "skipped"}
                    )
                    continue
                arguments = _resolve(step.arguments, values)
                step_started = time.monotonic()
                try:
                    result = await self.operations.get(step.tool)(**arguments)
                except Exception as exc:
                    result = {"status": "error", "error": str(exc)}
                step_log = {
                    "phase": phase.id,
                    "index": index,
                    "tool": step.tool,
                    "arguments": arguments,
                    "status": "success" if _result_succeeded(result) else "error",
                    "duration_ms": round((time.monotonic() - step_started) * 1000, 3),
                    "result": result,
                }
                log["steps"].append(step_log)
                if not _result_succeeded(result):
                    await self._rollback(transaction_id)
                    phase_log["status"] = "rolled-back"
                    log.update(
                        status="error",
                        error=result.get("error", f"tool failed: {step.tool}"),
                        duration_ms=round((time.monotonic() - started) * 1000, 3),
                    )
                    return log

            should_review = flow.review_policy == "phased" or phase.checkpoint
            if should_review and checkpoint_decision == "rollback":
                await self._rollback(transaction_id)
                phase_log["status"] = "rolled-back"
                log.update(status="rolled-back", duration_ms=round((time.monotonic() - started) * 1000, 3))
                return log
            await self._commit(transaction_id)
            phase_log["status"] = "committed"

        if flow.review_policy == "final":
            log["review"] = {"policy": "final", "decision": checkpoint_decision}
        log["duration_ms"] = round((time.monotonic() - started) * 1000, 3)
        return log

    def _parameter_values(self, flow: FlowDefinition, supplied: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for parameter in flow.parameters:
            if parameter.name in supplied:
                values[parameter.name] = supplied[parameter.name]
            elif parameter.default is not None:
                values[parameter.name] = parameter.default
            elif parameter.required:
                raise ValueError(f"missing required parameter: {parameter.name}")
            else:
                values[parameter.name] = None
        return values

    async def _begin_transaction(self, flow: FlowDefinition, phase_id: str) -> str | None:
        if "begin_edit_transaction" not in self.operations.names():
            return None
        result = await self.operations.get("begin_edit_transaction")(
            label=f"Repeatable Flow: {flow.title} / {phase_id}"
        )
        data = result.get("data", {})
        return data.get("transaction_id") if isinstance(data, dict) else None

    async def _commit(self, transaction_id: str | None) -> None:
        if "end_edit_transaction" in self.operations.names():
            await self.operations.get("end_edit_transaction")(transaction_id=transaction_id)

    async def _rollback(self, transaction_id: str | None) -> None:
        if "rollback_transaction" in self.operations.names():
            await self.operations.get("rollback_transaction")(transaction_id=transaction_id)


def _resolve(value: Any, parameters: dict[str, Any]) -> Any:
    if isinstance(value, str):
        exact = EXACT_REFERENCE_RE.match(value)
        if exact:
            return parameters[exact.group(1)]
        return REFERENCE_RE.sub(lambda match: str(parameters[match.group(1)]), value)
    if isinstance(value, dict):
        return {key: _resolve(item, parameters) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item, parameters) for item in value]
    return value


def _condition_matches(condition: str | None, parameters: dict[str, Any]) -> bool:
    if condition is None:
        return True
    exact = EXACT_REFERENCE_RE.match(condition.strip())
    if exact:
        return bool(parameters[exact.group(1)])
    for operator in ("==", "!="):
        if operator in condition:
            left, right = (part.strip() for part in condition.split(operator, 1))
            match = EXACT_REFERENCE_RE.match(left)
            if not match:
                return False
            expected = right.strip("'\"")
            actual = str(parameters[match.group(1)])
            return actual == expected if operator == "==" else actual != expected
    return False


def _result_succeeded(result: dict[str, Any]) -> bool:
    if "success" in result:
        return bool(result["success"])
    return result.get("status", "success") in {"success", "ok"}
