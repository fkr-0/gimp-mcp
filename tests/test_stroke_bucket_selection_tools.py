"""Focused generated-code coverage for stroke, bucket fill, and selection advancement tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from gimp_mcp_pro.protocol import PluginResponse
from gimp_mcp_pro.tools.drawing_tools import register_drawing_tools
from gimp_mcp_pro.tools.selection_tools import register_selection_tools

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
    register_selection_tools(mcp, bridge)
    register_drawing_tools(mcp, bridge)
    return mcp.tools


def generated_source(bridge: ScriptedBridge) -> str:
    return "\n".join("\n".join(call) for call in bridge.calls)


@pytest.mark.asyncio
async def test_stroke_selection_exposes_current_selection_stroke_api() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["stroke_selection"](color="#123456", brush_size=7.5)

    assert result["success"] is True
    assert result["operation"] == "stroke_selection"
    generated = generated_source(bridge)
    assert "Gimp.context_set_foreground(Gegl.Color.new('#123456'))" in generated
    assert "Gimp.context_set_line_width(7.5)" in generated
    assert "Gimp.Drawable.edit_stroke_selection(drawable)" in generated
    assert "Gimp.Selection.none(image)" not in generated


@pytest.mark.asyncio
async def test_bucket_fill_uses_drawable_seed_fill_with_threshold_context() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["bucket_fill"](
        x=10,
        y=12,
        color="red",
        threshold=51.0,
        sample_merged=True,
    )

    assert result["success"] is True
    assert result["operation"] == "bucket_fill"
    generated = generated_source(bridge)
    assert "Gimp.context_set_foreground(Gegl.Color.new('red'))" in generated
    assert "Gimp.context_set_sample_threshold(0.2)" in generated
    assert "Gimp.context_set_sample_merged(True)" in generated
    assert "Gimp.Drawable.edit_bucket_fill(drawable, Gimp.FillType.FOREGROUND, 10, 12)" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_selection_advancement_tools_expose_feather_border_grow_shrink() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    calls = [
        ("feather_selection", (3.5,), {}),
        ("border_selection", (2,), {}),
        ("select_grow", (4,), {}),
        ("select_shrink", (1,), {}),
    ]
    for name, args, kwargs in calls:
        result = await tools[name](*args, **kwargs)
        assert result["success"] is True, (name, result)
        assert result["operation"] == name

    generated = generated_source(bridge)
    assert "Gimp.Selection.feather(images[0], 3.5)" in generated
    assert "Gimp.Selection.border(images[0], 2)" in generated
    assert "Gimp.Selection.grow(images[0], 4)" in generated
    assert "Gimp.Selection.shrink(images[0], 1)" in generated
