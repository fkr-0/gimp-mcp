"""Lifecycle and state-safety tests for drawing category generated code."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.drawing_tools import register_drawing_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_create_text_box_removes_partial_text_layer_and_releases_color_refs() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools["create_text_box"](
        text="Hello",
        rectangle={"x": 12, "y": 24, "width": 320, "height": 80},
        style={"font": "Sans", "font_size": 24, "color": "#445566", "justify": "center"},
        name="Title text",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_text_layer_lifecycle__" in generated
    assert "text_layer = None" in generated
    assert "text_color = None" in generated
    assert "try:" in generated
    assert "except Exception:" in generated
    assert "image.remove_layer(text_layer)" in generated
    assert "raise" in generated
    assert "del text_color" in generated
    assert "del text_layer" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_draw_line_restores_context_color_and_brush_size() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools["draw_line"](
        x1=1,
        y1=2,
        x2=10,
        y2=12,
        color="#112233",
        brush_size=5.0,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_drawing_context_lifecycle__" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "previous_brush_size = Gimp.context_get_brush_size()" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "Gimp.context_set_brush_size(previous_brush_size)" in generated
    assert "del draw_color" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_gradient_fill_restores_foreground_and_background_context() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools["gradient_fill"](
        x1=0,
        y1=0,
        x2=20,
        y2=20,
        foreground_color="#112233",
        background_color="#445566",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_gradient_context_lifecycle__" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "previous_background = Gimp.context_get_background()" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "Gimp.context_set_background(previous_background)" in generated
    assert "del gradient_foreground" in generated
    assert "del gradient_background" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_fill_selection_restores_foreground_context() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools["fill_selection"](
        fill_type="foreground",
        color="#112233",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_drawing_fill_lifecycle__" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "fill_color = None" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "Gimp.Drawable.edit_fill(drawable, Gimp.FillType.FOREGROUND)" in generated
    assert "del fill_color" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_draw_brush_stroke_restores_foreground_and_brush_size() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools["draw_brush_stroke"](
        points=[1, 2, 3, 4, 5, 6],
        tool="paintbrush",
        color="#445566",
        brush_size=7.5,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_brush_stroke_lifecycle__" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "previous_brush_size = Gimp.context_get_brush_size()" in generated
    assert "stroke_color = None" in generated
    assert "Gimp.context_set_brush_size(7.5)" in generated
    assert "Gimp.paintbrush_default(drawable, [1, 2, 3, 4, 5, 6])" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "Gimp.context_set_brush_size(previous_brush_size)" in generated
    assert "del stroke_color" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_add_text_rolls_back_partial_text_layer_and_restores_foreground() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools["add_text"](
        text="Hello",
        x=10,
        y=20,
        font_name="Sans",
        font_size=18,
        color="#abcdef",
        layer_name="Caption",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_add_text_lifecycle__" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "text_layer = None" in generated
    assert "text_color = None" in generated
    assert "inserted_layer = False" in generated
    assert "try:" in generated
    assert "except Exception:" in generated
    assert "image.remove_layer(text_layer)" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "del text_color" in generated
    assert "del text_layer" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "kwargs", "selection_call", "mutation_call"),
    [
        (
            "draw_rectangle",
            {
                "x": 1,
                "y": 2,
                "width": 30,
                "height": 40,
                "filled": False,
                "color": "#112233",
                "line_width": 4.5,
            },
            "Gimp.Image.select_rectangle(image, Gimp.ChannelOps.REPLACE, 1, 2, 30, 40)",
            "Gimp.Drawable.edit_stroke_selection(drawable)",
        ),
        (
            "draw_ellipse",
            {"x": 3, "y": 4, "width": 20, "height": 10, "filled": True, "color": "#445566"},
            "Gimp.Image.select_ellipse(image, Gimp.ChannelOps.REPLACE, 3, 4, 20, 10)",
            "Gimp.Drawable.edit_fill(drawable, Gimp.FillType.FOREGROUND)",
        ),
        (
            "draw_polygon",
            {
                "points": [0, 0, 10, 0, 10, 10],
                "filled": False,
                "color": "#778899",
                "line_width": 3.0,
            },
            "Gimp.Image.select_polygon(image, Gimp.ChannelOps.REPLACE, [0, 0, 10, 0, 10, 10])",
            "Gimp.Drawable.edit_stroke_selection(drawable)",
        ),
    ],
)
async def test_shape_tools_restore_selection_and_context_lifecycle(
    tool_name: str,
    kwargs: dict[str, object],
    selection_call: str,
    mutation_call: str,
) -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools[tool_name](**kwargs)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_shape_selection_lifecycle__" in generated
    assert "previous_selection = Gimp.Selection.save(image)" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "previous_line_width = Gimp.context_get_line_width()" in generated
    assert "shape_color = None" in generated
    assert selection_call in generated
    assert mutation_call in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "image.select_item(Gimp.ChannelOps.REPLACE, previous_selection)" in generated
    assert "image.remove_channel(previous_selection)" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "Gimp.context_set_line_width(previous_line_width)" in generated
    assert "del shape_color" in generated
    assert "del previous_selection" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_remaining_drawing_matrix_only_tools_have_direct_generated_code_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools["set_foreground_color"]("#010203")
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "_color = Gegl.Color.new('#010203')" in generated
    assert "Gimp.context_set_foreground(_color)" in generated

    result = await mcp.tools["set_background_color"]("#040506")
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "_color = Gegl.Color.new('#040506')" in generated
    assert "Gimp.context_set_background(_color)" in generated

    result = await mcp.tools["edit_clear"]()
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "images = Gimp.get_images()" in generated
    assert "drawable = sel[0]" in generated
    assert "Gimp.Drawable.edit_clear(drawable)" in generated
    assert "Gimp.displays_flush()" in generated
