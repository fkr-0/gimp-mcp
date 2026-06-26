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


@pytest.mark.asyncio
async def test_select_by_color_defaults_to_global_select_color() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["select_by_color"](x=12, y=13, threshold=8.0)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "if False:" in generated
    assert "image.pick_color([drawable], 12, 13, False, False, 0.0)" in generated
    assert (
        "Gimp.Image.select_color(image, Gimp.ChannelOps.REPLACE, drawable, sampled_color)"
        in generated
    )


@pytest.mark.asyncio
async def test_select_by_color_can_still_use_contiguous_blob_mode() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["select_by_color"](x=12, y=13, threshold=8.0, contiguous=True)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "if True:" in generated
    assert (
        "Gimp.Image.select_contiguous_color(image, Gimp.ChannelOps.REPLACE, drawable, 12, 13)"
        in generated
    )


@pytest.mark.asyncio
async def test_select_layer_alpha_uses_image_select_item() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["select_layer_alpha"](layer_index=2, operation="add")

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "target = layers[2]" in generated
    assert "image.select_item(Gimp.ChannelOps.ADD, target)" in generated


@pytest.mark.asyncio
async def test_fuzzy_select_alias_for_contiguous_color_selection() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["fuzzy_select"](x=7, y=8, threshold=32.0)

    assert result["success"] is True
    assert result["operation"] == "fuzzy_select"
    generated = "\n".join(bridge.calls[-1][1])
    assert (
        "Gimp.Image.select_contiguous_color(image, Gimp.ChannelOps.REPLACE, drawable, 7, 8)"
        in generated
    )


@pytest.mark.asyncio
async def test_select_color_uses_explicit_global_color_selection() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["select_color"]("#ffffff", threshold=10.0, layer_index=0)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "drawable = layers[0]" in generated
    assert "selected_color = Gegl.Color.new('#ffffff')" in generated
    assert (
        "Gimp.Image.select_color(image, Gimp.ChannelOps.REPLACE, drawable, selected_color)"
        in generated
    )
