"""Lifecycle and leak-safety tests for layer category generated code."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.layer_tools import register_layer_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_create_visual_annotation_layer_cleans_up_partial_layer_on_failure() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["create_visual_annotation_layer"](
        annotations=[{"type": "box", "x": 1, "y": 2, "width": 10, "height": 12}],
        layer_name="MCP temporary annotations",
        temporary=True,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_annotation_lifecycle__" in generated
    assert "layer = None" in generated
    assert "parasite = None" in generated
    assert "try:" in generated
    assert "except Exception:" in generated
    assert "image.remove_layer(layer)" in generated
    assert "raise" in generated
    assert "del parasite" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_layer_version_stamp_replaces_existing_parasite_and_releases_refs() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["layer_version_stamp"](
        target={"layer_name": "Paint"},
        metadata={"operation": "paint"},
        merge=True,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_version_lifecycle__" in generated
    assert "old_parasite = None" in generated
    assert "parasite = None" in generated
    assert "layer.detach_parasite(metadata_namespace)" in generated
    assert "layer.attach_parasite(parasite)" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "del old_parasite" in generated
    assert "del parasite" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_set_layer_mode_has_focused_generated_code_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["set_layer_mode"](blend_mode="multiply", layer_name="Paint")

    assert result["success"] is True
    assert result["operation"] == "set_layer_mode"
    generated = "\n".join(bridge.calls[-1][1])
    assert "target = image.get_layer_by_name('Paint')" in generated
    assert "target.set_mode(Gimp.LayerMode.MULTIPLY)" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_set_layer_mode_rejects_unknown_mode_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["set_layer_mode"](blend_mode="surely-not-a-mode")

    assert result["success"] is False
    assert "unknown blend mode" in result["error"].lower()
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_core_layer_create_delete_duplicate_lifecycle_contracts() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["create_layer"](
        name="Paint",
        opacity=75.0,
        fill="transparent",
        position=0,
    )
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_create_lifecycle__" in generated
    assert "layer = None" in generated
    assert "inserted_layer = False" in generated
    assert "try:" in generated
    assert "except Exception:" in generated
    assert "image.remove_layer(layer)" in generated
    assert "Gimp.Drawable.edit_fill(layer, Gimp.FillType.TRANSPARENT)" in generated
    assert "del layer" in generated
    assert "gc.collect()" in generated

    result = await mcp.tools["delete_layer"](layer_name="Paint")
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_delete_lifecycle__" in generated
    assert "layers = image.get_layers()" in generated
    assert "if len(layers) <= 1: raise RuntimeError('Cannot delete the only layer')" in generated
    assert "image.remove_layer(target)" in generated
    assert "Gimp.displays_flush()" in generated

    result = await mcp.tools["duplicate_layer"](layer_name="Paint", new_name="Paint copy")
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_duplicate_lifecycle__" in generated
    assert "dup = None" in generated
    assert "inserted_duplicate = False" in generated
    assert "dup = target.copy()" in generated
    assert "dup.set_name('Paint copy')" in generated
    assert "image.insert_layer(dup, None, 0)" in generated
    assert "image.remove_layer(dup)" in generated
    assert "del dup" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_remaining_core_layer_lifecycle_contracts() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["set_active_layer"](layer_name="Paint")
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_active_lifecycle__" in generated
    assert "previous_selected_layers = image.get_selected_layers()" in generated
    assert "try:" in generated
    assert "except Exception:" in generated
    assert "image.set_selected_layers(previous_selected_layers)" in generated
    assert "image.set_selected_layers([target])" in generated
    assert "gc.collect()" in generated

    result = await mcp.tools["set_layer_opacity"](opacity=42.0, layer_name="Paint")
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_opacity_lifecycle__" in generated
    assert "previous_opacity = target.get_opacity()" in generated
    assert "target.set_opacity(42.0)" in generated
    assert "target.set_opacity(previous_opacity)" in generated
    assert "gc.collect()" in generated

    result = await mcp.tools["merge_visible_layers"]()
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_merge_lifecycle__" in generated
    assert (
        "visible_layers = [layer for layer in image.get_layers() if layer.get_visible()]"
        in generated
    )
    assert (
        "if len(visible_layers) < 2: raise RuntimeError('Need at least two visible layers to merge')"
        in generated
    )
    assert "image.undo_group_start()" in generated
    assert "image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)" in generated
    assert "image.undo_group_end()" in generated
    assert "gc.collect()" in generated

    result = await mcp.tools["add_alpha_channel"](layer_name="Paint")
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_alpha_lifecycle__" in generated
    assert "already_had_alpha = target.has_alpha()" in generated
    assert "if not already_had_alpha:" in generated
    assert "target.add_alpha()" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_create_layer_activates_new_layer_by_default() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["create_layer"](name="Fresh Paint")

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "if True: image.set_selected_layers([layer])" in generated
    assert result["data"]["active"] is True


@pytest.mark.asyncio
async def test_new_layer_from_visible_generates_non_destructive_composite_layer() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["new_layer_from_visible"](name="Composite", activate=True)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "Gimp.Layer.new_from_visible(image, image, 'Composite')" in generated
    assert "image.insert_layer(layer, None, 0)" in generated
    assert "if True: image.set_selected_layers([layer])" in generated


@pytest.mark.asyncio
async def test_merge_down_uses_gimp_image_merge_down_api() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["merge_down"](layer_index=0)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "merged = image.merge_down(target, Gimp.MergeType.CLIP_TO_IMAGE)" in generated
    assert "image.set_selected_layers([merged])" in generated


@pytest.mark.asyncio
async def test_copy_layer_alpha_to_mask_uses_select_item_and_selection_mask() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["copy_layer_alpha_to_mask"](
        source_layer_index=0,
        target_layer_index=1,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "image.select_item(Gimp.ChannelOps.REPLACE, source)" in generated
    assert "target.create_mask(Gimp.AddMaskType.SELECTION)" in generated
    assert "target.add_mask(mask)" in generated
