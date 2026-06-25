"""Focused tests for remaining tasks.issues.yml feature backlog items."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.color_tools import register_color_tools
from gimp_mcp_pro.tools.filter_tools import register_filter_tools
from gimp_mcp_pro.tools.history_tools import register_history_tools
from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_create_contact_sheet_builds_labeled_visible_layer_index() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["create_contact_sheet"](
        target="visible_layers",
        max_tile_size=96,
        label_tiles=True,
        include_hidden_layers=False,
    )

    assert result["success"] is True
    assert result["operation"] == "create_contact_sheet"
    generated = "\n".join(bridge.calls[-1][1])
    assert "include_hidden_layers = False" in generated
    assert "max_tile_size = 96" in generated
    assert "label_tiles = True" in generated
    assert "layer.get_id()" in generated
    assert "layer.get_visible()" in generated
    assert "tile_index.append" in generated
    assert "contact_sheet_png" in generated


@pytest.mark.asyncio
async def test_analyze_color_palette_generates_deterministic_region_palette_analysis() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["analyze_color_palette"](
        max_colors=5,
        ignore_transparent=True,
        region={"x": 1, "y": 2, "width": 8, "height": 6},
        layer_index=0,
    )

    assert result["success"] is True
    assert result["operation"] == "analyze_color_palette"
    generated = "\n".join(bridge.calls[-1][1])
    assert "max_colors = 5" in generated
    assert "ignore_transparent = True" in generated
    assert "region = {'x': 1, 'y': 2, 'width': 8, 'height': 6}" in generated
    assert "drawable.get_pixel" in generated
    assert "palette_counter" in generated
    assert "contrast_notes" in generated


@pytest.mark.asyncio
async def test_create_checkpoint_records_controlled_temp_checkpoint_metadata() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_history_tools(mcp, bridge)

    result = await mcp.tools["create_checkpoint"](
        label="before blur",
        include_xcf_copy=True,
    )

    assert result["success"] is True
    assert result["operation"] == "create_checkpoint"
    assert result["data"]["label"] == "before blur"
    generated = "\n".join(bridge.calls[-1][1])
    assert "tempfile.gettempdir()" in generated
    assert "gimp-mcp-checkpoints" in generated
    assert "checkpoint_id = str(uuid.uuid4())" in generated
    assert "image.duplicate()" in generated
    assert "xcf_path" in generated

    log_result = await mcp.tools["get_operation_log"](limit=5)
    assert log_result["success"] is True
    assert log_result["operation"] == "get_operation_log"
    assert log_result["data"]["operations"][0]["operation"] == "create_checkpoint"
    assert "local_file_path" not in str(log_result["data"])


@pytest.mark.asyncio
async def test_get_operation_log_redacts_paths_and_limits_entries() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_history_tools(mcp, bridge)

    await mcp.tools["create_checkpoint"](label="one", include_xcf_copy=False)
    await mcp.tools["create_checkpoint"](label="two", include_xcf_copy=True)

    result = await mcp.tools["get_operation_log"](limit=1, include_snapshots=False)

    assert result["success"] is True
    assert len(result["data"]["operations"]) == 1
    assert result["data"]["operations"][0]["label"] == "two"
    assert "gimp-mcp-checkpoints" not in str(result["data"])


@pytest.mark.asyncio
async def test_preview_filter_creates_temporary_layer_without_filtering_original() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["preview_filter"](
        filter="gaussian_blur",
        parameters={"radius_x": 3.0, "radius_y": 4.0},
        preview_mode="temporary_layer",
        layer_index=0,
    )

    assert result["success"] is True
    assert result["operation"] == "preview_filter"
    generated = "\n".join(bridge.calls[-1][1])
    assert "preview_layer = drawable.copy()" in generated
    assert "preview_layer.set_name" in generated
    assert "image.insert_layer(preview_layer" in generated
    assert "df = Gimp.DrawableFilter.new(preview_layer, 'gegl:gaussian-blur', '')" in generated
    assert "cfg.set_property('std-dev-x', 3.0)" in generated
    assert "drawable.append_filter" not in generated


@pytest.mark.asyncio
async def test_preview_filter_rejects_unknown_filter_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["preview_filter"](
        filter="unknown",
        parameters={},
    )

    assert result["success"] is False
    assert "Unsupported filter" in result["error"]
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_create_checkpoint_does_not_duplicate_image_without_xcf_copy() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_history_tools(mcp, bridge)

    result = await mcp.tools["create_checkpoint"](label="metadata only", include_xcf_copy=False)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "duplicate = image.duplicate()" not in generated
    assert "include_xcf_copy = False" in generated


@pytest.mark.asyncio
async def test_create_checkpoint_xcf_copy_releases_duplicate_image_ref() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_history_tools(mcp, bridge)

    result = await mcp.tools["create_checkpoint"](label="with copy", include_xcf_copy=True)

    assert result["success"] is True
    generated_items = bridge.calls[-1][1]
    generated = "\n".join(generated_items)
    assert "# __gimp_mcp_checkpoint_lifecycle__" in generated
    assert "duplicate = None" in generated
    assert "duplicate = image.duplicate()" in generated
    assert "finally:" in generated
    assert "duplicate.delete()" in generated
    assert "del duplicate" in generated
    assert "gc.collect()" in generated
    assert "try:" not in generated_items
