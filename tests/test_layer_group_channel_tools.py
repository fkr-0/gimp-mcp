"""Focused generated-code coverage for layer group and channel tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from gimp_mcp_pro.protocol import PluginResponse
from gimp_mcp_pro.tools.layer_tools import register_layer_tools

Tool = Callable[..., Awaitable[dict[str, Any]]]


class CaptureMCP:
    """Small FastMCP-compatible registrar used for direct tool invocation."""

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[Tool], Tool]:
        """Return a decorator that records a tool coroutine by function name."""
        del args, kwargs

        def decorator(fn: Tool) -> Tool:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class ScriptedBridge:
    """Async bridge fake that records generated Python without requiring GIMP."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        del timeout
        self.calls.append(code_lines)
        return {"status": "success", "results": ["ok"]}


def registered_tools(bridge: ScriptedBridge) -> dict[str, Tool]:
    mcp = CaptureMCP()
    register_layer_tools(mcp, bridge)
    return mcp.tools


def generated_source(bridge: ScriptedBridge) -> str:
    return "\n".join("\n".join(call) for call in bridge.calls)


@pytest.mark.asyncio
async def test_create_layer_group_uses_group_layer_api() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["create_layer_group"](name="Characters", position=1)

    assert result["success"] is True
    assert result["operation"] == "create_layer_group"
    generated = generated_source(bridge)
    assert "group = Gimp.GroupLayer.new(image, 'Characters')" in generated
    assert "parent = None" in generated
    assert "if not image.insert_layer(group, parent, 1):" in generated
    assert "image.set_selected_layers([group])" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_move_layer_to_group_reorders_target_under_group() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["move_layer_to_group"](
        layer_name="Face",
        group_name="Characters",
        position=0,
    )

    assert result["success"] is True
    assert result["operation"] == "move_layer_to_group"
    generated = generated_source(bridge)
    assert "target = image.get_layer_by_name('Face')" in generated
    assert "group = image.get_layer_by_name('Characters')" in generated
    assert "if group is None or not group.is_group():" in generated
    assert "if not image.reorder_item(target, group, 0):" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_list_channels_reads_image_channels() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["list_channels"]()

    assert result["success"] is True
    assert result["operation"] == "list_channels"
    generated = generated_source(bridge)
    assert "channels = image.get_channels()" in generated
    assert "for i, channel in enumerate(channels):" in generated
    assert "channel.get_name()" in generated
    assert "print(json.dumps(result))" in generated


@pytest.mark.asyncio
async def test_save_selection_to_channel_uses_selection_save() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["save_selection_to_channel"](name="Saved alpha")

    assert result["success"] is True
    assert result["operation"] == "save_selection_to_channel"
    generated = generated_source(bridge)
    assert "channel = Gimp.Selection.save(image)" in generated
    assert (
        "if channel is None: raise RuntimeError('Could not save selection to channel')" in generated
    )
    assert "channel.set_name('Saved alpha')" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_channel_to_selection_selects_channel_item() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["channel_to_selection"](
        channel_name="Saved alpha",
        operation="add",
    )

    assert result["success"] is True
    assert result["operation"] == "channel_to_selection"
    generated = generated_source(bridge)
    assert "target = image.get_channel_by_name('Saved alpha')" in generated
    assert "if target is None: raise RuntimeError" in generated
    assert "image.select_item(Gimp.ChannelOps.ADD, target)" in generated
    assert "Gimp.displays_flush()" in generated
