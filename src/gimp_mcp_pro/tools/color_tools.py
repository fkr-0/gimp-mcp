"""Color adjustment tools for GIMP MCP Pro.

Covers brightness/contrast, levels, curves, hue-saturation, desaturation,
color inversion, threshold, posterize, and color-to-alpha.
"""

from __future__ import annotations

import logging
from typing import Any

from gimp_mcp_pro.bridge import LONG_TIMEOUT
from gimp_mcp_pro.models.common import Color, OperationResult, py_literal
from gimp_mcp_pro.tools.roadmap_tools import _execute_json_tool
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.color")


def _color_preamble(layer_name: str | None, layer_index: int | None) -> list[str]:
    """Standard preamble for color adjustment tools."""
    code = [
        "from gi.repository import Gimp, Gegl",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
    ]
    if layer_name is not None:
        layer_name_expr = py_literal(layer_name)
        layer_error_expr = py_literal(f"Layer {layer_name!r} not found")
        code += [
            f"drawable = image.get_layer_by_name({layer_name_expr})",
            f"if drawable is None: raise RuntimeError({layer_error_expr})",
        ]
    elif layer_index is not None:
        code += [
            "layers = image.get_layers()",
            f"drawable = layers[{layer_index}]",
        ]
    else:
        code += [
            "sel = image.get_selected_layers()",
            "if not sel: raise RuntimeError('No active layer')",
            "drawable = sel[0]",
        ]
    return code


def _normalise_sample_points(
    points: list[dict[str, Any]] | None,
    grid: dict[str, Any] | None,
) -> tuple[list[dict[str, float]], int]:
    """Validate sample point and grid request shape for sample_pixels."""
    normalised: list[dict[str, float]] = []
    for point in points or []:
        normalised.append({"x": float(point["x"]), "y": float(point["y"])})

    grid_count = 0
    if grid is not None:
        columns = int(grid.get("columns", 1))
        rows = int(grid.get("rows", 1))
        width = float(grid.get("width", 0))
        height = float(grid.get("height", 0))
        if columns < 1 or rows < 1:
            raise ValueError("grid columns and rows must be >= 1")
        if width < 0 or height < 0:
            raise ValueError("grid width and height must be >= 0")
        grid_count = columns * rows
    return normalised, len(normalised) + grid_count


def _sample_pixels_code(
    points: list[dict[str, float]],
    grid: dict[str, Any] | None,
    *,
    sample_merged: bool,
    sample_average: bool,
    average_radius: float,
    layer_name: str | None,
    layer_index: int | None,
) -> list[str]:
    """Return generated GIMP Python code for point/grid color sampling."""
    code = [
        "import json",
        "from gi.repository import Gimp, Gegl",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
    ]
    if layer_name is not None:
        layer_name_expr = py_literal(layer_name)
        layer_error_expr = py_literal(f"Layer {layer_name!r} not found")
        code += [
            f"drawable = image.get_layer_by_name({layer_name_expr})",
            f"if drawable is None: raise RuntimeError({layer_error_expr})",
        ]
    elif layer_index is not None:
        code += [
            "layers = image.get_layers()",
            f"drawable = layers[{layer_index}]",
        ]
    else:
        code += [
            "sel = image.get_selected_layers()",
            "if not sel: raise RuntimeError('No active layer')",
            "drawable = sel[0]",
        ]

    code += [
        "drawables = [drawable]",
        f"sample_points = {py_literal(points)}",
    ]
    if grid is not None:
        x = float(grid.get("x", 0))
        y = float(grid.get("y", 0))
        width = float(grid.get("width", 0))
        height = float(grid.get("height", 0))
        columns = int(grid.get("columns", 1))
        rows = int(grid.get("rows", 1))
        code += [
            f"for row in range({rows}):",
            f"    py = {y!r} if {rows} == 1 else {y!r} + ({height!r} * row / ({rows} - 1))",
            f"    for col in range({columns}):",
            f"        px = {x!r} if {columns} == 1 else {x!r} + ({width!r} * col / ({columns} - 1))",
            "        sample_points.append({'x': px, 'y': py})",
        ]

    pick_expr = (
        "image.pick_color(drawables, x, y, "
        f"{sample_merged!r}, {sample_average!r}, {average_radius!r})"
    )
    code += [
        "def color_to_dict(color):\n"
        "    rgba = color.get_rgba()\n"
        "    return {'r': round(rgba.red, 4), 'g': round(rgba.green, 4), 'b': round(rgba.blue, 4), 'a': round(rgba.alpha, 4)}",
        "def color_to_hex(color):\n"
        "    rgba = color.get_rgba()\n"
        "    return '#%02x%02x%02x' % (int(max(0, min(1, rgba.red)) * 255), int(max(0, min(1, rgba.green)) * 255), int(max(0, min(1, rgba.blue)) * 255))",
        "samples = []",
        (
            "for point in sample_points:\n"
            "    x = float(point['x'])\n"
            "    y = float(point['y'])\n"
            "    try:\n"
            + (
                f"        picked = {pick_expr}\n"
                "        if isinstance(picked, tuple):\n"
                "            ok = bool(picked[0])\n"
                "            color = picked[-1]\n"
                "        else:\n"
                "            ok = picked is not None\n"
                "            color = picked\n"
                "        if not ok or color is None: raise RuntimeError('no color returned')\n"
                if sample_merged
                else "        color = drawable.get_pixel(int(round(x)), int(round(y)))\n"
            )
            + "        samples.append({'x': x, 'y': y, 'rgba': color_to_dict(color), 'hex': color_to_hex(color)})\n"
            + "    except Exception as exc:\n"
            + "        samples.append({'x': x, 'y': y, 'error': str(exc)})"
        ),
        "print(json.dumps({'samples': samples, 'color_space': 'rgba', 'sample_merged': "
        f"{sample_merged!r}, 'sample_average': {sample_average!r}, 'average_radius': {average_radius!r}}}))",
    ]
    return code


