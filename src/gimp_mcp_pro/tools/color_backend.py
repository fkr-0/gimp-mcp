"""Generated-code helpers for color MCP tool implementations."""

from __future__ import annotations

from typing import Any

from gimp_mcp_pro.models.common import py_literal

MAX_SAMPLE_POINTS = 4096
MAX_AVERAGE_RADIUS = 128.0


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


def _color_histogram_code(
    channels: list[str],
    start_range: float,
    end_range: float,
    layer_name: str | None,
    layer_index: int | None,
) -> list[str]:
    """Return generated code for bounded per-channel histogram summaries."""
    channel_expr = {
        "value": "Gimp.HistogramChannel.VALUE",
        "red": "Gimp.HistogramChannel.RED",
        "green": "Gimp.HistogramChannel.GREEN",
        "blue": "Gimp.HistogramChannel.BLUE",
        "alpha": "Gimp.HistogramChannel.ALPHA",
    }
    lines = _color_preamble(layer_name, layer_index) + ["import json", "stats = {}"]
    for channel in channels:
        lines += [
            f"ok, mean, std_dev, median, pixels, count, percentile = drawable.histogram({channel_expr[channel]}, {start_range}, {end_range})",
            f"stats[{channel!r}] = {{'ok': bool(ok), 'mean': mean, 'std_dev': std_dev, 'median': median, 'pixels': pixels, 'count': count, 'percentile': percentile}}",
        ]
    lines.append(
        "print(json.dumps({'channels': stats, 'range': {'start': "
        f"{start_range!r}, 'end': {end_range!r}" + "}}))"
    )
    return lines


def _sample_color_code(x: int, y: int, sample_merged: bool) -> list[str]:
    """Return generated code for one active-layer or merged color sample."""
    return [
        "import json",
        "from gi.repository import Gimp",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "sel = image.get_selected_layers()",
        "if not sel: raise RuntimeError('No active layer')",
        "drawable = sel[0]",
        (
            f"picked = image.pick_color([drawable], {x}, {y}, True, False, 0.0)\n"
            "color = picked[-1] if isinstance(picked, tuple) else picked\n"
            "if color is None: raise RuntimeError('No color returned')"
            if sample_merged
            else f"color = drawable.get_pixel({x}, {y})"
        ),
        "rgba = color.get_rgba()",
        "result = {'r': round(rgba.red, 4), 'g': round(rgba.green, 4), 'b': round(rgba.blue, 4), 'a': round(rgba.alpha, 4)}",
        "print(json.dumps(result))",
    ]


def _color_adjustment_lifecycle(mutation_lines: list[str]) -> list[str]:
    """Wrap mutating color adjustments in one explicit GIMP undo group."""
    lifecycle = [
        "try:",
        *[f"    {line}" for line in mutation_lines],
        "    Gimp.displays_flush()",
        "finally:",
        "    image.undo_group_end()",
    ]
    return [
        "# __gimp_mcp_color_adjustment_lifecycle__",
        "image.undo_group_start()",
        "\n".join(lifecycle),
    ]


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
    total_points = len(normalised) + grid_count
    if total_points > MAX_SAMPLE_POINTS:
        raise ValueError(f"sample point count must be <= {MAX_SAMPLE_POINTS}")
    return normalised, total_points


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
        "# __gimp_mcp_paint_context_lifecycle__",
        "previous_foreground_color = Gimp.context_get_foreground()",
        "previous_background_color = Gimp.context_get_background()",
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
        "foreground_color = None",
        "background_color = None",
    ]

    if brush is not None:
        code += [
            "brush_names = _resource_names(Gimp.brushes_get_list(''))",
            f"if {py_literal(brush)} not in brush_names:\n"
            f"    raise RuntimeError('Brush not found: {brush}')",
        ]
    if pattern is not None:
        code += [
            "pattern_names = _resource_names(Gimp.patterns_get_list(''))",
            f"if {py_literal(pattern)} not in pattern_names:\n"
            f"    raise RuntimeError('Pattern not found: {pattern}')",
        ]
    if gradient is not None:
        code += [
            "gradient_names = _resource_names(Gimp.gradients_get_list(''))",
            f"if {py_literal(gradient)} not in gradient_names:\n"
            f"    raise RuntimeError('Gradient not found: {gradient}')",
        ]
    if foreground is not None:
        code.append(f"foreground_color = Gegl.Color.new({py_literal(foreground)})")
    if background is not None:
        code.append(f"background_color = Gegl.Color.new({py_literal(background)})")

    lifecycle_lines = ["try:"]
    if brush is not None:
        lifecycle_lines.append(f"    Gimp.context_set_brush({py_literal(brush)})")
    if pattern is not None:
        lifecycle_lines.append(f"    Gimp.context_set_pattern({py_literal(pattern)})")
    if gradient is not None:
        lifecycle_lines.append(f"    Gimp.context_set_gradient({py_literal(gradient)})")
    if dynamics is not None:
        lifecycle_lines += [
            f"    Gimp.context_set_dynamics({py_literal(dynamics)})",
            "    warnings.append({'code': 'dynamics_not_list_validated', 'severity': 'info'})",
        ]
    if size is not None:
        lifecycle_lines.append(f"    Gimp.context_set_brush_size({float(size)!r})")
    if opacity is not None:
        lifecycle_lines.append(f"    Gimp.context_set_opacity({float(opacity)!r})")
    if foreground is not None:
        lifecycle_lines.append(
            f"    Gimp.context_set_foreground(foreground_color)  # Gimp.context_set_foreground(Gegl.Color.new({py_literal(foreground)}))"
        )
    if background is not None:
        lifecycle_lines.append(
            f"    Gimp.context_set_background(background_color)  # Gimp.context_set_background(Gegl.Color.new({py_literal(background)}))"
        )

    lifecycle_lines += [
        "except Exception:",
        "    try:",
        "        if previous_context['brush'] is not None:",
        "            Gimp.context_set_brush(previous_context['brush'])",
        "    except Exception:",
        "        pass",
        "    try:",
        "        if previous_context['pattern'] is not None:",
        "            Gimp.context_set_pattern(previous_context['pattern'])",
        "    except Exception:",
        "        pass",
        "    try:",
        "        if previous_context['gradient'] is not None:",
        "            Gimp.context_set_gradient(previous_context['gradient'])",
        "    except Exception:",
        "        pass",
        "    try:",
        "        Gimp.context_set_opacity(previous_context['opacity'])",
        "    except Exception:",
        "        pass",
        "    try:",
        "        Gimp.context_set_brush_size(previous_context['brush_size'])",
        "    except Exception:",
        "        pass",
        "    try:",
        "        Gimp.context_set_foreground(previous_foreground_color)",
        "    except Exception:",
        "        pass",
        "    try:",
        "        Gimp.context_set_background(previous_background_color)",
        "    except Exception:",
        "        pass",
        "    raise",
        "finally:",
        "    try:",
        "        del foreground_color",
        "    except Exception:",
        "        pass",
        "    try:",
        "        del background_color",
        "    except Exception:",
        "        pass",
        "    gc.collect()",
    ]
    code.append("\n".join(lifecycle_lines))

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
