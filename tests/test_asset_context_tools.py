"""Focused TDD coverage for paint-resource and paint-context features."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.color_tools import register_color_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_brush_inventory_lists_assets_with_current_context_markers() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["brush_inventory"](
        asset_types=["brushes", "patterns", "palettes"],
        filter="Hardness",
        limit=12,
        include_current=True,
    )

    assert result["success"] is True
    assert result["operation"] == "brush_inventory"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_brush_inventory__" in generated
    assert "asset_types = ['brushes', 'patterns', 'palettes']" in generated
    assert "filter_text = 'Hardness'" in generated
    assert "limit = 12" in generated
    assert "Gimp.brushes_get_list('')" in generated
    assert "Gimp.patterns_get_list('')" in generated
    assert "Gimp.palettes_get_list('')" in generated
    assert "Gimp.context_get_brush()" in generated
    assert "is_current" in generated


@pytest.mark.asyncio
async def test_set_paint_resource_validates_resource_and_reads_back_context() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["set_paint_resource"](
        resource_type="brush",
        name="2. Hardness 050",
    )

    assert result["success"] is True
    assert result["operation"] == "set_paint_resource"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_set_paint_resource__" in generated
    assert "resource_type = 'brush'" in generated
    assert "resource_name = '2. Hardness 050'" in generated
    assert "Gimp.brushes_get_list('')" in generated
    assert "if resource_name not in names" in generated
    assert "previous_resource" in generated
    assert "Gimp.context_set_brush(resource_name)" in generated
    assert "Gimp.context_get_brush()" in generated
    assert "active_resource" in generated


@pytest.mark.asyncio
async def test_set_paint_context_sets_multiple_validated_context_fields() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["set_paint_context"](
        brush="2. Hardness 050",
        size=12.5,
        opacity=80.0,
        pattern="Pine",
        gradient="FG to BG (RGB)",
        foreground="#112233",
        background="#ffffff",
    )

    assert result["success"] is True
    assert result["operation"] == "set_paint_context"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_set_paint_context__" in generated
    assert "Gimp.context_get_brush()" in generated
    assert "Gimp.context_get_opacity()" in generated
    assert "Gimp.context_get_brush_size()" in generated
    assert "Gimp.brushes_get_list('')" in generated
    assert "Gimp.patterns_get_list('')" in generated
    assert "Gimp.gradients_get_list('')" in generated
    assert "Gimp.context_set_brush('2. Hardness 050')" in generated
    assert "Gimp.context_set_brush_size(12.5)" in generated
    assert "Gimp.context_set_opacity(80.0)" in generated
    assert "Gimp.context_set_pattern('Pine')" in generated
    assert "Gimp.context_set_gradient('FG to BG (RGB)')" in generated
    assert "Gimp.context_set_foreground(Gegl.Color.new('#112233'))" in generated
    assert "Gimp.context_set_background(Gegl.Color.new('#ffffff'))" in generated
    assert "previous_context" in generated
    assert "new_context" in generated


@pytest.mark.asyncio
async def test_set_paint_resource_rejects_unsupported_resource_type_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["set_paint_resource"](
        resource_type="preset",
        name="Nope",
    )

    assert result["success"] is False
    assert "unsupported" in result["error"].lower()
    assert bridge.calls == []
