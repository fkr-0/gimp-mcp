"""Native path operation code generators."""

from __future__ import annotations

from typing import Any

from gimp_mcp_pro.tools.native_backend import (
    NativeOperation,
)


def _op_edit_paths(payload: dict[str, Any]) -> list[str]:
    return [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "paths = image.get_paths()",
        "result['paths'] = [{'name': p.get_name()} for p in paths]",
        "if result['action'] == 'to_selection' and paths:\n"
        "    image.select_item(Gimp.ChannelOps.REPLACE, paths[0])\n"
        "    result['selection_changed'] = True",
    ]


def _op_create_and_edit_paths(payload: dict[str, Any]) -> list[str]:
    return [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "paths = image.get_paths()",
        "if result['action'] == 'create':\n"
        "    path = Gimp.Path.new(image, result.get('name') or 'MCP Path')\n"
        "    raw_points = result.get('points') or []\n"
        "    points = []\n"
        "    for point in raw_points:\n"
        "        if isinstance(point, dict): points.extend([float(point.get('x', 0)), float(point.get('y', 0)), 0.0, 0.0, float(point.get('x', 0)), float(point.get('y', 0))])\n"
        "    if len(points) >= 6: path.stroke_new_from_points(Gimp.PathStrokeType.BEZIER, points, bool(result.get('closed')))\n"
        "    image.insert_path(path, None, 0)\n"
        "    result['active_path'] = {'name': path.get_name()}\n"
        "result['paths'] = [{'name': p.get_name()} for p in image.get_paths()]",
    ]


def _op_stroke_or_fill_path(payload: dict[str, Any]) -> list[str]:
    return [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "paths = image.get_paths()",
        "if not paths: raise RuntimeError('No paths available')",
        "target_path = paths[0]",
        "layers = image.get_layers()",
        "drawable = layers[0] if layers else None",
        "if drawable is None: raise RuntimeError('No drawable target available')",
        "if result['mode'] == 'stroke':\n"
        "    drawable.edit_stroke_item(target_path)\n"
        "else:\n"
        "    image.select_item(Gimp.ChannelOps.REPLACE, target_path)\n"
        "    drawable.edit_fill(Gimp.FillType.FOREGROUND)",
        "result['changed_bounds'] = {'source': 'path'}",
        "Gimp.displays_flush()",
    ]


def operations() -> dict[str, NativeOperation]:
    """Return registered native backend operations for this concern."""
    return {
        "edit_paths": NativeOperation(
            name="edit_paths", generator=_op_edit_paths, required_payload_keys=("action",)
        ),
        "create_and_edit_paths": NativeOperation(
            name="create_and_edit_paths",
            generator=_op_create_and_edit_paths,
            required_payload_keys=("action",),
        ),
        "stroke_or_fill_path": NativeOperation(
            name="stroke_or_fill_path",
            generator=_op_stroke_or_fill_path,
            required_payload_keys=("mode",),
        ),
    }