def _palette_analysis_code(
    max_colors: int,
    ignore_transparent: bool,
    region: dict[str, Any] | None,
    layer_name: str | None,
    layer_index: int | None,
) -> list[str]:
    """Return generated GIMP Python code for deterministic palette analysis."""
    code = _color_preamble(layer_name, layer_index)
    code = ["import json", "from collections import Counter"] + code
    code += [
        f"max_colors = {max_colors!r}",
        f"ignore_transparent = {ignore_transparent!r}",
        f"region = {py_literal(region)}",
        "def color_to_tuple(color):\n"
        "    rgba = color.get_rgba()\n"
        "    return (int(max(0, min(1, rgba.red)) * 255), int(max(0, min(1, rgba.green)) * 255), int(max(0, min(1, rgba.blue)) * 255), int(max(0, min(1, rgba.alpha)) * 255))",
        "def rel_luminance(rgb):\n"
        "    r, g, b = [channel / 255.0 for channel in rgb[:3]]\n"
        "    return 0.2126 * r + 0.7152 * g + 0.0722 * b",
        "width = drawable.get_width()",
        "height = drawable.get_height()",
        "left = int(region.get('x', 0)) if region else 0",
        "top = int(region.get('y', 0)) if region else 0",
        "right = min(width, left + int(region.get('width', width))) if region else width",
        "bottom = min(height, top + int(region.get('height', height))) if region else height",
        "step_x = max(1, (right - left) // 32 or 1)",
        "step_y = max(1, (bottom - top) // 32 or 1)",
        "palette_counter = Counter()",
        "sampled = 0",
        "transparent_skipped = 0",
        "for y in range(top, bottom, step_y):\n"
        "    for x in range(left, right, step_x):\n"
        "        try:\n"
        "            rgba = color_to_tuple(drawable.get_pixel(x, y))\n"
        "        except Exception:\n"
        "            continue\n"
        "        sampled += 1\n"
        "        if ignore_transparent and rgba[3] == 0:\n"
        "            transparent_skipped += 1\n"
        "            continue\n"
        "        bucket = (rgba[0] // 16 * 16, rgba[1] // 16 * 16, rgba[2] // 16 * 16, rgba[3])\n"
        "        palette_counter[bucket] += 1",
        "total = sum(palette_counter.values()) or 1",
        "palette = []",
        "for rgba, count in palette_counter.most_common(max_colors):\n"
        "    hex_value = '#%02x%02x%02x' % rgba[:3]\n"
        "    palette.append({'rgba': {'r': rgba[0], 'g': rgba[1], 'b': rgba[2], 'a': rgba[3]}, 'hex': hex_value, 'count': count, 'coverage': round(count / total, 6)})",
        "contrast_notes = []",
        "if len(palette) >= 2:\n"
        "    first = palette[0]['rgba']\n"
        "    last = palette[-1]['rgba']\n"
        "    contrast_notes.append({'pair': [palette[0]['hex'], palette[-1]['hex']], 'luminance_delta': round(abs(rel_luminance((first['r'], first['g'], first['b'])) - rel_luminance((last['r'], last['g'], last['b']))), 6)})",
        "result = {'palette': palette, 'coverage': [entry['coverage'] for entry in palette], 'contrast_notes': contrast_notes, 'sampled_pixels': sampled, 'transparent_skipped': transparent_skipped, 'region': region, 'deterministic': True}",
        "print(json.dumps(result))",
    ]
    return code


PAINT_RESOURCE_ALIASES = {
    "brush": "brushes",
    "brushes": "brushes",
    "pattern": "patterns",
    "patterns": "patterns",
    "gradient": "gradients",
    "gradients": "gradients",
    "font": "fonts",
    "fonts": "fonts",
    "palette": "palettes",
    "palettes": "palettes",
}

PAINT_RESOURCE_LIST_CALLS = {
    "brushes": "Gimp.brushes_get_list('')",
    "patterns": "Gimp.patterns_get_list('')",
    "gradients": "Gimp.gradients_get_list('')",
    "fonts": "Gimp.fonts_get_list('')",
    "palettes": "Gimp.palettes_get_list('')",
}

PAINT_RESOURCE_GETTERS = {
    "brushes": "Gimp.context_get_brush()",
    "patterns": "Gimp.context_get_pattern()",
    "gradients": "Gimp.context_get_gradient()",
    "fonts": "Gimp.context_get_font()",
    "palettes": "Gimp.context_get_palette()",
}

PAINT_RESOURCE_SETTERS = {
    "brushes": "Gimp.context_set_brush",
    "patterns": "Gimp.context_set_pattern",
    "gradients": "Gimp.context_set_gradient",
    "fonts": "Gimp.context_set_font",
    "palettes": "Gimp.context_set_palette",
}


def _json_from_bridge(result: dict[str, Any]) -> dict[str, Any]:
    """Decode the first JSON object printed by generated code."""
    import json as _json

    for out in result.get("results", []):
        if out and str(out).strip():
            try:
                decoded = _json.loads(str(out).strip())
            except _json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
    return {}


def _resource_common_code() -> list[str]:
    """Shared generated Python helpers for GIMP resource inspection."""
    return [
        "import json",
        "from gi.repository import Gimp, Gegl",
        (
            "def _resource_names(value):\n"
            "    if isinstance(value, tuple):\n"
            "        for part in reversed(value):\n"
            "            if isinstance(part, (list, tuple)):\n"
            "                value = part\n"
            "                break\n"
            "    names = []\n"
            "    for item in (value or []):\n"
            "        get_name = getattr(item, 'get_name', None)\n"
            "        names.append(str(get_name() if get_name else item))\n"
            "    return names"
        ),
        (
            "def _resource_name(value):\n"
            "    if value is None:\n"
            "        return None\n"
            "    get_name = getattr(value, 'get_name', None)\n"
            "    return str(get_name() if get_name else value)"
        ),
    ]


