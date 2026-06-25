"""Focused TDD coverage for a larger remaining-feature chunk."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.color_tools import register_color_tools
from gimp_mcp_pro.tools.drawing_tools import register_drawing_tools
from gimp_mcp_pro.tools.image_tools import register_image_tools
from gimp_mcp_pro.tools.target_tools import register_target_tools
from gimp_mcp_pro.tools.transform_tools import register_transform_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_find_similar_regions_scans_pixels_deterministically_without_semantic_claims() -> (
    None
):
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_target_tools(mcp, bridge)

    result = await mcp.tools["find_similar_regions"](
        color="#112233",
        alpha_range={"min": 0.25, "max": 1.0},
        region={"x": 10, "y": 20, "width": 100, "height": 80},
        tolerance=0.12,
        max_regions=8,
    )

    assert result["success"] is True
    assert result["operation"] == "find_similar_regions"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_find_similar_regions__" in generated
    assert "target_color = '#112233'" in generated
    assert "alpha_min = 0.25" in generated
    assert "alpha_max = 1.0" in generated
    assert "tolerance = 0.12" in generated
    assert "drawable.get_pixel(x, y)" in generated
    assert "confidence" in generated
    assert "semantic_object_recognition" not in generated


@pytest.mark.asyncio
async def test_create_text_box_places_text_layer_with_rectangle_and_style() -> None:
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
    assert result["operation"] == "create_text_box"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_create_text_box__" in generated
    assert "text = 'Hello'" in generated
    assert "x = 12" in generated and "y = 24" in generated
    assert "width = 320" in generated and "height = 80" in generated
    assert "Gimp.fonts_get_list('')" in generated
    assert "Gimp.TextLayer.new(image, text" in generated
    assert "text_layer.set_offsets(x, y)" in generated
    assert "text_layer.resize(width, height)" in generated
    assert "Gegl.Color.new('#445566')" in generated
    assert "Gimp.TextJustification.CENTER" in generated


@pytest.mark.asyncio
async def test_align_and_distribute_layers_reports_old_and_new_bounds_with_locks() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["align_and_distribute_layers"](
        layers=[{"layer_name": "A"}, {"layer_name": "B"}],
        align="center_x",
        distribute="horizontal",
        reference="canvas",
        dry_run=True,
    )

    assert result["success"] is True
    assert result["operation"] == "align_and_distribute_layers"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_align_and_distribute_layers__" in generated
    assert "image.get_layer_by_name('A')" in generated
    assert "image.get_layer_by_name('B')" in generated
    assert "align = 'center_x'" in generated
    assert "distribute = 'horizontal'" in generated
    assert "reference = 'canvas'" in generated
    assert "old_bounds" in generated and "new_bounds" in generated
    assert "get_lock_position" in generated
    assert "if not dry_run:" in generated
    assert "layer.set_offsets" in generated


@pytest.mark.asyncio
async def test_resource_catalog_lists_searchable_bounded_resources_and_optional_types() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["resource_catalog"](
        resource_type="brush",
        query="Hardness",
        limit=10,
        include_optional=True,
    )

    assert result["success"] is True
    assert result["operation"] == "resource_catalog"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_resource_catalog__" in generated
    assert "resource_type = 'brushes'" in generated
    assert "query = 'hardness'" in generated
    assert "limit = 10" in generated
    assert "Gimp.brushes_get_list('')" in generated
    assert "resources" in generated
    assert "optional_capability" in generated


@pytest.mark.asyncio
async def test_color_management_profile_inspects_profile_read_only() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["color_management_profile"](action="inspect")

    assert result["success"] is True
    assert result["operation"] == "color_management_profile"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_color_management_profile__" in generated
    assert "action = 'inspect'" in generated
    assert "image.get_color_profile()" in generated
    assert "image.get_effective_color_profile()" in generated
    assert "read_only" in generated
    assert "image.convert_color_profile" not in generated


@pytest.mark.asyncio
async def test_color_management_profile_rejects_conversion_without_confirmation() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["color_management_profile"](
        action="convert",
        profile_ref="sRGB",
        confirm=False,
    )

    assert result["success"] is False
    assert "confirm" in result["error"].lower()
    assert bridge.calls == []
