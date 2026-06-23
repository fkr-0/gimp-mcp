"""Focused generated-code coverage for guide and image-grid tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from gimp_mcp_pro.protocol import PluginResponse
from gimp_mcp_pro.tools.image_tools import register_image_tools

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
        return {"status": "success", "results": ["{}"]}


def registered_tools(bridge: ScriptedBridge) -> dict[str, Tool]:
    mcp = CaptureMCP()
    register_image_tools(mcp, bridge)
    return mcp.tools


def generated_source(bridge: ScriptedBridge) -> str:
    return "\n".join("\n".join(call) for call in bridge.calls)


@pytest.mark.asyncio
async def test_guide_tools_use_image_guide_api() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    add = await tools["add_guide"](orientation="vertical", position=42)
    listed = await tools["list_guides"]()
    deleted = await tools["delete_guide"](guide_id=7)

    assert add["success"] is True
    assert add["operation"] == "add_guide"
    assert listed["success"] is True
    assert listed["operation"] == "list_guides"
    assert deleted["success"] is True
    assert deleted["operation"] == "delete_guide"
    generated = generated_source(bridge)
    assert "guide_id = image.add_vguide(42)" in generated
    assert "guide_id = image.find_next_guide(0)" in generated
    assert "image.get_guide_orientation(guide_id)" in generated
    assert "image.get_guide_position(guide_id)" in generated
    assert "image.delete_guide(7)" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_set_image_grid_uses_grid_spacing_offset_and_style_api() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["set_image_grid"](
        xspacing=16.0,
        yspacing=8.0,
        xoffset=2.0,
        yoffset=3.0,
        style="solid",
    )

    assert result["success"] is True
    assert result["operation"] == "set_image_grid"
    assert result["data"] == {
        "xspacing": 16.0,
        "yspacing": 8.0,
        "xoffset": 2.0,
        "yoffset": 3.0,
        "style": "solid",
    }
    generated = generated_source(bridge)
    assert "image.grid_set_spacing(16.0, 8.0)" in generated
    assert "image.grid_set_offset(2.0, 3.0)" in generated
    assert "image.grid_set_style(Gimp.GridStyle.SOLID)" in generated
