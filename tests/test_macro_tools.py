from __future__ import annotations

from typing import Any

import pytest

from gimp_mcp_pro.flows.operations import OperationRegistry
from gimp_mcp_pro.tools.flow_tools import register_flow_tools


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func

        return decorator


class MacroRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.assertions_succeed = True


def macro_registry_factory(recorder: MacroRecorder) -> OperationRegistry:
    registry = OperationRegistry()

    @registry.tool()
    async def begin_edit_transaction(
        label: str = "Macro", capture_before_state: bool = True
    ) -> dict[str, object]:
        recorder.calls.append(
            (
                "begin_edit_transaction",
                {"label": label, "capture_before_state": capture_before_state},
            )
        )
        return {"status": "success", "data": {"transaction_id": "tx-123"}}

    @registry.tool()
    async def end_edit_transaction(transaction_id: str | None = None) -> dict[str, object]:
        recorder.calls.append(("end_edit_transaction", {"transaction_id": transaction_id}))
        return {"status": "success", "data": {"transaction_id": transaction_id}}

    @registry.tool()
    async def rollback_transaction(transaction_id: str | None = None) -> dict[str, object]:
        recorder.calls.append(("rollback_transaction", {"transaction_id": transaction_id}))
        return {"status": "success", "data": {"transaction_id": transaction_id}}

    @registry.tool()
    async def scale_image(width: int, height: int) -> dict[str, object]:
        recorder.calls.append(("scale_image", {"width": width, "height": height}))
        return {"status": "success", "data": {"width": width, "height": height}}

    @registry.tool()
    async def set_layer_visibility(layer_index: int, visible: bool) -> dict[str, object]:
        recorder.calls.append(
            ("set_layer_visibility", {"layer_index": layer_index, "visible": visible})
        )
        return {"status": "success", "data": {"layer_index": layer_index, "visible": visible}}

    @registry.tool()
    async def fail_step(reason: str = "boom") -> dict[str, object]:
        recorder.calls.append(("fail_step", {"reason": reason}))
        return {"status": "error", "error": reason}

    @registry.tool()
    async def execute_python(code: list[str]) -> dict[str, object]:
        recorder.calls.append(("execute_python", {"code": code}))
        return {"status": "success"}

    @registry.tool()
    async def assert_image_state(assertions: list[dict[str, Any]]) -> dict[str, object]:
        recorder.calls.append(("assert_image_state", {"assertions": assertions}))
        if recorder.assertions_succeed:
            return {"success": True, "data": {"assertions": assertions}}
        return {"success": False, "error": "image assertion failed"}

    return registry


def register_macro_tools(recorder: MacroRecorder) -> dict[str, Any]:
    mcp = FakeMCP()
    register_flow_tools(
        mcp,
        recorder,
        registry_factory=lambda bridge: macro_registry_factory(bridge),
    )
    return mcp.tools


@pytest.mark.asyncio
async def test_dry_run_macro_validates_steps_without_executing_operations() -> None:
    recorder = MacroRecorder()
    tools = register_macro_tools(recorder)
    steps = [
        {"tool": "scale_image", "arguments": {"width": 320, "height": 200}},
        {"tool": "set_layer_visibility", "arguments": {"layer_index": 0, "visible": False}},
    ]

    result = await tools["dry_run_macro"](steps)

    assert result["success"] is True
    assert result["data"]["valid"] is True
    assert result["data"]["failures"] == []
    assert result["data"]["predicted_changes"] == [
        {"step": 0, "tool": "scale_image", "arguments": {"width": 320, "height": 200}},
        {
            "step": 1,
            "tool": "set_layer_visibility",
            "arguments": {"layer_index": 0, "visible": False},
        },
    ]
    assert result["data"]["resolved_targets"] == [
        {
            "step": 1,
            "tool": "set_layer_visibility",
            "target_type": "layer",
            "selector": {"layer_index": 0},
        }
    ]
    assert recorder.calls == []


