"""Tests for first-wave async agent transaction tools."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from gimp_mcp_pro.protocol import BitmapRegion, CommandParams, PluginResponse, ToolResult
from gimp_mcp_pro.tools.agent_tools import IMPLEMENTED_AGENT_FEATURES, register_agent_tools
from gimp_mcp_pro.utils.errors import GimpCommandError

Tool = Callable[..., Awaitable[ToolResult]]


class CaptureMCP:
    """Tiny FastMCP-compatible registrar."""

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[Tool], Tool]:
        def decorator(fn: Tool) -> Tool:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class TransactionBridge:
    """Async bridge fake that records generated transaction snippets."""

    def __init__(self) -> None:
        self.execute_calls: list[list[str]] = []
        self.metadata_calls = 0

    async def async_send_command(
        self,
        command_type: str,
        params: CommandParams | None = None,
        timeout: float | None = None,
    ) -> PluginResponse:
        del command_type, params, timeout
        return {"status": "success", "results": {}}

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        del timeout
        self.execute_calls.append(code_lines)
        source = "\n".join(code_lines)
        if "begin_edit_transaction" in source:
            return {
                "status": "success",
                "results": [json.dumps({"image_id": 42, "undo_group_started": True})],
            }
        if "end_edit_transaction" in source:
            return {
                "status": "success",
                "results": [json.dumps({"undo_group_ended": True})],
            }
        if "rollback_transaction" in source:
            return {
                "status": "success",
                "results": [json.dumps({"undo_group_ended": True, "rolled_back": True})],
            }
        raise AssertionError(f"unexpected transaction code: {source}")

    async def async_evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        del expressions, timeout
        return {"status": "success", "results": []}

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: BitmapRegion | None = None,
    ) -> PluginResponse:
        del max_width, max_height, region
        return {"status": "success", "results": {}}

    async def async_get_image_metadata(self) -> PluginResponse:
        self.metadata_calls += 1
        return {
            "status": "success",
            "results": {"basic": {"width": 320, "height": 240}, "layers": []},
        }

    async def async_get_context_state(self) -> PluginResponse:
        return {"status": "success", "results": {}}

    async def async_get_gimp_info(self) -> PluginResponse:
        return {"status": "success", "results": {"gimp": {"version": "3.2.4"}}}


class FailingTransactionBridge(TransactionBridge):
    """Bridge fake that fails generated transaction execution."""

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        del code_lines, timeout
        raise GimpCommandError("transaction failed", command="execute_python")


def registered_tools(bridge: TransactionBridge) -> dict[str, Tool]:
    mcp = CaptureMCP()
    register_agent_tools(mcp, bridge)
    return mcp.tools


def test_agent_feature_manifest_tracks_selected_first_wave_features() -> None:
    """The module records the selected in-progress roadmap features."""
    feature_ids = {feature["id"] for feature in IMPLEMENTED_AGENT_FEATURES}

    assert feature_ids == {
        "FEAT-001",
        "FEAT-002",
        "FEAT-007",
        "FEAT-008",
        "FEAT-010",
        "FEAT-011",
        "FEAT-012",
        "FEAT-045",
    }
    assert {feature["status"] for feature in IMPLEMENTED_AGENT_FEATURES} == {"in_progress"}


@pytest.mark.asyncio
async def test_begin_transaction_starts_undo_group_and_captures_before_state() -> None:
    bridge = TransactionBridge()
    tools = registered_tools(bridge)

    result = await tools["begin_edit_transaction"]("Sketch pass", capture_before_state=True)

    assert result["success"] is True
    assert result["operation"] == "begin_edit_transaction"
    assert result["data"]["feature_id"] == "FEAT-010"
    assert result["data"]["transaction_id"].startswith("txn-")
    assert result["data"]["before_state"] == {"basic": {"width": 320, "height": 240}, "layers": []}
    assert bridge.metadata_calls == 1
    source = "\n".join(bridge.execute_calls[-1])
    assert "image.undo_group_start()" in source


@pytest.mark.asyncio
async def test_begin_then_end_transaction_tracks_known_transaction() -> None:
    bridge = TransactionBridge()
    tools = registered_tools(bridge)

    begin = await tools["begin_edit_transaction"]("Commit me")
    transaction_id = begin["data"]["transaction_id"]
    end = await tools["end_edit_transaction"](transaction_id, require_known=True)

    assert end["success"] is True
    assert end["data"]["tracked"] is True
    assert end["data"]["feature_id"] == "FEAT-011"
    assert end["data"]["undo_group_ended"] is True
    source = "\n".join(bridge.execute_calls[-1])
    assert "image.undo_group_end()" in source


@pytest.mark.asyncio
async def test_end_transaction_can_require_known_id_without_touching_bridge() -> None:
    bridge = TransactionBridge()
    tools = registered_tools(bridge)

    result = await tools["end_edit_transaction"]("missing", require_known=True)

    assert result["success"] is False
    assert result["operation"] == "end_edit_transaction"
    assert "unknown" in result["error"]
    assert bridge.execute_calls == []


@pytest.mark.asyncio
async def test_rollback_transaction_uses_generated_undo_fallback_and_tracks_id() -> None:
    bridge = TransactionBridge()
    tools = registered_tools(bridge)

    begin = await tools["begin_edit_transaction"]("Rollback me")
    transaction_id = begin["data"]["transaction_id"]
    rollback = await tools["rollback_transaction"](transaction_id, require_known=True)

    assert rollback["success"] is True
    assert rollback["data"]["tracked"] is True
    assert rollback["data"]["feature_id"] == "FEAT-012"
    assert rollback["data"]["rolled_back"] is True
    source = "\n".join(bridge.execute_calls[-1])
    assert "image.undo()" in source
    assert "gimp-image-undo" in source


@pytest.mark.asyncio
async def test_transaction_bridge_failures_return_structured_results() -> None:
    bridge = FailingTransactionBridge()
    tools = registered_tools(bridge)

    result = await tools["begin_edit_transaction"]()

    assert result["success"] is False
    assert result["operation"] == "begin_edit_transaction"
    assert "transaction failed" in result["error"]


@pytest.mark.asyncio
async def test_rollback_transaction_can_recover_all_tracked_open_transactions() -> None:
    bridge = TransactionBridge()
    tools = registered_tools(bridge)

    first = await tools["begin_edit_transaction"]("first")
    second = await tools["begin_edit_transaction"]("second")

    first_id = first["data"]["transaction_id"]
    second_id = second["data"]["transaction_id"]
    recovered = await tools["rollback_transaction"](recover_all=True)

    assert recovered["success"] is True
    assert recovered["data"]["recovered_transaction_ids"] == [second_id, first_id]
    assert recovered["data"]["tracked"] is True
    source = "\n".join(bridge.execute_calls[-1])
    assert "image.undo_group_end()" in source
    assert "gimp-image-undo" in source

    missing = await tools["end_edit_transaction"](first_id, require_known=True)
    assert missing["success"] is False
    assert "unknown" in missing["error"]