def _brush_inventory_code(
    asset_types: list[str],
    filter_text: str | None,
    limit: int,
    include_current: bool,
) -> list[str]:
    """Return generated Python code for resource inventory with current markers."""
    code = _resource_common_code()
    code += [
        "# __gimp_mcp_brush_inventory__",
        f"asset_types = {asset_types!r}",
        f"filter_text = {filter_text!r}",
        f"limit = {limit!r}",
        f"include_current = {include_current!r}",
        "current = {}",
    ]
    if include_current:
        for kind in asset_types:
            getter = PAINT_RESOURCE_GETTERS[kind]
            code.append(f"current[{py_literal(kind)}] = _resource_name({getter})")
    code.append("assets = []")
    for kind in asset_types:
        call = PAINT_RESOURCE_LIST_CALLS[kind]
        code += [
            f"names = _resource_names({call})",
            "if filter_text:",
            "    names = [name for name in names if filter_text.lower() in name.lower()]",
            f"for name in names[:limit]: assets.append({{'type': {py_literal(kind)}, 'name': name, 'is_current': current.get({py_literal(kind)}) == name}})",
        ]
    code += [
        "result = {'assets': assets, 'current': current, 'limit': limit, 'filter': filter_text}",
        "print(json.dumps(result))",
    ]
    return code


def _resource_catalog_code(
    resource_type: str,
    query: str | None,
    limit: int,
    include_optional: bool,
) -> list[str]:
    """Return generated code for bounded searchable resource catalog."""
    call = PAINT_RESOURCE_LIST_CALLS.get(resource_type)
    if call is None:
        call = "None"
    return _resource_common_code() + [
        "# __gimp_mcp_resource_catalog__",
        f"resource_type = {py_literal(resource_type)}",
        f"query = {py_literal((query or '').lower())}",
        f"limit = {limit!r}",
        f"include_optional = {include_optional!r}",
        "resources = []",
        "optional_capability = None",
        f"raw_names = _resource_names({call}) if {call!r} != 'None' else []",
        "if query:\n    raw_names = [name for name in raw_names if query in name.lower()]",
        "for index, name in enumerate(raw_names[:limit]):\n"
        "    resources.append({'type': resource_type, 'name': name, 'index': index})",
        "if not resources and resource_type in {'dynamics', 'tool_presets'}:\n"
        "    optional_capability = {'available': False, 'resource_type': resource_type, 'reason': 'GIMP API list function not exposed'}",
        "result = {'resource_type': resource_type, 'resources': resources, 'count': len(resources), 'limit': limit, 'query': query, 'optional_capability': optional_capability}",
        "print(json.dumps(result))",
    ]


def _set_paint_resource_code(resource_type: str, resource_name: str) -> list[str]:
    """Return generated Python code that validates and sets one paint resource."""
    resource_names_call = PAINT_RESOURCE_LIST_CALLS[resource_type]
    getter = PAINT_RESOURCE_GETTERS[resource_type]
    setter = PAINT_RESOURCE_SETTERS[resource_type]
    singular = {
        "brushes": "brush",
        "patterns": "pattern",
        "gradients": "gradient",
        "fonts": "font",
        "palettes": "palette",
    }[resource_type]
    return _resource_common_code() + [
        "# __gimp_mcp_set_paint_resource__",
        f"resource_type = {py_literal(singular)}",
        f"resource_name = {py_literal(resource_name)}",
        f"names = _resource_names({resource_names_call})",
        "if resource_name not in names:\n"
        "    raise RuntimeError(f'Resource not found: {resource_name}')",
        f"previous_resource = {{'type': resource_type, 'name': _resource_name({getter})}}",
        f"{setter}(resource_name)",
        f"active_resource = {{'type': resource_type, 'name': _resource_name({getter})}}",
        "result = {'previous_resource': previous_resource, 'active_resource': active_resource}",
        "print(json.dumps(result))",
    ]


def _set_paint_context_code(
    brush: str | None,
    size: float | None,
    opacity: float | None,
    dynamics: str | None,
    pattern: str | None,
    gradient: str | None,
    foreground: str | None,
    background: str | None,
) -> list[str]:
    """Return generated Python code that validates and applies paint context fields."""
    code = _resource_common_code() + [
        "# __gimp_mcp_set_paint_context__",
        "previous_context = {",
        "    'brush': _resource_name(Gimp.context_get_brush()),",
        "    'pattern': _resource_name(Gimp.context_get_pattern()),",
        "    'gradient': _resource_name(Gimp.context_get_gradient()),",
        "    'font': _resource_name(Gimp.context_get_font()),",
        "    'palette': _resource_name(Gimp.context_get_palette()),",
        "    'opacity': Gimp.context_get_opacity(),",
        "    'brush_size': Gimp.context_get_brush_size(),",
        "    'dynamics': _resource_name(Gimp.context_get_dynamics()),",
        "}",
        "warnings = []",
    ]

    if brush is not None:
        code += [
            "names = _resource_names(Gimp.brushes_get_list(''))",
            f"if {py_literal(brush)} not in names:\n"
            f"    raise RuntimeError('Brush not found: {brush}')",
            f"Gimp.context_set_brush({py_literal(brush)})",
        ]
    if pattern is not None:
        code += [
            "names = _resource_names(Gimp.patterns_get_list(''))",
            f"if {py_literal(pattern)} not in names:\n"
            f"    raise RuntimeError('Pattern not found: {pattern}')",
            f"Gimp.context_set_pattern({py_literal(pattern)})",
        ]
    if gradient is not None:
        code += [
            "names = _resource_names(Gimp.gradients_get_list(''))",
            f"if {py_literal(gradient)} not in names:\n"
            f"    raise RuntimeError('Gradient not found: {gradient}')",
            f"Gimp.context_set_gradient({py_literal(gradient)})",
        ]
    if dynamics is not None:
        code += [
            f"Gimp.context_set_dynamics({py_literal(dynamics)})",
            "warnings.append({'code': 'dynamics_not_list_validated', 'severity': 'info'})",
        ]
    if size is not None:
        code.append(f"Gimp.context_set_brush_size({float(size)!r})")
    if opacity is not None:
        code.append(f"Gimp.context_set_opacity({float(opacity)!r})")
    if foreground is not None:
        code.append(f"Gimp.context_set_foreground(Gegl.Color.new({py_literal(foreground)}))")
    if background is not None:
        code.append(f"Gimp.context_set_background(Gegl.Color.new({py_literal(background)}))")

    code += [
        "new_context = {",
        "    'brush': _resource_name(Gimp.context_get_brush()),",
        "    'pattern': _resource_name(Gimp.context_get_pattern()),",
        "    'gradient': _resource_name(Gimp.context_get_gradient()),",
        "    'font': _resource_name(Gimp.context_get_font()),",
        "    'palette': _resource_name(Gimp.context_get_palette()),",
        "    'opacity': Gimp.context_get_opacity(),",
        "    'brush_size': Gimp.context_get_brush_size(),",
        "    'dynamics': _resource_name(Gimp.context_get_dynamics()),",
        "}",
        "result = {'previous_context': previous_context, 'new_context': new_context, 'warnings': warnings}",
        "print(json.dumps(result))",
    ]
    return code