@pytest.mark.asyncio
async def test_dry_run_macro_reports_unknown_extra_and_unsafe_steps_without_execution() -> None:
    recorder = MacroRecorder()
    tools = register_macro_tools(recorder)
    steps = [
        {"tool": "missing_tool", "arguments": {}},
        {"tool": "scale_image", "arguments": {"width": 320, "height": 200, "extra": True}},
        {"tool": "execute_python", "arguments": {"code": ["print('nope')"]}},
    ]

    result = await tools["dry_run_macro"](steps)

    assert result["success"] is True
    assert result["data"]["valid"] is False
    assert result["data"]["predicted_changes"] == []
    assert [failure["error"] for failure in result["data"]["failures"]] == [
        "unknown tool: missing_tool",
        "tool scale_image has no argument extra",
        "unsafe tool execute_python requires confirm_unsafe=true",
    ]
    assert recorder.calls == []


@pytest.mark.asyncio
async def test_run_macro_transaction_commits_successful_steps_with_audit_log() -> None:
    recorder = MacroRecorder()
    tools = register_macro_tools(recorder)

    result = await tools["run_macro_transaction"](
        [
            {"tool": "scale_image", "arguments": {"width": 640, "height": 480}},
            {"tool": "set_layer_visibility", "arguments": {"layer_index": 0, "visible": True}},
        ],
        transaction_label="Resize and reveal",
        rollback_on_failure=True,
        capture_before_after=True,
    )

    assert result["success"] is True
    data = result["data"]
    assert data["transaction_id"] == "tx-123"
    assert data["rolled_back"] is False
    assert data["step_results"] == [
        {
            "step": 0,
            "tool": "scale_image",
            "arguments": {"width": 640, "height": 480},
            "status": "success",
            "result": {"status": "success", "data": {"width": 640, "height": 480}},
        },
        {
            "step": 1,
            "tool": "set_layer_visibility",
            "arguments": {"layer_index": 0, "visible": True},
            "status": "success",
            "result": {"status": "success", "data": {"layer_index": 0, "visible": True}},
        },
    ]
    assert [name for name, _args in recorder.calls] == [
        "begin_edit_transaction",
        "scale_image",
        "set_layer_visibility",
        "end_edit_transaction",
    ]


@pytest.mark.asyncio
async def test_run_macro_transaction_rolls_back_on_step_failure() -> None:
    recorder = MacroRecorder()
    tools = register_macro_tools(recorder)

    result = await tools["run_macro_transaction"](
        [
            {"tool": "scale_image", "arguments": {"width": 640, "height": 480}},
            {"tool": "fail_step", "arguments": {"reason": "bad target"}},
            {"tool": "set_layer_visibility", "arguments": {"layer_index": 0, "visible": True}},
        ],
        rollback_on_failure=True,
    )

    assert result["success"] is False
    assert result["error"] == "bad target"
    data = result["data"]
    assert data["transaction_id"] == "tx-123"
    assert data["rolled_back"] is True
    assert [step["tool"] for step in data["step_results"]] == ["scale_image", "fail_step"]
    assert [name for name, _args in recorder.calls] == [
        "begin_edit_transaction",
        "scale_image",
        "fail_step",
        "rollback_transaction",
    ]


@pytest.mark.asyncio
async def test_run_macro_transaction_checks_preconditions_before_mutation() -> None:
    recorder = MacroRecorder()
    recorder.assertions_succeed = False
    tools = register_macro_tools(recorder)

    result = await tools["run_macro_transaction"](
        [{"tool": "scale_image", "arguments": {"width": 640, "height": 480}}],
        preconditions=[{"path": "dimensions.width", "equals": 320}],
    )

    assert result["success"] is False
    assert result["data"]["validation_stage"] == "preconditions"
    assert [name for name, _args in recorder.calls] == ["assert_image_state"]


@pytest.mark.asyncio
async def test_run_macro_transaction_rolls_back_failed_postconditions() -> None:
    recorder = MacroRecorder()
    tools = register_macro_tools(recorder)
    original_assert = recorder.assertions_succeed
    recorder.assertions_succeed = False

    result = await tools["run_macro_transaction"](
        [{"tool": "scale_image", "arguments": {"width": 640, "height": 480}}],
        postconditions=[{"path": "dimensions.width", "equals": 640}],
    )

    recorder.assertions_succeed = original_assert
    assert result["success"] is False
    assert result["data"]["rolled_back"] is True
    assert [name for name, _args in recorder.calls] == [
        "begin_edit_transaction",
        "scale_image",
        "assert_image_state",
        "rollback_transaction",
    ]
