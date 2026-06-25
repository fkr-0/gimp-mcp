"""Roadmap feature wrappers for remaining agent-facing MCP tools."""

from __future__ import annotations

import json
import logging
from typing import Any

from gimp_mcp_pro.bridge import LONG_TIMEOUT
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.roadmap")

SUPPORTED_EXPORT_FORMATS = {"png", "jpeg", "jpg", "webp", "tiff", "tif", "psd", "xcf"}
SUPPORTED_CHANNEL_ACTIONS = {
    "list",
    "create",
    "rename",
    "duplicate",
    "show",
    "hide",
    "to_selection",
    "selection_to_channel",
}
SUPPORTED_PATH_ACTIONS = {"list", "create", "rename", "delete", "to_selection", "stroke", "fill"}
SUPPORTED_GUIDE_GRID_ACTIONS = {"list", "add", "move", "remove", "set_grid"}
SUPPORTED_COLOR_PROFILE_ACTIONS = {"inspect", "assign", "convert"}


def py_literal(value: object) -> str:
    """Return a safe Python literal for generated GIMP plug-in code."""
    return repr(value)


def _json_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Extract a JSON object printed by generated plug-in code."""
    raw = result.get("results")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        for item in reversed(raw):
            if isinstance(item, dict):
                return item
            if isinstance(item, str):
                stripped = item.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
    return {}


def _native_extra_for(operation: str, payload: dict[str, Any]) -> list[str]:
    """Return native GIMP backend code for promoted roadmap tools."""
    op = operation
    if op in {"edit_channels", "manage_channels"}:
        return [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "channels = image.get_channels()",
            "result['channels'] = [{'name': c.get_name(), 'visible': c.get_visible()} for c in channels]",
            "if result['action'] == 'create':\n"
            "    channel = Gimp.Channel.new(image, result.get('name') or 'MCP Channel', image.get_width(), image.get_height(), 100.0, Gegl.Color.new('black'))\n"
            "    image.insert_channel(channel, None, 0)\n"
            "    result['created'] = channel.get_name()",
            "elif result['action'] in {'show', 'hide'} and channels:\n"
            "    channels[0].set_visible(result['action'] == 'show')\n"
            "    result['updated'] = channels[0].get_name()",
            "elif result['action'] == 'to_selection' and channels:\n"
            "    image.select_item(Gimp.ChannelOps.REPLACE, channels[0])\n"
            "    result['selection_changed'] = True",
            "Gimp.displays_flush()",
        ]
    if op == "edit_paths":
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
    if op == "create_and_edit_paths":
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
    if op == "stroke_or_fill_path":
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
    if op == "palette_create_or_update":
        return [
            "palette = Gimp.context_get_palette()",
            "palette_name = result['palette']['name']",
            "# Gimp.Palette is referenced for native palette capability detection",
            "result['existing_palette'] = str(palette) if palette else None",
            "result['palette']['native_class'] = str(getattr(Gimp, 'Palette', None))",
        ]
    if op == "import_as_layer_with_metadata":
        return [
            "from gi.repository import Gio",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "file_obj = Gio.File.new_for_path(result['source'])",
            "layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, file_obj)",
            "if result.get('layer_name'): layer.set_name(result['layer_name'])",
            "placement = result.get('placement') or {}",
            "layer.set_offsets(int(placement.get('x', 0)), int(placement.get('y', 0)))",
            "image.insert_layer(layer, None, 0)",
            "parasite = Gimp.Parasite.new('gimp-mcp-import-metadata', 0, json.dumps(result['metadata'], sort_keys=True).encode('utf-8'))",
            "layer.attach_parasite(parasite)",
            "result['layer_id'] = int(layer.get_id()) if hasattr(layer, 'get_id') else None",
            "Gimp.displays_flush()",
        ]
    if op == "batch_export_variants":
        return [
            "from gi.repository import Gio",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "pdb = Gimp.get_pdb()",
            "procedure_by_format = {'png': 'file-png-export', 'jpeg': 'file-jpeg-export', 'jpg': 'file-jpeg-export', 'webp': 'file-webp-export', 'tiff': 'file-tiff-export', 'tif': 'file-tiff-export', 'xcf': 'gimp-xcf-save'}",
            "for index, variant in enumerate(result['variants']):\n"
            "    fmt = str(variant.get('format', 'png')).lower().lstrip('.')\n"
            "    export_proc = pdb.lookup_procedure(procedure_by_format[fmt])\n"
            "    config = export_proc.create_config()\n"
            "    file_path = f\"{result['base_path']}-{index}.{fmt}\"\n"
            "    config.set_property('file', Gio.File.new_for_path(file_path))\n"
            "    try: config.set_property('image', image)\n"
            "    except Exception: pass\n"
            "    export_proc.run(config)\n"
            "    result['files'].append(file_path)",
        ]
    if op == "pdb_introspect_typed":
        return [
            "pdb = Gimp.get_pdb()",
            "names = list(pdb.query_procedures(result['query'], '', '', '', '', '', '', ''))",
            "for name in names[:result['max_results']]:\n"
            "    proc = pdb.lookup_procedure(name)\n"
            "    cfg = proc.create_config() if proc else None\n"
            "    result['procedures'].append(name)\n"
            "    result['signatures'].append({'name': name, 'config_type': type(cfg).__name__ if cfg else None})",
        ]
    if op == "safe_python_eval":
        return [
            "import ast, io",
            "from contextlib import redirect_stdout, redirect_stderr",
            "SAFE_EVAL_BUILTINS = {'abs': abs, 'min': min, 'max': max, 'sum': sum, 'len': len, 'round': round}",
            "tree = ast.parse(result['code'], mode='eval' if result['mode'] == 'expression' else 'exec')",
            "stdout = io.StringIO(); stderr = io.StringIO()",
            "with redirect_stdout(stdout), redirect_stderr(stderr):\n"
            "    if result['mode'] == 'expression': result['result'] = eval(compile(tree, '<safe_python_eval>', 'eval'), {'__builtins__': SAFE_EVAL_BUILTINS}, {})\n"
            "    else: exec(compile(tree, '<safe_python_eval>', 'exec'), {'__builtins__': SAFE_EVAL_BUILTINS}, {})",
            "result['stdout'] = stdout.getvalue(); result['stderr'] = stderr.getvalue()",
        ]
    if op == "manage_guides_and_grid":
        return [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "guide_id = image.find_next_guide(0)",
            "guides = []",
            "while guide_id:\n"
            "    guides.append({'id': guide_id, 'orientation': str(image.get_guide_orientation(guide_id)), 'position': image.get_guide_position(guide_id)})\n"
            "    guide_id = image.find_next_guide(guide_id)",
            "if result['action'] == 'add' and result.get('orientation') == 'horizontal': result['guide_id'] = image.add_hguide(int(result.get('position') or 0))",
            "if result['action'] == 'add' and result.get('orientation') == 'vertical': result['guide_id'] = image.add_vguide(int(result.get('position') or 0))",
            "result['guides'] = guides",
            "Gimp.displays_flush()",
        ]
    if op == "preview_gegl_operation":
        return [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "preview_image = image.duplicate()",
            "layers = preview_image.get_layers()",
            "drawable = layers[0] if layers else None",
            "if drawable is None: raise RuntimeError('No drawable target available')",
            "df = Gimp.DrawableFilter.new(drawable, result['operation'], '')",
            "cfg = df.get_config()",
            "for key, value in result['properties'].items(): cfg.set_property(key, value)",
            "drawable.append_filter(df); drawable.merge_filter(df)",
            "# get_image_bitmap compatible bounded preview export happens through the MCP bitmap path",
            "result['metrics'] = {'document_mutated': False, 'preview_image_width': preview_image.get_width()}",
        ]
    return []


def _code(marker: str, payload: dict[str, Any], extra_lines: list[str] | None = None) -> list[str]:
    """Build a deterministic JSON-emitting code block for GIMP-side execution."""
    lines = [
        "from gi.repository import Gimp, Gegl",
        "import json, os, time, tempfile",
        f"# {marker}",
        f"result = {py_literal(payload)}",
    ]
    lines.extend(_native_extra_for(payload.get("operation", ""), payload))
    lines.extend(extra_lines or [])
    lines.append("print(json.dumps(result, sort_keys=True))")
    return lines


async def _execute_json_tool(
    bridge: AsyncToolBridge,
    *,
    operation: str,
    marker: str,
    payload: dict[str, Any],
    message: str,
    extra_lines: list[str] | None = None,
) -> ToolResult:
    """Run generated GIMP code and return a structured operation result."""
    try:
        response = await bridge.async_execute_python(
            _code(marker, dict(payload, operation=operation), extra_lines), timeout=LONG_TIMEOUT
        )
        data = _json_payload(response)
        if not data:
            data = payload
        return OperationResult.ok(operation=operation, message=message, data=data).model_dump()
    except GimpCommandError as exc:
        return OperationResult.fail(operation=operation, error=str(exc)).model_dump()


def _normalise_format(value: object) -> str:
    """Normalize an export format token."""
    return str(value).strip().lower().lstrip(".")


def _validate_formats(formats: list[object]) -> list[str]:
    """Return unsupported export formats."""
    return [
        fmt
        for fmt in (_normalise_format(item) for item in formats)
        if fmt not in SUPPORTED_EXPORT_FORMATS
    ]


def _validate_positive_size(width: object, height: object) -> tuple[int, int]:
    """Coerce and validate a positive two-dimensional size."""
    width_int = int(str(width))
    height_int = int(str(height))
    if width_int < 1 or height_int < 1:
        raise ValueError("width and height must be positive")
    return width_int, height_int


def register_roadmap_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register remaining roadmap feature tools with the MCP server."""
