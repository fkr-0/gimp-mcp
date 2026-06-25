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