def register_color_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all color adjustment tools with the MCP server."""

    @mcp.tool()
    async def adjust_brightness_contrast(
        brightness: int = 0,
        contrast: int = 0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust brightness and contrast of a layer.

        Args:
            brightness: Brightness adjustment (-127 to 127, 0 = no change)
            contrast: Contrast adjustment (-127 to 127, 0 = no change)
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        brightness = max(-127, min(127, brightness))
        contrast = max(-127, min(127, contrast))

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.brightness_contrast(drawable, {brightness / 127.0}, {contrast / 127.0})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="adjust_brightness_contrast",
                message=f"Brightness={brightness}, Contrast={contrast}",
                data={"brightness": brightness, "contrast": contrast},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="adjust_brightness_contrast", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def adjust_hue_saturation(
        hue: float = 0.0,
        saturation: float = 0.0,
        lightness: float = 0.0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust hue, saturation, and lightness of a layer.

        Args:
            hue: Hue rotation in degrees (-180 to 180, 0 = no change)
            saturation: Saturation adjustment (-100 to 100, 0 = no change)
            lightness: Lightness adjustment (-100 to 100, 0 = no change)
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        hue = max(-180.0, min(180.0, hue))
        saturation = max(-100.0, min(100.0, saturation))
        lightness = max(-100.0, min(100.0, lightness))

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.hue_saturation(drawable, Gimp.HueRange.ALL, "
            f"{hue}, {lightness}, {saturation}, 0.0)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="adjust_hue_saturation",
                message=f"Hue={hue}°, Saturation={saturation}, Lightness={lightness}",
                data={"hue": hue, "saturation": saturation, "lightness": lightness},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="adjust_hue_saturation", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def adjust_color_balance(
        range: str = "midtones",
        cyan_red: float = 0.0,
        magenta_green: float = 0.0,
        yellow_blue: float = 0.0,
        preserve_luminosity: bool = True,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust shadows, midtones, or highlights color balance for a layer.

        Args:
            range: Tonal range to adjust: "shadows", "midtones", or "highlights".
            cyan_red: Cyan-to-red shift (-100 to 100, 0 = no change).
            magenta_green: Magenta-to-green shift (-100 to 100, 0 = no change).
            yellow_blue: Yellow-to-blue shift (-100 to 100, 0 = no change).
            preserve_luminosity: Keep luminance stable while shifting colors.
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        range_key = range.lower().strip().replace("-", "_")
        range_map = {
            "shadows": "Gimp.TransferMode.SHADOWS",
            "shadow": "Gimp.TransferMode.SHADOWS",
            "midtones": "Gimp.TransferMode.MIDTONES",
            "midtone": "Gimp.TransferMode.MIDTONES",
            "highlights": "Gimp.TransferMode.HIGHLIGHTS",
            "highlight": "Gimp.TransferMode.HIGHLIGHTS",
        }
        transfer_expr = range_map.get(range_key, "Gimp.TransferMode.MIDTONES")
        resolved_range = {
            "Gimp.TransferMode.SHADOWS": "shadows",
            "Gimp.TransferMode.MIDTONES": "midtones",
            "Gimp.TransferMode.HIGHLIGHTS": "highlights",
        }[transfer_expr]

        cyan_red = max(-100.0, min(100.0, cyan_red))
        magenta_green = max(-100.0, min(100.0, magenta_green))
        yellow_blue = max(-100.0, min(100.0, yellow_blue))

        code = _color_preamble(layer_name, layer_index) + [
            "Gimp.Drawable.color_balance("
            f"drawable, {transfer_expr}, {preserve_luminosity}, "
            f"{cyan_red / 100.0}, {magenta_green / 100.0}, {yellow_blue / 100.0})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="adjust_color_balance",
                message=(
                    f"Color balance adjusted for {resolved_range}: "
                    f"cyan_red={cyan_red}, magenta_green={magenta_green}, yellow_blue={yellow_blue}"
                ),
                data={
                    "range": resolved_range,
                    "cyan_red": cyan_red,
                    "magenta_green": magenta_green,
                    "yellow_blue": yellow_blue,
                    "preserve_luminosity": preserve_luminosity,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="adjust_color_balance", error=str(e)).model_dump()

    @mcp.tool()
    async def adjust_levels(
        input_low: int = 0,
        input_high: int = 255,
        gamma: float = 1.0,
        output_low: int = 0,
        output_high: int = 255,
        channel: str = "value",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust levels for a layer.

        Notes:
            Use this tool when fine-tuning tonal range, fixing underexposed/overexposed
            images, adjusting individual color channels.

        Args:
            input_low: Input black point (0-255)
            input_high: Input white point (0-255)
            gamma: Midtone gamma (0.1-10.0, 1.0 = no change)
            output_low: Output black point (0-255)
            output_high: Output white point (0-255)
            channel: "value" (all), "red", "green", "blue", "alpha"
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        channel_map = {
            "value": "Gimp.HistogramChannel.VALUE",
            "red": "Gimp.HistogramChannel.RED",
            "green": "Gimp.HistogramChannel.GREEN",
            "blue": "Gimp.HistogramChannel.BLUE",
            "alpha": "Gimp.HistogramChannel.ALPHA",
        }
        ch_expr = channel_map.get(channel.lower(), "Gimp.HistogramChannel.VALUE")

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.levels(drawable, {ch_expr}, "
            f"{input_low / 255.0}, {input_high / 255.0}, False, "
            f"{gamma}, "
            f"{output_low / 255.0}, {output_high / 255.0}, False)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="adjust_levels",
                message=f"Levels adjusted ({channel}): input [{input_low}-{input_high}], gamma {gamma}",
                data={
                    "channel": channel,
                    "input_low": input_low,
                    "input_high": input_high,
                    "gamma": gamma,
                    "output_low": output_low,
                    "output_high": output_high,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="adjust_levels", error=str(e)).model_dump()

    @mcp.tool()
    async def adjust_curves(
        control_points: list[float],
        channel: str = "value",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust curves for a layer.

        Notes:
            Use this tool when fine-grained tonal control, creating custom contrast curves,
            cross-processing effects.

        Args:
            control_points: Flat list of input/output pairs [in1,out1, in2,out2, ...].
                           Values are 0.0-1.0 (0=black, 1=white).
                           Example: [0,0, 0.25,0.2, 0.5,0.6, 0.75,0.85, 1,1] for S-curve.
            channel: "value", "red", "green", "blue", "alpha"
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if len(control_points) < 4 or len(control_points) % 2 != 0:
            return OperationResult.fail(
                operation="adjust_curves",
                error="control_points must have at least 2 pairs (4 values) with even count",
            ).model_dump()

        channel_map = {
            "value": "Gimp.HistogramChannel.VALUE",
            "red": "Gimp.HistogramChannel.RED",
            "green": "Gimp.HistogramChannel.GREEN",
            "blue": "Gimp.HistogramChannel.BLUE",
            "alpha": "Gimp.HistogramChannel.ALPHA",
        }
        ch_expr = channel_map.get(channel.lower(), "Gimp.HistogramChannel.VALUE")

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.curves_spline(drawable, {ch_expr}, {control_points})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            n_points = len(control_points) // 2
            return OperationResult.ok(
                operation="adjust_curves",
                message=f"Curves adjusted ({channel}, {n_points} control points)",
                data={"channel": channel, "num_points": n_points},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="adjust_curves", error=str(e)).model_dump()

    @mcp.tool()
    async def desaturate(
        method: str = "luminosity",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Convert a layer to grayscale while keeping it in RGB mode.

        Args:
            method: Desaturation method —
                    "luminosity" (perceptual, recommended),
                    "average" (equal weight),
                    "lightness" (HSL lightness),
                    "luminance" (linear luminance)
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        method_map = {
            "luminosity": "Gimp.DesaturateMode.LUMA",
            "luma": "Gimp.DesaturateMode.LUMA",
            "average": "Gimp.DesaturateMode.AVERAGE",
            "lightness": "Gimp.DesaturateMode.LIGHTNESS",
            "luminance": "Gimp.DesaturateMode.LUMINANCE",
            "value": "Gimp.DesaturateMode.VALUE",
        }
        m_expr = method_map.get(method.lower().strip(), "Gimp.DesaturateMode.LUMA")

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.desaturate(drawable, {m_expr})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="desaturate",
                message=f"Desaturated using {method} method",
                data={"method": method},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="desaturate", error=str(e)).model_dump()

    @mcp.tool()
    async def invert_colors(
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Invert all colors in a layer (negative effect).

        Each pixel's color is replaced with its complement.

        Args:
            layer_name: Target layer by name. Uses the active layer when omitted.
            layer_index: Target layer by index. Uses the active layer when omitted.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _color_preamble(layer_name, layer_index) + [
            "Gimp.Drawable.invert(drawable, False)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="invert_colors", message="Colors inverted"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="invert_colors", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_threshold(
        low: int = 128,
        high: int = 255,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply threshold — convert to pure black and white.

        Pixels darker than `low` become black, lighter than `high` become white.

        Args:
            low: Lower threshold (0-255, default 128)
            high: Upper threshold (0-255, default 255)
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.threshold(drawable, Gimp.HistogramChannel.VALUE, "
            f"{low / 255.0}, {high / 255.0})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="apply_threshold",
                message=f"Threshold applied ({low}-{high})",
                data={"low": low, "high": high},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_threshold", error=str(e)).model_dump()

    @mcp.tool()
    async def posterize(
        levels: int = 4,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Reduce the number of color levels (posterization effect).

        Args:
            levels: Number of color levels per channel (2-256, lower = more dramatic)
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        levels = max(2, min(256, levels))

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.posterize(drawable, {levels})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="posterize",
                message=f"Posterized to {levels} levels",
                data={"levels": levels},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="posterize", error=str(e)).model_dump()

    @mcp.tool()
    async def color_to_alpha(
        color: str = "white",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Make a specific color transparent (color to alpha).

        Notes:
            Use this tool when removing backgrounds, making white/black transparent
            for compositing, creating cutouts.

        Args:
            color: Color to make transparent — name, hex, or rgb.
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        c = Color(value=color)

        lifecycle = [
            "import gc",
            "# __gimp_mcp_color_to_alpha_lifecycle__",
            "df = None",
            "cfg = None",
            "try:",
            "    if not drawable.has_alpha(): drawable.add_alpha()",
            f"    gegl_color = {c.to_gegl_code()}",
            "    df = Gimp.DrawableFilter.new(drawable, 'gegl:color-to-alpha', '')",
            "    cfg = df.get_config()",
            "    cfg.set_property('color', gegl_color)",
            "    drawable.append_filter(df)",
            "    drawable.merge_filter(df)",
            "finally:",
            "    try:",
            "        if df is not None and hasattr(drawable, 'remove_filter'):",
            "            drawable.remove_filter(df)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del cfg",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del df",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
        ]
        code = _color_preamble(layer_name, layer_index) + [
            "\n".join(lifecycle),
            "Gimp.displays_flush()",
        ]

        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="color_to_alpha",
                message=f"Color '{color}' made transparent",
                data={"color": color},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="color_to_alpha", error=str(e)).model_dump()

    @mcp.tool()
    async def auto_white_balance(
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Automatically adjust white balance (stretch colors).

        Performs automatic levels adjustment to normalize color distribution.

        Args:
            layer_name: Target layer by name. Uses the active layer when omitted.
            layer_index: Target layer by index. Uses the active layer when omitted.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _color_preamble(layer_name, layer_index) + [
            "Gimp.Drawable.levels_stretch(drawable)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="auto_white_balance",
                message="Auto white balance applied",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="auto_white_balance", error=str(e)).model_dump()

    @mcp.tool()
    async def brush_inventory(
        asset_types: list[str] | None = None,
        filter: str | None = None,
        limit: int = 100,
        include_current: bool = True,
    ) -> ToolResult:
        """List paint resources with current-context markers.

        Args:
            asset_types: Resource types to list. Supported: brushes, patterns, gradients, fonts, palettes.
            filter: Optional case-insensitive substring filter.
            limit: Maximum entries per requested resource type.
            include_current: Mark resources currently active in GIMP context.

        Returns:
            Operation result with flat ``assets`` list and current resource map.
        """
        requested = asset_types or ["brushes", "patterns", "gradients", "fonts", "palettes"]
        normalised: list[str] = []
        unsupported: list[str] = []
        for item in requested:
            key = PAINT_RESOURCE_ALIASES.get(str(item).lower().strip().replace("-", "_"))
            if key is None:
                unsupported.append(str(item))
            elif key not in normalised:
                normalised.append(key)
        if unsupported:
            return OperationResult.fail(
                operation="brush_inventory",
                error=f"unsupported asset type(s): {', '.join(unsupported)}",
            ).model_dump()
        limit = max(1, min(1000, int(limit)))
        try:
            result = await bridge.async_execute_python(
                _brush_inventory_code(normalised, filter, limit, include_current)
            )
            data = _json_from_bridge(result)
            data.setdefault("assets", [])
            data.setdefault("current", {})
            return OperationResult.ok(
                operation="brush_inventory",
                message=f"Listed paint inventory for {len(normalised)} asset type(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="brush_inventory", error=str(e)).model_dump()

    @mcp.tool()
    async def set_paint_resource(
        resource_type: str,
        name: str,
    ) -> ToolResult:
        """Set one active paint resource by validated name.

        Args:
            resource_type: One of brush, pattern, gradient, font, or palette.
            name: Resource name to validate and activate.

        Returns:
            Operation result with previous_resource and active_resource read-back.
        """
        key = PAINT_RESOURCE_ALIASES.get(resource_type.lower().strip().replace("-", "_"))
        if key is None:
            return OperationResult.fail(
                operation="set_paint_resource",
                error=f"unsupported paint resource type: {resource_type}",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(_set_paint_resource_code(key, name))
            data = _json_from_bridge(result)
            data.setdefault("previous_resource", {})
            data.setdefault("active_resource", {"type": resource_type, "name": name})
            return OperationResult.ok(
                operation="set_paint_resource",
                message=f"Activated {resource_type} resource {name!r}",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_paint_resource", error=str(e)).model_dump()

    @mcp.tool()
    async def set_paint_context(
        brush: str | None = None,
        size: float | None = None,
        opacity: float | None = None,
        dynamics: str | None = None,
        pattern: str | None = None,
        gradient: str | None = None,
        foreground: str | None = None,
        background: str | None = None,
    ) -> ToolResult:
        """Set multiple paint context fields with validation and read-back.

        Args:
            brush: Optional brush name.
            size: Optional brush size.
            opacity: Optional context opacity percent, 0..100.
            dynamics: Optional dynamics name. Applied with read-back warning because GIMP does not expose list validation.
            pattern: Optional pattern name.
            gradient: Optional gradient name.
            foreground: Optional foreground color.
            background: Optional background color.

        Returns:
            Operation result with previous_context, new_context, and warnings.
        """
        if size is not None and float(size) <= 0:
            return OperationResult.fail(
                operation="set_paint_context",
                error="size must be positive",
            ).model_dump()
        if opacity is not None and (float(opacity) < 0 or float(opacity) > 100):
            return OperationResult.fail(
                operation="set_paint_context",
                error="opacity must be between 0 and 100",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _set_paint_context_code(
                    brush,
                    float(size) if size is not None else None,
                    float(opacity) if opacity is not None else None,
                    dynamics,
                    pattern,
                    gradient,
                    foreground,
                    background,
                )
            )
            data = _json_from_bridge(result)
            data.setdefault("previous_context", {})
            data.setdefault("new_context", {})
            data.setdefault("warnings", [])
            return OperationResult.ok(
                operation="set_paint_context",
                message="Paint context updated",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_paint_context", error=str(e)).model_dump()

    @mcp.tool()
    async def resource_catalog(
        resource_type: str,
        query: str | None = None,
        limit: int = 50,
        include_optional: bool = True,
    ) -> ToolResult:
        """List bounded searchable resources with optional capability notes.

        Args:
            resource_type: Resource kind such as brush, pattern, gradient, font, palette, dynamics, or tool preset.
            query: Optional case-insensitive search string.
            limit: Maximum number of resources to return.
            include_optional: Include structured optional-capability notes for missing resource APIs.

        Returns:
            Operation result with resource records, count, and optional-capability metadata.
        """
        aliases = dict(PAINT_RESOURCE_ALIASES)
        aliases.update(
            {
                "dynamic": "dynamics",
                "dynamics": "dynamics",
                "preset": "tool_presets",
                "tool_preset": "tool_presets",
                "tool_presets": "tool_presets",
            }
        )
        key = aliases.get(resource_type.lower().strip().replace("-", "_"))
        if key is None:
            return OperationResult.fail(
                operation="resource_catalog", error=f"unsupported resource_type: {resource_type}"
            ).model_dump()
        limit = max(1, min(1000, int(limit)))
        try:
            result = await bridge.async_execute_python(
                _resource_catalog_code(key, query, limit, include_optional)
            )
            data = _json_from_bridge(result)
            data.setdefault("resources", [])
            data.setdefault("count", len(data.get("resources", [])))
            return OperationResult.ok(
                operation="resource_catalog",
                message=f"Catalogued {data.get('count', 0)} {key} resource(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="resource_catalog", error=str(e)).model_dump()

    @mcp.tool()
    async def list_gimp_resources(
        resource_type: str = "all",
        limit: int = 100,
    ) -> ToolResult:
        """List available GIMP brushes, patterns, fonts, and gradients.

        Args:
            resource_type: One of "all", "brushes", "patterns", "fonts", or "gradients".
            limit: Maximum number of names returned per resource category.

        Returns:
            Operation result dictionary with status, message, and resource name lists.
        """
        resource_key = resource_type.lower().strip().replace("-", "_")
        aliases = {
            "brush": "brushes",
            "brushes": "brushes",
            "pattern": "patterns",
            "patterns": "patterns",
            "font": "fonts",
            "fonts": "fonts",
            "gradient": "gradients",
            "gradients": "gradients",
            "all": "all",
        }
        selected = aliases.get(resource_key, "all")
        limit = max(1, min(1000, limit))
        resource_calls = {
            "brushes": "Gimp.brushes_get_list('')",
            "patterns": "Gimp.patterns_get_list('')",
            "fonts": "Gimp.fonts_get_list('')",
            "gradients": "Gimp.gradients_get_list('')",
        }
        selected_calls = (
            resource_calls if selected == "all" else {selected: resource_calls[selected]}
        )

        code = [
            "import json",
            "from gi.repository import Gimp",
            "resources = {}",
            (
                "def _resource_names(value):\n"
                "    if isinstance(value, tuple):\n"
                "        for part in reversed(value):\n"
                "            if isinstance(part, (list, tuple)):\n"
                "                value = part\n"
                "                break\n"
                "    names = []\n"
                "    for item in (value or []):\n"
                "        get_name = getattr(item, 'get_name', None)\n"
                "        names.append(str(get_name() if get_name else item))\n"
                "    return names"
            ),
        ]
        for kind, call_expr in selected_calls.items():
            code.append(f"resources[{py_literal(kind)}] = _resource_names({call_expr})[:{limit}]")
        code.append("print(json.dumps(resources))")

        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            resources: dict[str, object] = {}
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        resources = _json.loads(str(out).strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            total = sum(len(v) for v in resources.values() if isinstance(v, list))
            return OperationResult.ok(
                operation="list_gimp_resources",
                message=f"Listed {total} GIMP resources",
                data=resources,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="list_gimp_resources", error=str(e)).model_dump()

    @mcp.tool()
    async def get_colors() -> ToolResult:
        """Get the current foreground and background colors.

        Notes:
            Use this tool before drawing to verify colors are set correctly,
            especially since the user can change them in GIMP's UI at any time.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "import json",
            "from gi.repository import Gimp, Gegl",
            "fg = Gimp.context_get_foreground()",
            "bg = Gimp.context_get_background()",
            "result = {}",
            "def color_to_dict(c):\n"
            "    try:\n"
            "        rgba = c.get_rgba()\n"
            "        return {'r': round(rgba.red, 4), 'g': round(rgba.green, 4), 'b': round(rgba.blue, 4), 'a': round(rgba.alpha, 4)}\n"
            "    except:\n"
            "        return str(c)",
            "result['foreground'] = color_to_dict(fg)",
            "result['background'] = color_to_dict(bg)",
            "print(json.dumps(result))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            colors_data = {}
            for out in result.get("results", []):
                if out and out.strip():
                    try:
                        colors_data = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="get_colors",
                message="Current colors retrieved",
                data=colors_data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_colors", error=str(e)).model_dump()

    @mcp.tool()
    async def swap_colors() -> ToolResult:
        """Swap foreground and background colors.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "from gi.repository import Gimp",
            "Gimp.context_swap_colors()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="swap_colors",
                message="Foreground and background colors swapped",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="swap_colors", error=str(e)).model_dump()

    @mcp.tool()
    async def analyze_color_palette(
        max_colors: int = 8,
        ignore_transparent: bool = True,
        region: dict[str, Any] | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Extract a deterministic approximate color palette for a layer or region.

        Args:
            max_colors: Maximum number of dominant colors to return.
            ignore_transparent: Skip fully transparent samples.
            region: Optional ``x/y/width/height`` rectangle in layer coordinates.
            layer_name: Target layer by name.
            layer_index: Target layer by index.

        Returns:
            Operation result with palette entries, coverage, contrast notes, and stats.

        Contract:
            The generated sampler is deterministic for the same pixels and region.
        """
        if max_colors < 1 or max_colors > 64:
            return OperationResult.fail(
                operation="analyze_color_palette",
                error="max_colors must be between 1 and 64",
            ).model_dump()
        if region is not None:
            try:
                width = int(region["width"])
                height = int(region["height"])
            except (KeyError, TypeError, ValueError) as e:
                return OperationResult.fail(
                    operation="analyze_color_palette", error=str(e)
                ).model_dump()
            if width < 1 or height < 1:
                return OperationResult.fail(
                    operation="analyze_color_palette",
                    error="region width and height must be >= 1",
                ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _palette_analysis_code(
                    max_colors, ignore_transparent, region, layer_name, layer_index
                ),
                timeout=LONG_TIMEOUT,
            )
            import json as _json

            data: dict[str, Any] = {}
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        decoded = _json.loads(str(out).strip())
                    except _json.JSONDecodeError:
                        continue
                    if isinstance(decoded, dict):
                        data = decoded
                        break
            data.setdefault("palette", [])
            data.setdefault("coverage", [])
            data.setdefault("contrast_notes", [])
            return OperationResult.ok(
                operation="analyze_color_palette",
                message=f"Analyzed up to {max_colors} palette color(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="analyze_color_palette", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def sample_pixels(
        points: list[dict[str, Any]] | None = None,
        grid: dict[str, Any] | None = None,
        sample_merged: bool = False,
        sample_average: bool = False,
        average_radius: float = 0.0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Sample colors at multiple points or over a rectangular grid.

        Args:
            points: Explicit point dictionaries with x and y coordinates.
            grid: Optional grid spec with x, y, width, height, columns, and rows.
            sample_merged: If True, sample the visible composite image.
            sample_average: If True, average a radius around each point via GIMP pick_color.
            average_radius: Radius used when sample_average is enabled.
            layer_name: Target layer by name when not sampling merged output.
            layer_index: Target layer by index when not sampling merged output.

        Returns:
            Operation result with sampled RGBA/hex colors and request metadata.
        """
        if not points and grid is None:
            return OperationResult.fail(
                operation="sample_pixels",
                error="sample_pixels requires points or grid",
            ).model_dump()

        try:
            normalised_points, points_requested = _normalise_sample_points(points, grid)
        except (KeyError, TypeError, ValueError) as e:
            return OperationResult.fail(operation="sample_pixels", error=str(e)).model_dump()

        average_radius = max(0.0, float(average_radius))
        code = _sample_pixels_code(
            normalised_points,
            grid,
            sample_merged=sample_merged,
            sample_average=sample_average,
            average_radius=average_radius,
            layer_name=layer_name,
            layer_index=layer_index,
        )
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            sample_data: dict[str, Any] = {}
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        decoded = _json.loads(str(out).strip())
                    except _json.JSONDecodeError:
                        continue
                    if isinstance(decoded, dict):
                        sample_data = decoded
                        break
            sample_data.setdefault("samples", [])
            sample_data.setdefault("color_space", "rgba")
            sample_data["points_requested"] = points_requested
            sample_data["sample_merged"] = sample_merged
            sample_data["sample_average"] = sample_average
            sample_data["average_radius"] = average_radius
            return OperationResult.ok(
                operation="sample_pixels",
                message=f"Sampled {points_requested} pixel point(s)",
                data=sample_data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="sample_pixels", error=str(e)).model_dump()

    @mcp.tool()
    async def sample_color(
        x: int,
        y: int,
        sample_merged: bool = False,
    ) -> ToolResult:
        """Pick/sample a color from a pixel in the image.

        Args:
            x: X coordinate to sample
            y: Y coordinate to sample
            sample_merged: If True, sample from all visible layers merged.
                          If False, sample from active layer only.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "import json",
            "from gi.repository import Gimp, Gegl",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "sel = image.get_selected_layers()",
            "if not sel: raise RuntimeError('No active layer')",
            "drawable = sel[0]",
            "result = {}",
            "try:\n"
            f"    color = drawable.get_pixel({x}, {y})\n"
            "    rgba = color.get_rgba()\n"
            "    result = {'r': round(rgba.red, 4), 'g': round(rgba.green, 4), 'b': round(rgba.blue, 4), 'a': round(rgba.alpha, 4)}\n"
            "except Exception as e:\n"
            "    result = {'error': str(e)}",
            "print(json.dumps(result))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            color_data = {}
            for out in result.get("results", []):
                if out and out.strip():
                    try:
                        color_data = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="sample_color",
                message=f"Color sampled at ({x}, {y})",
                data=color_data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="sample_color", error=str(e)).model_dump()

    @mcp.tool()
    async def palette_create_or_update(
        action: str,
        palette_name: str,
        colors: list[dict[str, Any]] | None = None,
        overwrite: bool = False,
    ) -> ToolResult:
        """Create, inspect, or update a palette from provided colors.

        Args:
            action: create/update/inspect.
            palette_name: Palette name.
            colors: Optional named color entries.
            overwrite: Allow replacing an existing palette.

        Returns:
            Operation result with palette metadata.
        """
        normalized = action.strip().lower().replace("-", "_")
        if normalized not in {"create", "update", "inspect"}:
            return OperationResult.fail(
                operation="palette_create_or_update",
                error="action must be create, update, or inspect",
            ).model_dump()
        if not palette_name.strip():
            return OperationResult.fail(
                operation="palette_create_or_update", error="palette_name is required"
            ).model_dump()
        payload = {
            "action": normalized,
            "palette": {"name": palette_name, "colors": colors or [], "overwrite": overwrite},
        }
        return await _execute_json_tool(
            bridge,
            operation="palette_create_or_update",
            marker="__gimp_mcp_palette_create_or_update__",
            payload=payload,
            message="Palette operation prepared",
        )
