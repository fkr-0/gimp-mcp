"""Lifecycle and context-safety tests for selection category generated code."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.selection_tools import register_selection_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_stroke_selection_restores_foreground_and_line_width_context() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["stroke_selection"](
        color="#112233",
        brush_size=4.0,
        layer_name="Ink",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_selection_stroke_lifecycle__" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "previous_line_width = Gimp.context_get_line_width()" in generated
    assert "stroke_color = None" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "Gimp.context_set_line_width(previous_line_width)" in generated
    assert "del stroke_color" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_bucket_fill_restores_foreground_sample_threshold_and_merged_context() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["bucket_fill"](
        x=5,
        y=6,
        color="#445566",
        threshold=32,
        sample_merged=True,
        layer_name="Paint",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_selection_bucket_lifecycle__" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "previous_sample_threshold = Gimp.context_get_sample_threshold()" in generated
    assert "previous_sample_merged = Gimp.context_get_sample_merged()" in generated
    assert "fill_color = None" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "Gimp.context_set_sample_threshold(previous_sample_threshold)" in generated
    assert "Gimp.context_set_sample_merged(previous_sample_merged)" in generated
    assert "del fill_color" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_select_by_color_restores_sample_context_after_contiguous_color_selection() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["select_by_color"](
        x=30,
        y=30,
        threshold=40.0,
        operation="add",
        sample_merged=True,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_selection_sample_lifecycle__" in generated
    assert "previous_sample_threshold = Gimp.context_get_sample_threshold()" in generated
    assert "previous_sample_merged = Gimp.context_get_sample_merged()" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.context_set_sample_threshold(0.1568627450980392)" in generated
    assert "Gimp.context_set_sample_merged(True)" in generated
    assert (
        "Gimp.Image.select_contiguous_color(image, Gimp.ChannelOps.ADD, drawable, 30, 30)"
        in generated
    )
    assert "Gimp.context_set_sample_threshold(previous_sample_threshold)" in generated
    assert "Gimp.context_set_sample_merged(previous_sample_merged)" in generated
    assert "gc.collect()" in generated
