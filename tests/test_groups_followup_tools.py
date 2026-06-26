"""Direct coverage follow-ups for selected groups.yml findings."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.drawing_tools import register_drawing_tools
from gimp_mcp_pro.tools.filter_tools import register_filter_tools
from gimp_mcp_pro.tools.history_tools import register_history_tools
from gimp_mcp_pro.tools.image_tools import register_image_tools
from gimp_mcp_pro.tools.layer_tools import register_layer_tools
from gimp_mcp_pro.tools.path_tools import register_path_tools
from gimp_mcp_pro.tools.pdb_tools import register_pdb_tools
from gimp_mcp_pro.tools.selection_tools import register_selection_tools
from gimp_mcp_pro.tools.transform_tools import register_transform_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


def generated_source(bridge: ScriptedBridge) -> str:
    return "\n".join(bridge.calls[-1][1])


@pytest.mark.asyncio
async def test_selection_primitives_have_direct_generated_code_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_selection_tools(mcp, bridge)

    result = await mcp.tools["select_rectangle"](
        x=1,
        y=2,
        width=30,
        height=40,
        operation="add",
        feather_radius=2.0,
    )
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "Gimp.Image.select_rectangle(image, Gimp.ChannelOps.ADD, 1, 2, 30, 40)" in generated
    assert "Gimp.Selection.feather(image, 2.0)" in generated
    assert "Gimp.displays_flush()" in generated

    result = await mcp.tools["select_ellipse"](
        x=3,
        y=4,
        width=20,
        height=10,
        operation="intersect",
    )
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "Gimp.Image.select_ellipse(image, Gimp.ChannelOps.INTERSECT, 3, 4, 20, 10)" in generated
    assert "Gimp.displays_flush()" in generated

    result = await mcp.tools["select_polygon"](
        points=[0, 0, 10, 0, 10, 10],
        operation="subtract",
    )
    assert result["success"] is True
    generated = generated_source(bridge)
    assert (
        "Gimp.Image.select_polygon(image, Gimp.ChannelOps.SUBTRACT, [0, 0, 10, 0, 10, 10])"
        in generated
    )
    assert "Gimp.displays_flush()" in generated

    assert (await mcp.tools["select_all"]())["success"] is True
    assert "Gimp.Selection.all(images[0])" in generated_source(bridge)

    assert (await mcp.tools["select_none"]())["success"] is True
    assert "Gimp.Selection.none(images[0])" in generated_source(bridge)

    assert (await mcp.tools["select_invert"]())["success"] is True
    assert "Gimp.Selection.invert(images[0])" in generated_source(bridge)

    invalid_polygon = await mcp.tools["select_polygon"](points=[0, 0, 1])
    assert invalid_polygon["success"] is False
    assert "at least 3 points" in invalid_polygon["error"]


@pytest.mark.asyncio
async def test_history_redo_and_undo_group_tools_have_direct_generated_code_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_history_tools(mcp, bridge)

    result = await mcp.tools["begin_undo_group"]("Batch edit")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.undo_group_start()" in generated

    result = await mcp.tools["end_undo_group"]()
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.undo_group_end()" in generated

    result = await mcp.tools["redo"](steps=1)
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "pdb.lookup_procedure('gimp-image-redo')" in generated
    assert "cfg.set_property('image', image)" in generated
    assert "proc.run(cfg)" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_image_introspection_tools_have_direct_generated_code_and_metadata_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["list_images"]()
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "images = Gimp.get_images()" in generated
    assert "img.get_width()" in generated
    assert "img.get_height()" in generated
    assert "print(json.dumps(result))" in generated

    result = await mcp.tools["get_image_info"]()
    assert result["success"] is True
    assert bridge.calls[-1] == ("get_image_metadata", None)
    assert result["data"]["basic"]["width"] == 320


@pytest.mark.asyncio
async def test_remaining_drawing_matrix_only_tools_have_direct_generated_code_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_drawing_tools(mcp, bridge)

    result = await mcp.tools["set_foreground_color"]("#102030")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "Gimp.context_set_foreground(_color)" in generated
    assert "Gegl.Color.new('#102030')" in generated

    result = await mcp.tools["set_background_color"]("#405060")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "Gimp.context_set_background(_color)" in generated
    assert "Gegl.Color.new('#405060')" in generated

    result = await mcp.tools["edit_clear"]()
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "Gimp.Drawable.edit_clear(drawable)" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_layer_matrix_only_tools_have_direct_generated_code_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["create_layer"](name="Paint", opacity=75, fill="transparent")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "# __gimp_mcp_layer_create_lifecycle__" in generated
    assert "Gimp.Layer.new(image, 'Paint'" in generated
    assert "image.insert_layer(layer, None, 0)" in generated

    result = await mcp.tools["list_layers"]()
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "layers = image.get_layers()" in generated
    assert "print(json.dumps(result))" in generated

    result = await mcp.tools["set_active_layer"](layer_name="Paint")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.set_selected_layers([target])" in generated

    result = await mcp.tools["delete_layer"](layer_name="Paint")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.remove_layer(target)" in generated
    assert "Cannot delete the only layer" in generated

    result = await mcp.tools["set_layer_opacity"](opacity=42, layer_index=0)
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "target.set_opacity(42)" in generated

    result = await mcp.tools["duplicate_layer"](layer_name="Paint", new_name="Paint copy")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "dup = None" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "dup = target.copy()" in generated
    assert "image.insert_layer(dup, None, 0)" in generated

    result = await mcp.tools["merge_visible_layers"]()
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)" in generated

    result = await mcp.tools["add_alpha_channel"](layer_index=0)
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "already_had_alpha = target.has_alpha()" in generated
    assert "if not already_had_alpha:" in generated
    assert "target.add_alpha()" in generated


@pytest.mark.asyncio
async def test_transform_matrix_only_tools_have_direct_generated_code_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["scale_layer"](
        new_width=120, new_height=80, interpolation="linear", layer_index=0
    )
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "Gimp.context_set_interpolation(Gimp.InterpolationType.LINEAR)" in generated
    assert "target.scale(120, 80, True)" in generated

    result = await mcp.tools["rotate_image"](angle=90)
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.rotate(Gimp.RotationType.DEGREES90)" in generated

    result = await mcp.tools["rotate_layer"](
        angle_degrees=45.0, auto_resize=False, layer_name="Photo"
    )
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "Gimp.Item.transform_rotate(target, angle_rad, False, cx, cy)" in generated

    result = await mcp.tools["flip_image"](direction="vertical")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.flip(Gimp.OrientationType.VERTICAL)" in generated

    result = await mcp.tools["flip_layer"](direction="horizontal", layer_index=0)
    assert result["success"] is True
    generated = generated_source(bridge)
    assert (
        "Gimp.Item.transform_flip_simple(target, Gimp.OrientationType.HORIZONTAL, True, 0)"
        in generated
    )

    result = await mcp.tools["crop_to_selection"]()
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "bounds = Gimp.Selection.bounds(image)" in generated
    assert (
        "image.crop(bounds.x2 - bounds.x1, bounds.y2 - bounds.y1, bounds.x1, bounds.y1)"
        in generated
    )

    result = await mcp.tools["crop_image"](x=1, y=2, width=30, height=40)
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.crop(30, 40, 1, 2)" in generated

    result = await mcp.tools["resize_canvas"](new_width=640, new_height=480, offset_x=5, offset_y=6)
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "image.resize(640, 480, 5, 6)" in generated
    assert "layer.resize_to_image_size()" in generated

    result = await mcp.tools["offset_layer"](offset_x=7, offset_y=8, layer_name="Photo")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "target.set_offsets(target.get_offsets().offset_x + 7" in generated
    assert "target.get_offsets().offset_y + 8)" in generated


@pytest.mark.asyncio
async def test_path_lifecycle_tools_restore_context_and_wrap_mutations() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_path_tools(mcp, bridge)

    result = await mcp.tools["create_path"](points=[0, 0, 10, 0, 10, 10], name="Triangle")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "# __gimp_mcp_path_create_lifecycle__" in generated
    assert "path = None" in generated
    assert "inserted_path = False" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.Path.new(image, 'Triangle')" in generated
    assert "image.insert_path(path, None, 0)" in generated
    assert "image.remove_path(path)" in generated
    assert "del path" in generated
    assert "gc.collect()" in generated

    result = await mcp.tools["stroke_path"](path_name="Triangle", color="#112233", brush_size=3.5)
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "# __gimp_mcp_path_stroke_context_lifecycle__" in generated
    assert "previous_foreground = Gimp.context_get_foreground()" in generated
    assert "previous_line_width = Gimp.context_get_line_width()" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.context_set_foreground(Gegl.Color.new('#112233'))" in generated
    assert "Gimp.context_set_line_width(3.5)" in generated
    assert "drawable.edit_stroke_item(target)" in generated
    assert "Gimp.context_set_foreground(previous_foreground)" in generated
    assert "Gimp.context_set_line_width(previous_line_width)" in generated
    assert "gc.collect()" in generated

    result = await mcp.tools["remove_path"](path_name="Triangle")
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "# __gimp_mcp_path_remove_lifecycle__" in generated
    assert "image.undo_group_start()" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "image.remove_path(target)" in generated
    assert "image.undo_group_end()" in generated


@pytest.mark.asyncio
async def test_classic_filter_wrappers_have_direct_lifecycle_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    cases = [
        (
            "apply_pixelize",
            {"block_width": 8, "block_height": 12},
            "gegl:pixelize",
            "cfg.set_property('size-x', 8)",
        ),
        (
            "apply_edge_detect",
            {"method": "sobel", "amount": 2.5},
            "gegl:edge",
            "cfg.set_property('amount', 2.5)",
        ),
        (
            "apply_emboss",
            {"azimuth": 315.0, "elevation": 40.0, "depth": 3},
            "gegl:emboss",
            "cfg.set_property('depth', 3)",
        ),
        (
            "apply_noise",
            {"amount": 0.4},
            "gegl:noise-hsv",
            "cfg.set_property('value-distance', 0.4)",
        ),
        ("apply_median", {"radius": 5}, "gegl:median-blur", "cfg.set_property('radius', 5)"),
    ]

    for tool_name, kwargs, gegl_op, property_line in cases:
        result = await mcp.tools[tool_name](**kwargs)
        assert result["success"] is True
        generated = generated_source(bridge)
        assert "# __gimp_mcp_filter_lifecycle__" in generated
        assert f"Gimp.DrawableFilter.new(drawable, '{gegl_op}', '')" in generated
        assert property_line in generated
        assert "drawable.append_filter(df)" in generated
        assert "drawable.merge_filter(df)" in generated
        assert "drawable.remove_filter(df)" in generated
        assert "del cfg" in generated
        assert "del df" in generated
        assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_discard_filter_preview_uses_same_undo_lifecycle_as_commit() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["commit_filter_preview"]("preview-layer", action="discard")

    assert result["success"] is True
    generated = generated_source(bridge)
    assert "# __gimp_mcp_commit_filter_preview__" in generated
    assert "image.undo_group_start()" in generated
    assert "try:" in generated
    assert "image.remove_layer(preview_layer)" in generated
    assert "finally:" in generated
    assert "image.undo_group_end()" in generated
    assert "transaction_wrapped': True" in generated


@pytest.mark.asyncio
async def test_execute_python_is_disabled_by_default_and_requires_explicit_debug_intent() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_pdb_tools(mcp, bridge)

    default_result = await mcp.tools["execute_python"](["print('unsafe')"])

    assert default_result["success"] is False
    assert "disabled by default" in default_result["error"]
    assert bridge.calls == []

    missing_intent = await mcp.tools["execute_python"](
        ["print('unsafe')"],
        require_debug_enabled=True,
    )

    assert missing_intent["success"] is False
    assert "allow_dangerous_code=true" in missing_intent["error"]
    assert bridge.calls == []

    enabled = await mcp.tools["execute_python"](
        ["print('ok')"],
        require_debug_enabled=True,
        allow_dangerous_code=True,
    )

    assert enabled["success"] is True
    assert bridge.calls[-1][0] == "execute_python"
    assert bridge.calls[-1][1] == ["print('ok')"]


@pytest.mark.asyncio
async def test_image_mutators_emit_undo_lifecycle_code() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["set_image_grid"](
        xspacing=16,
        yspacing=24,
        xoffset=2,
        yoffset=3,
        style="solid",
    )
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "# __gimp_mcp_image_grid_lifecycle__" in generated
    assert "image.undo_group_start()" in generated
    assert "try:" in generated
    assert "image.grid_set_spacing(16.0, 24.0)" in generated
    assert "image.grid_set_offset(2.0, 3.0)" in generated
    assert "image.grid_set_style(Gimp.GridStyle.SOLID)" in generated
    assert "finally:" in generated
    assert "image.undo_group_end()" in generated

    result = await mcp.tools["flatten_image"]()
    assert result["success"] is True
    generated = generated_source(bridge)
    assert "# __gimp_mcp_image_flatten_lifecycle__" in generated
    assert "image.undo_group_start()" in generated
    assert "try:" in generated
    assert "image.flatten()" in generated
    assert "finally:" in generated
    assert "image.undo_group_end()" in generated


@pytest.mark.asyncio
async def test_create_image_rolls_back_new_image_on_layer_fill_failure() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["create_image"](width=64, height=32, fill="white")

    assert result["success"] is True
    generated = generated_source(bridge)
    assert "# __gimp_mcp_create_image_lifecycle__" in generated
    assert "image = None" in generated
    assert "layer = None" in generated
    assert "created_image = False" in generated
    assert "try:" in generated
    assert "image = Gimp.Image.new(64, 32" in generated
    assert "Gimp.Layer.new(image, 'Background', 64, 32" in generated
    assert "Gimp.Drawable.edit_fill(layer, Gimp.FillType.WHITE)" in generated
    assert "except Exception:" in generated
    assert "if created_image and image is not None:" in generated
    assert "image.delete()" in generated
    assert "finally:" in generated
    assert "del layer" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_history_undo_groups_can_be_recovered_when_caller_loses_group_ids() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_history_tools(mcp, bridge)

    first = await mcp.tools["begin_undo_group"]("first")
    second = await mcp.tools["begin_undo_group"]("second")

    assert first["success"] is True
    assert second["success"] is True
    assert first["data"]["group_id"].startswith("undo-")
    assert second["data"]["group_id"].startswith("undo-")

    recovered = await mcp.tools["end_undo_group"](close_all=True)

    assert recovered["success"] is True
    assert recovered["data"]["closed_count"] == 2
    assert recovered["data"]["closed_group_ids"] == [
        second["data"]["group_id"],
        first["data"]["group_id"],
    ]
    generated = generated_source(bridge)
    assert "# __gimp_mcp_history_close_all_undo_groups__" in generated
    assert generated.count("image.undo_group_end()") == 2
