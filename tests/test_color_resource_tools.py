"""Focused generated-code coverage for color balance and GIMP resource listing tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from gimp_mcp_pro.protocol import PluginResponse
from gimp_mcp_pro.tools.color_tools import register_color_tools

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
    register_color_tools(mcp, bridge)
    return mcp.tools


def generated_source(bridge: ScriptedBridge) -> str:
    return "\n".join("\n".join(call) for call in bridge.calls)


@pytest.mark.asyncio
async def test_adjust_color_balance_uses_drawable_color_balance_api() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["adjust_color_balance"](
        range="highlights",
        cyan_red=25.0,
        magenta_green=-10.0,
        yellow_blue=5.0,
        preserve_luminosity=False,
        layer_name="Paint",
    )

    assert result["success"] is True
    assert result["operation"] == "adjust_color_balance"
    assert result["data"] == {
        "range": "highlights",
        "cyan_red": 25.0,
        "magenta_green": -10.0,
        "yellow_blue": 5.0,
        "preserve_luminosity": False,
    }
    generated = generated_source(bridge)
    assert "drawable = image.get_layer_by_name('Paint')" in generated
    assert (
        "Gimp.Drawable.color_balance(drawable, Gimp.TransferMode.HIGHLIGHTS, "
        "False, 0.25, -0.1, 0.05)" in generated
    )
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_list_gimp_resources_queries_brush_pattern_font_gradient_lists() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["list_gimp_resources"](resource_type="all", limit=5)

    assert result["success"] is True
    assert result["operation"] == "list_gimp_resources"
    assert result["data"] == {}
    generated = generated_source(bridge)
    assert "Gimp.brushes_get_list" in generated
    assert "Gimp.patterns_get_list" in generated
    assert "Gimp.fonts_get_list" in generated
    assert "Gimp.gradients_get_list" in generated
    assert "resources['brushes'] = _resource_names(Gimp.brushes_get_list(''))[:5]" in generated
    assert "resources['patterns'] = _resource_names(Gimp.patterns_get_list(''))[:5]" in generated
    assert "resources['fonts'] = _resource_names(Gimp.fonts_get_list(''))[:5]" in generated
    assert "resources['gradients'] = _resource_names(Gimp.gradients_get_list(''))[:5]" in generated
    assert "print(json.dumps(resources))" in generated


@pytest.mark.asyncio
async def test_color_to_alpha_releases_drawable_filter_refs() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["color_to_alpha"]("white")

    assert result["success"] is True
    generated_items = bridge.calls[-1]
    generated = generated_source(bridge)
    assert "# __gimp_mcp_color_to_alpha_lifecycle__" in generated
    assert "df = None" in generated
    assert "cfg = None" in generated
    assert "finally:" in generated
    assert "del cfg" in generated
    assert "del df" in generated
    assert "gc.collect()" in generated
    assert "try:" not in generated_items
