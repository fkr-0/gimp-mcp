from __future__ import annotations

from typing import Any

import pytest

from gimp_mcp_pro.flows.models import FlowDefinition
from gimp_mcp_pro.flows.operations import OperationRegistry
from gimp_mcp_pro.flows.runner import FlowRunner


def make_flow(*steps: dict[str, Any], capabilities: list[str] | None = None) -> FlowDefinition:
    return FlowDefinition.model_validate(
        {
            "id": "runner-test",
            "title": "Runner Test",
            "parameters": [
                {"name": "name", "type": "text", "required": True},
                {"name": "enabled", "type": "boolean", "default": True},
            ],
            "phases": [{"id": "main", "steps": list(steps)}],
            "review_policy": "none",
            "capabilities": capabilities or [],
        }
    )


def test_operation_registry_captures_decorated_async_tools() -> None:
    registry = OperationRegistry()

    @registry.tool()
    async def hello(name: str) -> dict[str, object]:
        return {"status": "success", "name": name}

    assert registry.get("hello") is hello
    assert registry.names() == ["hello"]


@pytest.mark.asyncio
async def test_runner_substitutes_parameters_and_honors_when() -> None:
    calls: list[tuple[str, Any]] = []
    registry = OperationRegistry()

    @registry.tool()
    async def record(payload: Any) -> dict[str, object]:
        calls.append(("record", payload))
        return {"status": "success"}

    flow = make_flow(
        {"tool": "record", "arguments": {"payload": {"name": "${name}"}}},
        {"tool": "record", "arguments": {"payload": "skipped"}, "when": "${enabled}"},
    )
    result = await FlowRunner(registry).run(flow, {"name": "Alice", "enabled": False})

    assert result["status"] == "success"
    assert calls == [("record", {"name": "Alice"})]
    assert result["steps"][1]["status"] == "skipped"


@pytest.mark.asyncio
async def test_runner_wraps_phase_in_transaction() -> None:
    calls: list[str] = []
    registry = OperationRegistry()

    @registry.tool()
    async def begin_edit_transaction(label: str) -> dict[str, object]:
        calls.append("begin")
        return {"status": "success", "data": {"transaction_id": "txn-1"}}

    @registry.tool()
    async def record(payload: Any) -> dict[str, object]:
        calls.append("step")
        return {"status": "success"}

    @registry.tool()
    async def end_edit_transaction(transaction_id: str | None = None) -> dict[str, object]:
        calls.append("commit")
        return {"status": "success"}

    flow = make_flow({"tool": "record", "arguments": {"payload": "${name}"}})
    result = await FlowRunner(registry).run(flow, {"name": "x"})

    assert result["status"] == "success"
    assert calls == ["begin", "step", "commit"]


@pytest.mark.asyncio
async def test_runner_rolls_back_failed_phase() -> None:
    calls: list[str] = []
    registry = OperationRegistry()

    @registry.tool()
    async def begin_edit_transaction(label: str) -> dict[str, object]:
        calls.append("begin")
        return {"status": "success", "data": {"transaction_id": "txn-2"}}

    @registry.tool()
    async def fail() -> dict[str, object]:
        calls.append("fail")
        return {"status": "error", "error": "boom"}

    @registry.tool()
    async def rollback_transaction(transaction_id: str | None = None) -> dict[str, object]:
        calls.append("rollback")
        return {"status": "success"}

    flow = make_flow({"tool": "fail", "arguments": {}})
    result = await FlowRunner(registry).run(flow, {"name": "x"})

    assert result["status"] == "error"
    assert result["error"] == "boom"
    assert calls == ["begin", "fail", "rollback"]


@pytest.mark.asyncio
async def test_final_review_can_roll_back_before_commit() -> None:
    calls: list[str] = []
    registry = OperationRegistry()

    @registry.tool()
    async def begin_edit_transaction(label: str) -> dict[str, object]:
        calls.append("begin")
        return {"status": "success", "data": {"transaction_id": "txn-final"}}

    @registry.tool()
    async def record(payload: Any) -> dict[str, object]:
        calls.append("step")
        return {"status": "success"}

    @registry.tool()
    async def end_edit_transaction(transaction_id: str | None = None) -> dict[str, object]:
        calls.append("commit")
        return {"status": "success"}

    @registry.tool()
    async def rollback_transaction(transaction_id: str | None = None) -> dict[str, object]:
        calls.append("rollback")
        return {"status": "success"}

    flow = make_flow({"tool": "record", "arguments": {"payload": "x"}})
    flow.review_policy = "final"
    result = await FlowRunner(registry).run(flow, {"name": "x"}, checkpoint_decision="rollback")

    assert result["status"] == "rolled-back"
    assert calls == ["begin", "step", "rollback"]


@pytest.mark.asyncio
async def test_runner_requires_confirmation_for_unsafe_flow() -> None:
    registry = OperationRegistry()

    @registry.tool()
    async def execute_python(code: list[str]) -> dict[str, object]:
        return {"status": "success"}

    flow = make_flow(
        {"tool": "execute_python", "arguments": {"code": ["print('x')"]}},
        capabilities=["arbitrary-code"],
    )

    with pytest.raises(PermissionError, match="unsafe"):
        await FlowRunner(registry).run(flow, {"name": "x"})

    assert (await FlowRunner(registry).run(flow, {"name": "x"}, confirm_unsafe=True))["status"] == "success"


def test_runner_validation_reports_unknown_tools_and_arguments() -> None:
    registry = OperationRegistry()

    @registry.tool()
    async def known(value: int) -> dict[str, object]:
        return {"status": "success"}

    flow = make_flow({"tool": "known", "arguments": {"wrong": 1}})
    errors = FlowRunner(registry).validate(flow)

    assert any("wrong" in error for error in errors)
