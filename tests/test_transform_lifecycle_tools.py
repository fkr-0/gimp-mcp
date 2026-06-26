"""Lifecycle and context-safety tests for transform category generated code."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.transform_tools import register_transform_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_perspective_layer_restores_transform_context() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["perspective_layer"](
        x0=0,
        y0=0,
        x1=100,
        y1=0,
        x2=0,
        y2=90,
        x3=100,
        y3=90,
        interpolation="linear",
        resize="crop",
        layer_name="Photo",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_transform_context_lifecycle__" in generated
    assert "previous_interpolation = Gimp.context_get_interpolation()" in generated
    assert "previous_transform_resize = Gimp.context_get_transform_resize()" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "Gimp.context_set_interpolation(previous_interpolation)" in generated
    assert "Gimp.context_set_transform_resize(previous_transform_resize)" in generated
    assert "Gimp.context_set_interpolation(Gimp.InterpolationType.LINEAR)" in generated
    assert "Gimp.context_set_transform_resize(Gimp.TransformResize.CROP)" in generated
    assert "Gimp.Item.transform_perspective(target," in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_shear_layer_restores_transform_context() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["shear_layer"](
        direction="vertical",
        magnitude=12.5,
        interpolation="nohalo",
        resize="clip",
        layer_index=0,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_transform_context_lifecycle__" in generated
    assert "previous_interpolation = Gimp.context_get_interpolation()" in generated
    assert "previous_transform_resize = Gimp.context_get_transform_resize()" in generated
    assert "Gimp.context_set_interpolation(Gimp.InterpolationType.NOHALO)" in generated
    assert "Gimp.context_set_transform_resize(Gimp.TransformResize.CLIP)" in generated
    assert "Gimp.Item.transform_shear(target, Gimp.OrientationType.VERTICAL, 12.5)" in generated
    assert "Gimp.context_set_interpolation(previous_interpolation)" in generated
    assert "Gimp.context_set_transform_resize(previous_transform_resize)" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_autocrop_image_releases_pdb_config_and_proc_refs() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["autocrop_image"]()

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_autocrop_lifecycle__" in generated
    assert "pdb = None" in generated
    assert "proc = None" in generated
    assert "cfg = None" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "proc.run(cfg)" in generated
    assert "del cfg" in generated
    assert "del proc" in generated
    assert "del pdb" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "kwargs", "marker", "mutation"),
    [
        (
            "scale_image",
            {"new_width": 640, "new_height": 480, "interpolation": "linear"},
            "__gimp_mcp_transform_image_lifecycle__",
            "image.scale(640, 480)",
        ),
        (
            "scale_layer",
            {"new_width": 320, "new_height": 240, "interpolation": "nohalo", "layer_name": "Paint"},
            "__gimp_mcp_transform_layer_lifecycle__",
            "target.scale(320, 240, True)",
        ),
        (
            "rotate_image",
            {"angle": 90},
            "__gimp_mcp_transform_image_lifecycle__",
            "image.rotate(Gimp.RotationType.DEGREES90)",
        ),
        (
            "rotate_layer",
            {"angle_degrees": 15.0, "layer_name": "Paint"},
            "__gimp_mcp_transform_layer_lifecycle__",
            "Gimp.Item.transform_rotate(target, angle_rad, True, cx, cy)",
        ),
        (
            "flip_image",
            {"direction": "vertical"},
            "__gimp_mcp_transform_image_lifecycle__",
            "image.flip(Gimp.OrientationType.VERTICAL)",
        ),
        (
            "flip_layer",
            {"direction": "horizontal", "layer_name": "Paint"},
            "__gimp_mcp_transform_layer_lifecycle__",
            "Gimp.Item.transform_flip_simple(target, Gimp.OrientationType.HORIZONTAL, True, 0)",
        ),
        (
            "crop_to_selection",
            {},
            "__gimp_mcp_transform_image_lifecycle__",
            "image.crop(bounds.x2 - bounds.x1, bounds.y2 - bounds.y1, bounds.x1, bounds.y1)",
        ),
        (
            "crop_image",
            {"x": 1, "y": 2, "width": 100, "height": 80},
            "__gimp_mcp_transform_image_lifecycle__",
            "image.crop(100, 80, 1, 2)",
        ),
        (
            "resize_canvas",
            {"new_width": 800, "new_height": 600, "offset_x": 10, "offset_y": 20},
            "__gimp_mcp_transform_image_lifecycle__",
            "image.resize(800, 600, 10, 20)",
        ),
        (
            "offset_layer",
            {"offset_x": 5, "offset_y": -7, "layer_name": "Paint"},
            "__gimp_mcp_transform_layer_lifecycle__",
            "target.set_offsets(target.get_offsets().offset_x + 5, target.get_offsets().offset_y + -7)",
        ),
    ],
)
async def test_remaining_transform_primitives_use_undo_lifecycle(
    tool_name: str,
    kwargs: dict[str, object],
    marker: str,
    mutation: str,
) -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools[tool_name](**kwargs)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert f"# {marker}" in generated
    assert "undo_started = False" in generated
    assert "image.undo_group_start()" in generated
    assert "undo_started = True" in generated
    assert mutation in generated
    assert "image.undo_group_end()" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_scale_operations_restore_interpolation_context() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["scale_image"](new_width=640, new_height=480, interpolation="linear")
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "previous_interpolation = Gimp.context_get_interpolation()" in generated
    assert "Gimp.context_set_interpolation(Gimp.InterpolationType.LINEAR)" in generated
    assert "Gimp.context_set_interpolation(previous_interpolation)" in generated

    result = await mcp.tools["scale_layer"](
        new_width=320, new_height=240, interpolation="nohalo", layer_name="Paint"
    )
    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "previous_interpolation = Gimp.context_get_interpolation()" in generated
    assert "Gimp.context_set_interpolation(Gimp.InterpolationType.NOHALO)" in generated
    assert "Gimp.context_set_interpolation(previous_interpolation)" in generated
