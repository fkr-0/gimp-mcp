"""Geometry, bounds, layer-report, and export-checklist inspection tools."""

from __future__ import annotations

import json
import logging
from typing import Any

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.inspect")

SUPPORTED_GEOMETRY_MEASUREMENTS = {"bounds", "distance", "overlap", "alignment", "spacing"}
SUPPORTED_EXPORT_FORMATS = {"png", "jpeg", "jpg", "webp", "tiff", "tif", "psd", "xcf"}


def _json_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the first JSON object printed by a generated Python command."""
    outputs = result.get("results", [])
    if isinstance(outputs, dict):
        return outputs
    if not isinstance(outputs, list):
        return {}
    for out in outputs:
        if not isinstance(out, str) or not out.strip():
            continue
        try:
            decoded = json.loads(out.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    return {}


def _geometry_target_lookup_lines(targets: list[dict[str, object]]) -> list[str]:
    """Return literal target lookup lines for geometry measurement code."""
    lines = ["targets = []"]
    for index, target in enumerate(targets):
        layer_name = target.get("layer_name") if isinstance(target, dict) else None
        layer_index = target.get("layer_index") if isinstance(target, dict) else None
        if layer_name is not None:
            lines.append(f"target_{index} = image.get_layer_by_name({str(layer_name)!r})")
        elif layer_index is not None:
            layer_index_int = int(str(layer_index))
            lines.append(
                f"target_{index} = layers[{layer_index_int}] if 0 <= {layer_index_int} < len(layers) else None"
            )
        else:
            lines.append(f"target_{index} = layers[{index}] if {index} < len(layers) else None")
        lines.append(f"targets.append(target_{index})")
    return lines


def _measure_geometry_code(targets: list[dict[str, object]], measurements: list[str]) -> list[str]:
    """Return generated Python code that reports stable geometry metrics."""
    lookup_lines = _geometry_target_lookup_lines(targets)
    return [
        "import json, math",
        "# __gimp_mcp_measure_geometry__",
        f"measurements = {measurements!r}",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def offsets(layer):\n"
        "    off = safe_call(lambda: layer.get_offsets(), None)\n"
        "    if off is None:\n"
        "        return {'x': 0, 'y': 0}\n"
        "    if hasattr(off, 'offset_x'):\n"
        "        return {'x': off.offset_x, 'y': off.offset_y}\n"
        "    try:\n"
        "        return {'x': off[0], 'y': off[1]}\n"
        "    except Exception:\n"
        "        return {'x': 0, 'y': 0}",
        "def rect(layer):\n"
        "    off = offsets(layer)\n"
        "    width = int(safe_call(lambda: layer.get_width(), 0) or 0)\n"
        "    height = int(safe_call(lambda: layer.get_height(), 0) or 0)\n"
        "    return {'x': off['x'], 'y': off['y'], 'width': width, 'height': height, 'right': off['x'] + width, 'bottom': off['y'] + height}\n",
        "def center(box):\n"
        "    return {'x': box['x'] + box['width'] / 2, 'y': box['y'] + box['height'] / 2}",
        "def overlap(a, b):\n"
        "    x1 = max(a['x'], b['x']); y1 = max(a['y'], b['y'])\n"
        "    x2 = min(a['right'], b['right']); y2 = min(a['bottom'], b['bottom'])\n"
        "    width = max(0, x2 - x1); height = max(0, y2 - y1)\n"
        "    return {'x': x1, 'y': y1, 'width': width, 'height': height, 'area': width * height}\n",
        "images = Gimp.get_images()",
        "if not images:\n"
        "    result = {'metrics': {}, 'warnings': ['no open images']}\n"
        "else:\n"
        "    image = images[0]\n"
        "    layers = list(safe_call(lambda: image.get_layers(), []) or [])",
        *lookup_lines,
        "    boxes = [rect(layer) for layer in targets if layer is not None]\n"
        "    metrics = {'canvas_relative': boxes, 'target_relative': []}\n"
        "    if boxes:\n"
        "        origin = boxes[0]\n"
        "        metrics['target_relative'] = [{'x': box['x'] - origin['x'], 'y': box['y'] - origin['y'], 'width': box['width'], 'height': box['height']} for box in boxes]\n"
        "    if 'bounds' in measurements:\n"
        "        metrics['bounds'] = boxes\n"
        "    if len(boxes) >= 2:\n"
        "        a, b = boxes[0], boxes[1]\n"
        "        ac, bc = center(a), center(b)\n"
        "        if 'distance' in measurements:\n"
        "            metrics['distance'] = {'dx': bc['x'] - ac['x'], 'dy': bc['y'] - ac['y'], 'euclidean': math.hypot(bc['x'] - ac['x'], bc['y'] - ac['y'])}\n"
        "        if 'overlap' in measurements:\n"
        "            metrics['overlap'] = overlap(a, b)\n"
        "        if 'alignment' in measurements:\n"
        "            metrics['alignment'] = {'left': a['x'] == b['x'], 'top': a['y'] == b['y'], 'center_x': ac['x'] == bc['x'], 'center_y': ac['y'] == bc['y']}\n"
        "        if 'spacing' in measurements:\n"
        "            metrics['spacing'] = {'horizontal_gap': max(0, max(a['x'], b['x']) - min(a['right'], b['right'])), 'vertical_gap': max(0, max(a['y'], b['y']) - min(a['bottom'], b['bottom']))}\n"
        "    result = {'metrics': metrics, 'target_count': len(targets), 'measurements': measurements, 'warnings': []}",
        "print(json.dumps(result))",
    ]


def _layer_report_code(
    include_previews: bool,
    include_warnings: bool,
    include_markdown: bool,
) -> list[str]:
    """Return generated Python code that builds a read-only layer report."""
    return [
        "import json",
        "# __gimp_mcp_layer_report__",
        f"include_previews = {include_previews!r}",
        f"include_warnings = {include_warnings!r}",
        f"include_markdown = {include_markdown!r}",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def offsets(layer):\n"
        "    off = safe_call(lambda: layer.get_offsets(), None)\n"
        "    if off is None:\n"
        "        return {'x': 0, 'y': 0}\n"
        "    if hasattr(off, 'offset_x'):\n"
        "        return {'x': off.offset_x, 'y': off.offset_y}\n"
        "    try:\n"
        "        return {'x': off[0], 'y': off[1]}\n"
        "    except Exception:\n"
        "        return {'x': 0, 'y': 0}",
        "def layer_record(layer, index, image_width, image_height):\n"
        "    width = int(safe_call(lambda: layer.get_width(), 0) or 0)\n"
        "    height = int(safe_call(lambda: layer.get_height(), 0) or 0)\n"
        "    layer_offsets = offsets(layer)\n"
        "    visible = bool(safe_call(lambda: layer.get_visible(), True))\n"
        "    text_layer = Gimp.TextLayer.get_by_id(layer.get_id())\n"
        "    font = safe_call(lambda: text_layer.get_font(), None) if text_layer is not None else None\n"
        "    warnings = []\n"
        "    if include_warnings and not visible:\n"
        "        warnings.append({'code': 'hidden_layer', 'severity': 'info'})\n"
        "    if include_warnings and (width <= 0 or height <= 0):\n"
        "        warnings.append({'code': 'empty_layer', 'severity': 'warning'})\n"
        "    if include_warnings and (layer_offsets['x'] < 0 or layer_offsets['y'] < 0 or layer_offsets['x'] + width > image_width or layer_offsets['y'] + height > image_height):\n"
        "        warnings.append({'code': 'out_of_canvas', 'severity': 'warning'})\n"
        "    if include_warnings and text_layer is not None and font is None:\n"
        "        warnings.append({'code': 'missing_font', 'severity': 'warning'})\n"
        "    mode = str(safe_call(lambda: layer.get_mode(), 'unknown'))\n"
        "    if include_warnings and 'PASS_THROUGH' in mode:\n"
        "        warnings.append({'code': 'unsupported_export_state', 'severity': 'warning', 'detail': 'pass-through blend mode may not export identically'})\n"
        "    return {\n"
        "        'id': safe_call(lambda: int(layer.get_id()), None),\n"
        "        'index': index,\n"
        "        'name': safe_call(lambda: layer.get_name(), ''),\n"
        "        'visible': visible,\n"
        "        'width': width,\n"
        "        'height': height,\n"
        "        'offsets': layer_offsets,\n"
        "        'opacity': safe_call(lambda: layer.get_opacity(), None),\n"
        "        'mode': mode,\n"
        "        'is_text_layer': text_layer is not None,\n"
        "        'warnings': warnings,\n"
        "    }",
        "images = Gimp.get_images()",
        "if not images:\n"
        "    result = {'has_image': False, 'report': {'layers': [], 'warnings': ['no open images']}, 'markdown': None}\n"
        "else:\n"
        "    image = images[0]\n"
        "    image_width = int(safe_call(lambda: image.get_width(), 0) or 0)\n"
        "    image_height = int(safe_call(lambda: image.get_height(), 0) or 0)\n"
        "    layers = list(safe_call(lambda: image.get_layers(), []) or [])\n"
        "    layer_rows = [layer_record(layer, index, image_width, image_height) for index, layer in enumerate(layers)]\n"
        "    warnings = [warning for row in layer_rows for warning in row.get('warnings', [])]\n"
        "    report = {'image': {'width': image_width, 'height': image_height}, 'layer_count': len(layer_rows), 'layers': layer_rows, 'warnings': warnings, 'include_previews': include_previews}\n"
        "    markdown = None\n"
        "    if include_markdown:\n"
        "        markdown = '# Layer report\\n\\n' + '\\n'.join([f\"- {row.get('name')} ({row.get('width')}x{row.get('height')}) warnings={len(row.get('warnings', []))}\" for row in layer_rows])\n"
        "    result = {'has_image': True, 'report': report, 'markdown': markdown}",
        "print(json.dumps(result))",
    ]


def _export_checklist_code(
    formats: list[str],
    require_alpha: bool,
    require_layers_preserved: bool,
) -> list[str]:
    """Return generated Python code that validates export readiness without exporting."""
    normalized_formats = ["jpeg" if fmt == "jpg" else fmt for fmt in formats]
    return [
        "import json",
        "# __gimp_mcp_export_checklist__",
        f"formats = {normalized_formats!r}",
        f"require_alpha = {require_alpha!r}",
        f"require_layers_preserved = {require_layers_preserved!r}",
        "format_limitations = {\n"
        "    'png': {'procedure': 'file-png-export', 'preserves_alpha': True, 'preserves_layers': False},\n"
        "    'jpeg': {'procedure': 'file-jpeg-export', 'preserves_alpha': False, 'preserves_layers': False},\n"
        "    'webp': {'procedure': 'file-webp-export', 'preserves_alpha': True, 'preserves_layers': False},\n"
        "    'tiff': {'procedure': 'file-tiff-export', 'preserves_alpha': True, 'preserves_layers': False},\n"
        "    'psd': {'procedure': 'file-psd-export', 'preserves_alpha': True, 'preserves_layers': True},\n"
        "    'xcf': {'procedure': 'gimp-xcf-save', 'preserves_alpha': True, 'preserves_layers': True},\n"
        "}",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "images = Gimp.get_images()",
        "issues = []",
        "recommended_settings = {}",
        "if not images:\n"
        "    issues.append({'code': 'no_open_image', 'severity': 'error'})\n"
        "    image = None\n"
        "    layers = []\n"
        "else:\n"
        "    image = images[0]\n"
        "    layers = list(safe_call(lambda: image.get_layers(), []) or [])",
        "for format_name in formats:\n"
        "    limits = format_limitations[format_name]\n"
        "    recommended_settings[format_name] = {'procedure': limits['procedure']}\n"
        "    if require_alpha and not limits['preserves_alpha']:\n"
        "        issues.append({'format': format_name, 'code': 'alpha_loss', 'severity': 'warning'})\n"
        "    if require_layers_preserved and len(layers) > 1 and not limits['preserves_layers']:\n"
        "        issues.append({'format': format_name, 'code': 'layers_will_flatten', 'severity': 'warning'})\n"
        "    if image is not None and format_name == 'jpeg' and any(safe_call(lambda layer=layer: layer.has_alpha(), False) for layer in layers):\n"
        "        issues.append({'format': format_name, 'code': 'alpha_loss', 'severity': 'warning', 'detail': 'JPEG has no alpha channel'})",
        "ready = not any(issue.get('severity') == 'error' for issue in issues)",
        "result = {'ready': ready, 'issues': issues, 'recommended_settings': recommended_settings, 'formats': formats, 'layer_count': len(layers)}",
        "print(json.dumps(result))",
    ]


def _content_bounds_code(
    target: str,
    threshold: float,
    include_sample_points: bool,
    layer_name: str | None,
    layer_index: int | None,
) -> list[str]:
    """Return generated Python code that computes non-transparent content bounds."""
    return [
        "import json",
        "# __gimp_mcp_content_bounds__",
        f"target = {target!r}",
        f"threshold = {threshold!r}",
        f"include_sample_points = {include_sample_points!r}",
        f"layer_name = {layer_name!r}",
        f"layer_index = {layer_index!r}",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def color_alpha(color):\n"
        "    rgba = safe_call(lambda: color.get_rgba(), None)\n"
        "    if rgba is not None:\n"
        "        return float(getattr(rgba, 'alpha', 0.0))\n"
        "    try:\n"
        "        return float(color[3])\n"
        "    except Exception:\n"
        "        return 0.0",
        "def layer_payload(drawable):\n"
        "    if drawable is None:\n"
        "        return {'target_found': False, 'content_bounds': None, 'fully_transparent': True, 'sample_points': []}\n"
        "    width = int(safe_call(lambda: drawable.get_width(), 0) or 0)\n"
        "    height = int(safe_call(lambda: drawable.get_height(), 0) or 0)\n"
        "    min_x = min_y = None\n"
        "    max_x = max_y = None\n"
        "    samples = []\n"
        "    step = max(1, min(width or 1, height or 1) // 32)\n"
        "    for y in range(0, height, step):\n"
        "        for x in range(0, width, step):\n"
        "            color = safe_call(lambda x=x, y=y: drawable.get_pixel(x, y), None)\n"
        "            alpha = color_alpha(color)\n"
        "            if alpha > threshold:\n"
        "                min_x = x if min_x is None else min(min_x, x)\n"
        "                min_y = y if min_y is None else min(min_y, y)\n"
        "                max_x = x if max_x is None else max(max_x, x)\n"
        "                max_y = y if max_y is None else max(max_y, y)\n"
        "                if include_sample_points and len(samples) < 12:\n"
        "                    samples.append({'x': x, 'y': y, 'alpha': round(alpha, 4)})\n"
        "    bounds = None if min_x is None else {'x': min_x, 'y': min_y, 'width': max_x - min_x + 1, 'height': max_y - min_y + 1}\n"
        "    return {'target_found': True, 'layer_id': safe_call(lambda: int(drawable.get_id()), None), 'layer_name': safe_call(lambda: drawable.get_name(), ''), 'content_bounds': bounds, 'fully_transparent': bounds is None, 'sample_points': samples}",
        "images = Gimp.get_images()",
        "if not images:\n"
        "    result = {'has_image': False, 'content_bounds': None, 'fully_transparent': True, 'warnings': ['no open images']}\n"
        "else:\n"
        "    image = images[0]\n"
        "    layers = list(safe_call(lambda: image.get_layers(), []) or [])\n"
        "    selected = list(safe_call(lambda: image.get_selected_layers(), []) or [])\n"
        "    drawable = None\n"
        "    if layer_name is not None:\n"
        "        drawable = safe_call(lambda: image.get_layer_by_name(layer_name), None)\n"
        "    elif layer_index is not None and 0 <= layer_index < len(layers):\n"
        "        drawable = layers[layer_index]\n"
        "    elif selected:\n"
        "        drawable = selected[0]\n"
        "    elif layers:\n"
        "        drawable = layers[0]\n"
        "    result = layer_payload(drawable)\n"
        "    result.update({'has_image': True, 'target': target, 'threshold': threshold})",
        "print(json.dumps(result))",
    ]


def _text_layer_introspection_code(
    layer_name: str | None,
    layer_index: int | None,
    include_font_details: bool,
) -> list[str]:
    """Return generated Python code that reads text-layer metadata without mutation."""
    return [
        "import json",
        "# __gimp_mcp_text_layer_introspection__",
        f"layer_name = {layer_name!r}",
        f"layer_index = {layer_index!r}",
        f"include_font_details = {include_font_details!r}",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def font_payload(font):\n"
        "    if font is None:\n"
        "        return None\n"
        "    return {'name': safe_call(lambda: font.get_name(), str(font))}",
        "images = Gimp.get_images()",
        "if not images:\n"
        "    result = {'has_image': False, 'is_text_layer': False, 'text': None, 'warnings': ['no open images']}\n"
        "else:\n"
        "    image = images[0]\n"
        "    layers = list(safe_call(lambda: image.get_layers(), []) or [])\n"
        "    selected = list(safe_call(lambda: image.get_selected_layers(), []) or [])\n"
        "    layer = None\n"
        "    if layer_name is not None:\n"
        f"        layer = image.get_layer_by_name({layer_name!r})\n"
        "    elif layer_index is not None and 0 <= layer_index < len(layers):\n"
        "        layer = layers[layer_index]\n"
        "    elif selected:\n"
        "        layer = selected[0]\n"
        "    elif layers:\n"
        "        layer = layers[0]\n"
        "    text_layer = Gimp.TextLayer.get_by_id(layer.get_id()) if layer is not None else None\n"
        "    if text_layer is None:\n"
        "        result = {'has_image': True, 'target_found': layer is not None, 'is_text_layer': False, 'text': None, 'warnings': ['target is not a text layer']}\n"
        "    else:\n"
        "        font = safe_call(lambda: text_layer.get_font(), None)\n"
        "        size = safe_call(lambda: text_layer.get_font_size(), None)\n"
        "        color = safe_call(lambda: str(text_layer.get_color()), None)\n"
        "        result = {\n"
        "            'has_image': True,\n"
        "            'target_found': True,\n"
        "            'is_text_layer': True,\n"
        "            'layer_id': safe_call(lambda: int(layer.get_id()), None),\n"
        "            'layer_name': safe_call(lambda: layer.get_name(), ''),\n"
        "            'text': safe_call(lambda: text_layer.get_text(), ''),\n"
        "            'font': font_payload(font) if include_font_details else safe_call(lambda: font.get_name(), None),\n"
        "            'font_size': size,\n"
        "            'color': color,\n"
        "            'justification': str(safe_call(lambda: text_layer.get_justification(), 'unknown')),\n"
        "            'warnings': [],\n"
        "        }",
        "print(json.dumps(result))",
    ]


def register_geometry_inspect_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register this focused inspect tool subset."""

    @mcp.tool()
    async def measure_geometry(
        targets: list[dict[str, object]] | None = None,
        measurements: list[str] | None = None,
    ) -> ToolResult:
        """Measure bounds, distance, overlap, alignment, and spacing for targets.

        Args:
            targets: List of layer references such as {"layer_name": "A"} or {"layer_index": 0}.
            measurements: Metrics to compute: bounds, distance, overlap, alignment, spacing.

        Returns:
            Operation result with canvas_relative and target_relative geometry metrics.

        Contract:
            This tool is read-only and reports stable pixel-coordinate units.
        """
        selected_targets = targets or []
        selected_measurements = measurements or ["bounds"]
        unknown = [m for m in selected_measurements if m not in SUPPORTED_GEOMETRY_MEASUREMENTS]
        if unknown:
            return OperationResult.fail(
                operation="measure_geometry",
                error=f"unsupported measurement(s): {', '.join(unknown)}",
            ).model_dump()
        if not selected_targets:
            return OperationResult.fail(
                operation="measure_geometry",
                error="at least one target is required",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _measure_geometry_code(selected_targets, selected_measurements)
            )
            data = _json_payload(result)
            data.setdefault("metrics", {})
            data.setdefault("warnings", [])
            return OperationResult.ok(
                operation="measure_geometry",
                message="Geometry measured",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="measure_geometry", error=str(e)).model_dump()

    @mcp.tool()
    async def generate_layer_report(
        include_previews: bool = False,
        include_warnings: bool = True,
        include_markdown: bool = False,
    ) -> ToolResult:
        """Generate a read-only structured report of layers and export-relevant warnings.

        Args:
            include_previews: Reserve preview metadata in the report without embedding bitmaps.
            include_warnings: Flag hidden, empty, out-of-canvas, missing-font, and export issues.
            include_markdown: Include a compact Markdown summary for human handoff.

        Returns:
            Operation result with a structured report and optional Markdown summary.

        Contract:
            This tool is read-only. It observes layer state and does not modify the image.
        """
        try:
            result = await bridge.async_execute_python(
                _layer_report_code(include_previews, include_warnings, include_markdown)
            )
            data = _json_payload(result)
            data.setdefault("report", {"layers": [], "warnings": []})
            data.setdefault("markdown", None)
            return OperationResult.ok(
                operation="generate_layer_report",
                message="Layer report generated",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="generate_layer_report", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def prepare_export_checklist(
        formats: list[str] | None = None,
        require_alpha: bool = False,
        require_layers_preserved: bool = False,
    ) -> ToolResult:
        """Prepare a read-only export readiness checklist for common image formats.

        Args:
            formats: Formats to evaluate. Supported: png, jpeg/jpg, webp, tiff, psd, xcf.
            require_alpha: Flag formats that would lose required alpha information.
            require_layers_preserved: Flag formats that would flatten required layer data.

        Returns:
            Operation result with ready flag, issues, and recommended export settings.

        Contract:
            This tool does not export files. Use export_image or a dedicated export tool separately.
        """
        selected_formats = [fmt.lower() for fmt in (formats or ["png"])]
        unsupported = [fmt for fmt in selected_formats if fmt not in SUPPORTED_EXPORT_FORMATS]
        if unsupported:
            return OperationResult.fail(
                operation="prepare_export_checklist",
                error=f"unsupported export format(s): {', '.join(unsupported)}",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _export_checklist_code(
                    selected_formats,
                    require_alpha,
                    require_layers_preserved,
                )
            )
            data = _json_payload(result)
            data.setdefault("ready", False)
            data.setdefault("issues", [])
            data.setdefault("recommended_settings", {})
            return OperationResult.ok(
                operation="prepare_export_checklist",
                message="Export checklist prepared",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="prepare_export_checklist", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def content_bounds(
        target: str = "active_layer",
        threshold: float = 0.0,
        include_sample_points: bool = False,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Inspect non-transparent content bounds for a layer without mutation.

        Args:
            target: Target mode label. Currently active_layer is the default path.
            threshold: Alpha threshold from 0.0 to 1.0 for deciding content presence.
            include_sample_points: Include a bounded list of sampled content pixels.
            layer_name: Optional layer name target.
            layer_index: Optional layer index target.

        Returns:
            Operation result with content_bounds, fully_transparent, and sample evidence.

        Contract:
            This tool is read-only. It never crops, resizes, selects, or edits the target layer.
        """
        if threshold < 0.0 or threshold > 1.0:
            return OperationResult.fail(
                operation="content_bounds",
                error="threshold must be between 0.0 and 1.0",
            ).model_dump()
        if target not in {"active_layer", "selected_layer", "layer"}:
            return OperationResult.fail(
                operation="content_bounds",
                error="target must be active_layer, selected_layer, or layer",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _content_bounds_code(
                    target,
                    threshold,
                    include_sample_points,
                    layer_name,
                    layer_index,
                )
            )
            data = _json_payload(result)
            data.setdefault("content_bounds", None)
            data.setdefault("fully_transparent", True)
            data.setdefault("sample_points", [])
            return OperationResult.ok(
                operation="content_bounds",
                message="Content bounds inspected",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="content_bounds", error=str(e)).model_dump()

    @mcp.tool()
    async def text_layer_introspection(
        layer_name: str | None = None,
        layer_index: int | None = None,
        include_font_details: bool = True,
    ) -> ToolResult:
        """Read text-layer metadata without rasterizing or mutating the layer.

        Args:
            layer_name: Optional layer name target.
            layer_index: Optional layer index target.
            include_font_details: Include structured font details where GIMP exposes them.

        Returns:
            Operation result with text, font, size, color, justification, and warnings.

        Contract:
            This tool is read-only and returns a structured unsupported state for non-text layers.
        """
        try:
            result = await bridge.async_execute_python(
                _text_layer_introspection_code(layer_name, layer_index, include_font_details)
            )
            data = _json_payload(result)
            data.setdefault("is_text_layer", False)
            data.setdefault("text", None)
            data.setdefault("warnings", [])
            return OperationResult.ok(
                operation="text_layer_introspection",
                message="Text layer introspected",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="text_layer_introspection", error=str(e)
            ).model_dump()
