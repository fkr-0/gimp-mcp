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


@pytest.mark.asyncio
async def test_select_by_color_uses_gimp_3_2_contiguous_color_api_without_removed_pdb_run_procedure() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["select_by_color"](
        x=30,
        y=30,
        threshold=40.0,
        operation="add",
        sample_merged=True,
    )

    assert result["success"] is True
    assert result["operation"] == "select_by_color"
    generated = generated_source(bridge)
    assert "run_procedure" not in generated
    assert "Gimp.Image.select_contiguous_color(" in generated
    assert "Gimp.ChannelOps.ADD" in generated
    assert "Gimp.context_set_sample_threshold(" in generated
    assert "Gimp.context_set_sample_merged(True)" in generated


@pytest.mark.asyncio
async def test_selection_info_and_color_selection_handle_gimp_3_2_bounds_return_shape() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    await tools["get_selection_info"]()
    await tools["select_by_color"](x=4, y=5)

    generated = generated_source(bridge)
    assert "bounds = Gimp.Selection.bounds(image)" in generated
    assert "if len(bounds) == 6:" in generated
    assert "_, non_empty, x1, y1, x2, y2 = bounds" in generated
    assert "else:" in generated
    assert "non_empty, x1, y1, x2, y2 = bounds" in generated


@pytest.mark.asyncio
async def test_gradient_fill_uses_drawable_gradient_api_with_colors() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["gradient_fill"](
        x1=0,
        y1=0,
        x2=100,
        y2=50,
        gradient_type="radial",
        foreground_color="#000000",
        background_color="#ffffff",
        dither=True,
    )

    assert result["success"] is True
    assert result["operation"] == "gradient_fill"
    generated = generated_source(bridge)
    assert "Gimp.context_set_foreground(Gegl.Color.new('#000000'))" in generated
    assert "Gimp.context_set_background(Gegl.Color.new('#ffffff'))" in generated
    assert (
        "Gimp.Drawable.edit_gradient_fill(drawable, Gimp.GradientType.RADIAL, "
        "0.0, False, 3, 0.2, True, 0, 0, 100, 50)" in generated
    )
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_edit_text_layer_updates_content_font_size_color_and_alignment() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["edit_text_layer"](
        text="Revised caption",
        layer_name="Caption",
        font_name="Serif",
        font_size=32.0,
        color="#336699",
        justification="center",
    )

    assert result["success"] is True
    assert result["operation"] == "edit_text_layer"
    generated = generated_source(bridge)
    assert "layer = image.get_layer_by_name('Caption')" in generated
    assert "text_layer = Gimp.TextLayer.get_by_id(layer.get_id())" in generated
    assert "text_layer.set_text('Revised caption')" in generated
    assert "font = Gimp.Font.get_by_name('Serif')" in generated
    assert "text_layer.set_font(font)" in generated
    assert "text_layer.set_font_size(32.0, Gimp.Unit.pixel())" in generated
    assert "text_layer.set_color(Gegl.Color.new('#336699'))" in generated
    assert "text_layer.set_justification(Gimp.TextJustification.CENTER)" in generated
