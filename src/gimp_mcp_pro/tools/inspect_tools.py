"""Inspection tools for GIMP MCP Pro — image viewing, metadata, context state."""

from __future__ import annotations

import json
import logging
from typing import Any

from gimp_mcp_pro import __version__
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, CommandParams, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.inspect")


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


def _document_state_code() -> list[str]:
    """Return generated Python code that observes the active document state."""
    return [
        "import json",
        "# __gimp_mcp_document_state__",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def stable_id(obj):\n"
        "    return safe_call(lambda: int(obj.get_id()), None) if obj is not None else None",
        "def offsets(obj):\n"
        "    off = safe_call(lambda: obj.get_offsets(), None)\n"
        "    if off is None:\n"
        "        return {'x': 0, 'y': 0}\n"
        "    if hasattr(off, 'offset_x'):\n"
        "        return {'x': off.offset_x, 'y': off.offset_y}\n"
        "    try:\n"
        "        return {'x': off[0], 'y': off[1]}\n"
        "    except Exception:\n"
        "        return {'x': 0, 'y': 0}",
        "def layer_info(layer, index):\n"
        "    layer_offsets = offsets(layer)\n"
        "    return {\n"
        "        'id': stable_id(layer),\n"
        "        'index': index,\n"
        "        'name': safe_call(lambda: layer.get_name(), ''),\n"
        "        'type': type(layer).__name__,\n"
        "        'visible': bool(safe_call(lambda: layer.get_visible(), True)),\n"
        "        'opacity': safe_call(lambda: layer.get_opacity(), None),\n"
        "        'mode': str(safe_call(lambda: layer.get_mode(), 'unknown')),\n"
        "        'width': safe_call(lambda: layer.get_width(), None),\n"
        "        'height': safe_call(lambda: layer.get_height(), None),\n"
        "        'offsets': layer_offsets,\n"
        "        'bounds': {'x': layer_offsets['x'], 'y': layer_offsets['y'], 'width': safe_call(lambda: layer.get_width(), None), 'height': safe_call(lambda: layer.get_height(), None)},\n"
        "        'has_alpha': bool(safe_call(lambda: layer.has_alpha(), False)),\n"
        "        'is_group': bool(safe_call(lambda: layer.is_group(), False)),\n"
        "        'lock_content': bool(safe_call(lambda: layer.get_lock_content(), False)),\n"
        "        'lock_position': bool(safe_call(lambda: layer.get_lock_position(), False)),\n"
        "        'editable': not bool(safe_call(lambda: layer.get_lock_content(), False)),\n"
        "    }",
        "images = Gimp.get_images()",
        "if not images:\n"
        "    result = {'has_image': False, 'image_id': None, 'dimensions': None, 'color_mode': None, 'active_layer': None, 'layer_tree': [], 'selections': {'non_empty': False}, 'guides': [], 'paths': [], 'channels': [], 'warnings': ['no open images']}\n"
        "else:\n"
        "    image = images[0]\n"
        "    layers = list(safe_call(lambda: image.get_layers(), []) or [])\n"
        "    selected = list(safe_call(lambda: image.get_selected_layers(), []) or [])\n"
        "    active = selected[0] if selected else (layers[0] if layers else None)\n"
        "    bounds = safe_call(lambda: Gimp.Selection.bounds(image), None)\n"
        "    selection = {'non_empty': False}\n"
        "    if bounds is not None:\n"
        "        selection = {\n"
        "            'non_empty': bool(getattr(bounds, 'non_empty', False)),\n"
        "            'x1': getattr(bounds, 'x1', None),\n"
        "            'y1': getattr(bounds, 'y1', None),\n"
        "            'x2': getattr(bounds, 'x2', None),\n"
        "            'y2': getattr(bounds, 'y2', None),\n"
        "        }\n"
        "    result = {\n"
        "        'has_image': True,\n"
        "        'image_id': stable_id(image),\n"
        "        'dimensions': {'width': safe_call(lambda: image.get_width(), None), 'height': safe_call(lambda: image.get_height(), None)},\n"
        "        'color_mode': str(safe_call(lambda: image.get_base_type(), 'unknown')),\n"
        "        'file': str(safe_call(lambda: image.get_file().get_path(), '') or ''),\n"
        "        'is_dirty': bool(safe_call(lambda: image.is_dirty(), False)),\n"
        "        'active_layer': layer_info(active, layers.index(active)) if active in layers else None,\n"
        "        'selected_layer_ids': [stable_id(layer) for layer in selected],\n"
        "        'layer_tree': [layer_info(layer, index) for index, layer in enumerate(layers)],\n"
        "        'layers_flat': [layer_info(layer, index) for index, layer in enumerate(layers)],\n"
        "        'selections': selection,\n"
        "        'guides': [],\n"
        "        'paths': [],\n"
        "        'channels': [],\n"
        "        'warnings': [],\n"
        "    }",
        "print(json.dumps(result))",
    ]


def _layer_tree_code(
    image_id: int | None, include_pixel_bounds: bool, include_text_metadata: bool
) -> list[str]:
    """Return generated Python code that inspects the layer tree."""
    return _document_state_code()[:-1] + [
        "# __gimp_mcp_layer_tree__",
        f"requested_image_id = {image_id!r}",
        f"include_pixel_bounds = {include_pixel_bounds!r}",
        f"include_text_metadata = {include_text_metadata!r}",
        "if result.get('has_image'):\n"
        "    layers = result.get('layers_flat', [])\n"
        "    groups = [layer for layer in layers if layer.get('is_group')]\n"
        "    warnings = []\n"
        "    for layer in layers:\n"
        "        if not layer.get('visible', True): warnings.append({'layer_id': layer.get('id'), 'warning': 'layer_hidden'})\n"
        "        if layer.get('lock_content'): warnings.append({'layer_id': layer.get('id'), 'warning': 'content_locked'})\n"
        "    result = {'image_id': result.get('image_id'), 'layers': layers, 'groups': groups, 'warnings': warnings, 'include_pixel_bounds': include_pixel_bounds, 'include_text_metadata': include_text_metadata}\n"
        "else:\n"
        "    result = {'image_id': None, 'layers': [], 'groups': [], 'warnings': ['no open images'], 'include_pixel_bounds': include_pixel_bounds, 'include_text_metadata': include_text_metadata}",
        "print(json.dumps(result))",
    ]


def _session_capabilities_code(include_pdb_probe: bool, include_export_probe: bool) -> list[str]:
    """Return generated Python code that reports read-only runtime capabilities."""
    probes = [
        "file-png-export",
        "file-jpeg-export",
        "gimp-image-undo",
        "gimp-image-redo",
        "gimp-image-autocrop",
        "script-fu-drop-shadow",
    ]
    return [
        "import json, platform, sys",
        "# __gimp_mcp_session_capabilities__",
        f"include_pdb_probe = {include_pdb_probe!r}",
        f"include_export_probe = {include_export_probe!r}",
        f"probe_names = {probes!r}",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "pdb = safe_call(lambda: Gimp.get_pdb(), None)",
        "procedure_map = {}",
        "if include_pdb_probe and pdb is not None:\n"
        "    for name in probe_names:\n"
        "        procedure_map[name] = bool(safe_call(lambda n=name: pdb.lookup_procedure(n), None))",
        "export_map = {}",
        "if include_export_probe:\n"
        "    for name in ['file-png-export', 'file-jpeg-export']:\n"
        "        export_map[name] = procedure_map.get(name, bool(safe_call(lambda n=name: pdb.lookup_procedure(n), None)) if pdb is not None else False)",
        "result = {\n"
        "    'gimp_version': str(safe_call(lambda: Gimp.version(), 'unknown')),\n"
        "    'api_namespace': '3.0',\n"
        "    'python_version': sys.version.split()[0],\n"
        "    'platform': platform.platform(),\n"
        "    'open_images': len(safe_call(lambda: Gimp.get_images(), []) or []),\n"
        "    'capabilities': {\n"
        "        'pdb_available': pdb is not None,\n"
        "        'procedures': procedure_map,\n"
        "        'export': export_map,\n"
        "        'safety_mode': 'localhost-only',\n"
        "        'supports_observation_tools': True,\n"
        "        'supports_target_validation': True,\n"
        "    },\n"
        "    'unavailable': [name for name, available in procedure_map.items() if not available],\n"
        "}\n",
        "print(json.dumps(result))",
    ]


def _region_sample_code(
    x: int, y: int, width: int, height: int, include_histogram: bool
) -> list[str]:
    """Return generated Python code for lightweight region metadata and samples."""
    return [
        "import json",
        "# __gimp_mcp_region_samples__",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def color_to_dict(color):\n"
        "    rgba = safe_call(lambda: color.get_rgba(), None)\n"
        "    if rgba is None: return {'value': str(color)}\n"
        "    return {'r': round(rgba.red, 4), 'g': round(rgba.green, 4), 'b': round(rgba.blue, 4), 'a': round(rgba.alpha, 4)}",
        "images = Gimp.get_images()",
        "samples = []",
        "if images:\n"
        "    image = images[0]\n"
        "    layers = list(safe_call(lambda: image.get_selected_layers(), []) or safe_call(lambda: image.get_layers(), []) or [])\n"
        "    drawable = layers[0] if layers else None\n"
        f"    points = [({x}, {y}), ({x + width // 2}, {y + height // 2}), ({x + width - 1}, {y + height - 1})]\n"
        "    if drawable is not None:\n"
        "        for px, py in points:\n"
        "            color = safe_call(lambda px=px, py=py: drawable.get_pixel(px, py), None)\n"
        "            samples.append({'x': px, 'y': py, 'color': color_to_dict(color) if color is not None else None})\n",
        f"result = {{'region_bounds': {{'x': {x}, 'y': {y}, 'width': {width}, 'height': {height}}}, 'sampled_colors': samples, 'histogram': None, 'include_histogram': {include_histogram!r}}}",
        "print(json.dumps(result))",
    ]



def _contact_sheet_code(
    target: str,
    max_tile_size: int,
    label_tiles: bool,
    include_hidden_layers: bool,
) -> list[str]:
    """Return generated Python code that creates contact-sheet metadata."""
    return [
        "import json",
        "# __gimp_mcp_contact_sheet__",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        f"target = {target!r}",
        f"max_tile_size = {max_tile_size!r}",
        f"label_tiles = {label_tiles!r}",
        f"include_hidden_layers = {include_hidden_layers!r}",
        "layers = list(safe_call(lambda: image.get_layers(), []) or [])",
        "tile_index = []",
        "visible_candidates = []",
        "for layer in layers:\n"
        "    visible = bool(safe_call(lambda layer=layer: layer.get_visible(), True))\n"
        "    if not include_hidden_layers and not visible:\n"
        "        continue\n"
        "    layer_id = safe_call(lambda layer=layer: int(layer.get_id()), None)\n"
        "    layer_name = safe_call(lambda layer=layer: layer.get_name(), '')\n"
        "    width = safe_call(lambda layer=layer: layer.get_width(), 0)\n"
        "    height = safe_call(lambda layer=layer: layer.get_height(), 0)\n"
        "    tile_index.append({'id': layer_id, 'name': layer_name, 'visible': visible, 'width': width, 'height': height, 'label': f'{layer_id}: {layer_name}' if label_tiles else None})\n"
        "    visible_candidates.append(layer)",
        "columns = max(1, int(len(tile_index) ** 0.5 + 0.999))",
        "rows = 0 if not tile_index else (len(tile_index) + columns - 1) // columns",
        "contact_sheet_png = None",
        "result = {'contact_sheet_png': contact_sheet_png, 'tile_index': tile_index, 'tile_count': len(tile_index), 'columns': columns, 'rows': rows, 'max_tile_size': max_tile_size, 'label_tiles': label_tiles, 'include_hidden_layers': include_hidden_layers, 'warnings': ['contact_sheet_png is reserved for live bitmap export; tile_index is authoritative']}",
        "print(json.dumps(result))",
    ]


def _scalar_fields(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten stable scalar fields from a snapshot for structural comparison."""
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key, nested in value.items():
            nested_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_scalar_fields(nested, nested_prefix))
        return flattened
    if isinstance(value, list):
        return {f"{prefix}.length" if prefix else "length": len(value)}
    if isinstance(value, str | int | float | bool) or value is None:
        return {prefix: value} if prefix else {}
    return {prefix: repr(value)} if prefix else {}


def _region_contains(region: dict[str, Any] | None, x: float, y: float) -> bool:
    """Return whether a point is inside an optional inclusive-exclusive region."""
    if not region:
        return True
    left = float(region.get("x", region.get("origin_x", 0)))
    top = float(region.get("y", region.get("origin_y", 0)))
    width = float(region.get("width", 0))
    height = float(region.get("height", 0))
    return left <= x < left + width and top <= y < top + height


def _sample_color(sample: dict[str, Any]) -> dict[str, float] | None:
    """Extract an RGBA-like mapping from a sampled color payload."""
    raw = sample.get("rgba") or sample.get("color")
    if not isinstance(raw, dict):
        return None
    try:
        return {
            "r": float(raw.get("r", 0.0)),
            "g": float(raw.get("g", 0.0)),
            "b": float(raw.get("b", 0.0)),
            "a": float(raw.get("a", 1.0)),
        }
    except (TypeError, ValueError):
        return None


def _color_delta(before: dict[str, float], after: dict[str, float]) -> float:
    """Return a compact RGBA mean absolute delta."""
    return sum(abs(after[channel] - before[channel]) for channel in ("r", "g", "b", "a")) / 4.0


def _snapshot_samples(snapshot: dict[str, Any]) -> dict[tuple[float, float], dict[str, Any]]:
    """Index sampled colors by point coordinates."""
    samples = snapshot.get("sampled_colors") or snapshot.get("samples") or []
    indexed: dict[tuple[float, float], dict[str, Any]] = {}
    if not isinstance(samples, list):
        return indexed
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        try:
            key = (float(sample["x"]), float(sample["y"]))
        except (KeyError, TypeError, ValueError):
            continue
        indexed[key] = sample
    return indexed


def _compare_snapshot_data(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    region: dict[str, Any] | None = None,
    ignore_transparent: bool = False,
    tolerance: float = 0.0,
) -> dict[str, Any]:
    """Compare two supplied snapshot-like payloads without mutating GIMP."""
    before_samples = _snapshot_samples(before)
    after_samples = _snapshot_samples(after)
    changed_points: list[tuple[float, float]] = []
    deltas: list[float] = []
    ignored_transparent = 0

    for point in sorted(before_samples.keys() & after_samples.keys()):
        x, y = point
        if not _region_contains(region, x, y):
            continue
        before_color = _sample_color(before_samples[point])
        after_color = _sample_color(after_samples[point])
        if before_color is None or after_color is None:
            continue
        delta = _color_delta(before_color, after_color)
        if ignore_transparent and (before_color["a"] <= 0.0 or after_color["a"] <= 0.0):
            if delta > tolerance:
                ignored_transparent += 1
            continue
        if delta > tolerance:
            changed_points.append(point)
            deltas.append(delta)

    bounding_box: dict[str, int] | None = None
    if changed_points:
        xs = [point[0] for point in changed_points]
        ys = [point[1] for point in changed_points]
        min_x, max_x = int(min(xs)), int(max(xs))
        min_y, max_y = int(min(ys)), int(max(ys))
        bounding_box = {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x + 1,
            "height": max_y - min_y + 1,
        }

    changed_fields: list[str] = []
    if not before_samples and not after_samples:
        before_fields = _scalar_fields(before)
        after_fields = _scalar_fields(after)
        changed_fields = sorted(
            key
            for key in set(before_fields) | set(after_fields)
            if before_fields.get(key) != after_fields.get(key)
        )

    before_bitmap = before.get("image_data") or before.get("crop_png")
    after_bitmap = after.get("image_data") or after.get("crop_png")
    bitmap_changed = bool(
        before_bitmap is not None and after_bitmap is not None and before_bitmap != after_bitmap
    )

    return {
        "changed_pixels": len(changed_points),
        "bounding_box": bounding_box,
        "mean_delta": round(sum(deltas) / len(deltas), 6) if deltas else 0.0,
        "changed_fields": changed_fields,
        "bitmap_changed": bitmap_changed,
        "ignored_transparent_samples": ignored_transparent,
        "compared_samples": len(before_samples.keys() & after_samples.keys()),
        "region": region,
    }


def _find_layer(state: dict[str, Any], assertion: dict[str, Any]) -> dict[str, Any] | None:
    """Find a layer in a document-state payload by name, id, or index."""
    layers = state.get("layer_tree") or state.get("layers_flat") or state.get("layers") or []
    if not isinstance(layers, list):
        return None
    expected_name = assertion.get("name") or assertion.get("layer_name")
    expected_id = assertion.get("id") or assertion.get("layer_id")
    expected_index = assertion.get("index") or assertion.get("layer_index")
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        if expected_name is not None and layer.get("name") == expected_name:
            return layer
        if expected_id is not None and layer.get("id") == expected_id:
            return layer
        if expected_index is not None and layer.get("index") == expected_index:
            return layer
    return None


def _assertion_result(
    index: int, assertion: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate one typed image-state assertion."""
    kind = str(assertion.get("type") or assertion.get("kind") or "").strip()
    if kind == "layer_exists":
        layer = _find_layer(state, assertion)
        label = (
            assertion.get("name")
            or assertion.get("layer_name")
            or assertion.get("id")
            or assertion.get("index")
        )
        passed = layer is not None
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "message": f"Layer {label!r} exists" if passed else f"Layer {label!r} does not exist",
        }
    if kind == "layer_visible":
        layer = _find_layer(state, assertion)
        expected = bool(assertion.get("visible", True))
        actual = bool(layer.get("visible", True)) if layer else None
        passed = layer is not None and actual == expected
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "message": f"Layer visibility is {actual}, expected {expected}",
        }
    if kind == "dimensions_equal":
        dimensions = state.get("dimensions") or state.get("basic") or {}
        actual_width = dimensions.get("width") if isinstance(dimensions, dict) else None
        actual_height = dimensions.get("height") if isinstance(dimensions, dict) else None
        expected_width = assertion.get("width")
        expected_height = assertion.get("height")
        passed = actual_width == expected_width and actual_height == expected_height
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": {"width": expected_width, "height": expected_height},
            "actual": {"width": actual_width, "height": actual_height},
            "message": f"Dimensions are {actual_width}x{actual_height}, expected {expected_width}x{expected_height}",
        }
    if kind == "selection_non_empty":
        selection = state.get("selections") or state.get("selection") or {}
        actual = bool(selection.get("non_empty", False)) if isinstance(selection, dict) else False
        expected = bool(assertion.get("expected", True))
        passed = actual == expected
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "message": f"Selection non-empty is {actual}, expected {expected}",
        }
    if kind == "color_close":
        actual = assertion.get("actual")
        expected = assertion.get("expected")
        tolerance = float(assertion.get("tolerance", 0.01))
        passed = False
        delta = None
        if isinstance(actual, dict) and isinstance(expected, dict):
            actual_color = _sample_color({"rgba": actual})
            expected_color = _sample_color({"rgba": expected})
            if actual_color is not None and expected_color is not None:
                delta = _color_delta(actual_color, expected_color)
                passed = delta <= tolerance
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "delta": delta,
            "tolerance": tolerance,
            "message": f"Color delta {delta} is within tolerance {tolerance}"
            if passed
            else f"Color delta {delta} exceeds tolerance {tolerance}",
        }
    if kind == "region_changed":
        comparison = assertion.get("comparison") or {}
        changed_pixels = comparison.get("changed_pixels", 0) if isinstance(comparison, dict) else 0
        minimum = int(assertion.get("min_changed_pixels", 1))
        passed = int(changed_pixels) >= minimum
        return {
            "index": index,
            "type": kind,
            "passed": passed,
            "expected": {"min_changed_pixels": minimum},
            "actual": {"changed_pixels": changed_pixels},
            "message": f"Region changed pixels {changed_pixels}, expected at least {minimum}",
        }
    return {
        "index": index,
        "type": kind or "unknown",
        "passed": False,
        "message": f"Unsupported assertion type: {kind or 'missing'}",
    }



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


def register_inspect_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all inspection tools with the MCP server."""


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


    @mcp.tool()
    async def create_contact_sheet(
        target: str = "visible_layers",
        max_tile_size: int = 128,
        label_tiles: bool = True,
        include_hidden_layers: bool = False,
    ) -> ToolResult:
        """Render contact-sheet metadata for visible or selected layers.

        Args:
            target: Layer candidate set, currently ``visible_layers`` or ``all_layers``.
            max_tile_size: Maximum tile size requested for future bitmap rendering.
            label_tiles: Include stable layer ID/name labels in the tile index.
            include_hidden_layers: Include hidden layers instead of filtering them out.

        Returns:
            Operation result with ``contact_sheet_png`` placeholder and authoritative tile index.

        Contract:
            This inspection tool is read-only. It labels tiles with stable layer IDs
            and applies the hidden-layer policy explicitly.
        """
        if max_tile_size < 16 or max_tile_size > 1024:
            return OperationResult.fail(
                operation="create_contact_sheet",
                error="max_tile_size must be between 16 and 1024",
            ).model_dump()
        if target not in {"visible_layers", "all_layers", "selected"}:
            return OperationResult.fail(
                operation="create_contact_sheet",
                error="target must be visible_layers, all_layers, or selected",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _contact_sheet_code(target, max_tile_size, label_tiles, include_hidden_layers)
            )
            data = _json_payload(result)
            data.setdefault("contact_sheet_png", None)
            data.setdefault("tile_index", [])
            return OperationResult.ok(
                operation="create_contact_sheet",
                message=f"Contact sheet index contains {len(data.get('tile_index', []))} tile(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="create_contact_sheet", error=str(e)).model_dump()

    @mcp.tool()
    async def compare_snapshots(
        before: dict[str, Any],
        after: dict[str, Any],
        metrics: list[str] | None = None,
        region: dict[str, Any] | None = None,
        ignore_transparent: bool = False,
        tolerance: float = 0.0,
    ) -> ToolResult:
        """Compare two supplied snapshot, thumbnail, or region payloads.

        Notes:
            This verification tool is intentionally read-only and deterministic.
            It compares sampled region colors when present, otherwise falls back
            to stable scalar-field differences. Ordinary visual mismatches are
            returned as structured data, not exceptions.

        Args:
            before: Snapshot-like payload captured before an operation.
            after: Snapshot-like payload captured after an operation.
            metrics: Optional metric names requested by the caller.
            region: Optional bounded region to limit sampled-color comparison.
            ignore_transparent: Ignore sampled points where either side is fully transparent.
            tolerance: RGBA mean absolute delta threshold for sampled colors.

        Returns:
            Operation result with changed sample count, bounding box, mean delta, and changed fields.
        """
        if not isinstance(before, dict) or not isinstance(after, dict):
            return OperationResult.fail(
                operation="compare_snapshots",
                error="before and after must be snapshot dictionaries",
            ).model_dump()
        if tolerance < 0:
            return OperationResult.fail(
                operation="compare_snapshots",
                error="tolerance must be >= 0",
            ).model_dump()
        data = _compare_snapshot_data(
            before,
            after,
            region=region,
            ignore_transparent=ignore_transparent,
            tolerance=tolerance,
        )
        data["metrics"] = metrics or ["changed_pixels", "bounding_box", "mean_delta"]
        return OperationResult.ok(
            operation="compare_snapshots",
            message="Snapshots compared",
            data=data,
        ).model_dump()

    @mcp.tool()
    async def assert_image_state(
        assertions: list[dict[str, Any]] | None = None,
        state: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Evaluate typed postconditions against supplied or active document state.

        Notes:
            Use this after edits to verify facts such as layer existence,
            layer visibility, canvas dimensions, non-empty selection, and color
            closeness. Failed assertions are reported in ``data.results`` while
            the tool call itself still succeeds.

        Args:
            assertions: List of typed assertion dictionaries.
            state: Optional state payload. When absent, the active GIMP document is observed.

        Returns:
            Operation result whose data contains ``passed`` plus per-assertion results.
        """
        assertion_list = assertions or []
        if not isinstance(assertion_list, list):
            return OperationResult.fail(
                operation="assert_image_state",
                error="assertions must be a list",
            ).model_dump()
        try:
            resolved_state = state
            state_source = "provided"
            if resolved_state is None:
                observed = await bridge.async_execute_python(_document_state_code())
                resolved_state = _json_payload(observed)
                state_source = "observed"
            if not isinstance(resolved_state, dict):
                return OperationResult.fail(
                    operation="assert_image_state",
                    error="state must be a dictionary",
                ).model_dump()
            results = [
                _assertion_result(index, assertion, resolved_state)
                for index, assertion in enumerate(assertion_list)
                if isinstance(assertion, dict)
            ]
            invalid_count = len(assertion_list) - len(results)
            for _ in range(invalid_count):
                results.append(
                    {
                        "index": len(results),
                        "type": "invalid",
                        "passed": False,
                        "message": "Assertion must be a dictionary",
                    }
                )
            passed = all(result.get("passed") is True for result in results)
            return OperationResult.ok(
                operation="assert_image_state",
                message="Image state assertions evaluated",
                data={
                    "passed": passed,
                    "results": results,
                    "assertion_count": len(assertion_list),
                    "state_source": state_source,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="assert_image_state", error=str(e)).model_dump()

    @mcp.tool()
    async def session_capabilities(
        include_pdb_probe: bool = True,
        include_export_probe: bool = True,
    ) -> ToolResult:
        """Report GIMP runtime capabilities and safety-relevant environment state.

        Notes:
            This read-only tool should be the first call in an autonomous workflow.
            It tells the agent which GIMP version, plug-in version, PDB procedures,
            export procedures, and safety mode are currently available.

        Args:
            include_pdb_probe: Probe selected PDB procedures by name.
            include_export_probe: Include export-specific procedure availability.

        Returns:
            Operation result with version, capability, unavailable-procedure, and safety data.
        """
        try:
            result = await bridge.async_execute_python(
                _session_capabilities_code(include_pdb_probe, include_export_probe)
            )
            data = _json_payload(result)
            data.setdefault("plugin_version", __version__)
            return OperationResult.ok(
                operation="session_capabilities",
                message="Session capabilities retrieved",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="session_capabilities", error=str(e)).model_dump()

    @mcp.tool()
    async def observe_document_state(
        include_thumbnail: bool = False,
        include_layer_previews: bool = False,
        max_preview_size: int = 256,
    ) -> ToolResult:
        """Return a compact snapshot of the active GIMP document state.

        Notes:
            Use this before planning edits. It includes stable image/layer IDs,
            dimensions, active layer, selected layers, layer tree, selection state,
            guides, paths, channels, and optional bounded thumbnail evidence.

        Args:
            include_thumbnail: Include a bounded PNG thumbnail of the active document.
            include_layer_previews: Reserved flag for future per-layer previews.
            max_preview_size: Maximum thumbnail width/height when thumbnail is requested.

        Returns:
            Operation result with document state and optional thumbnail metadata.
        """
        if max_preview_size < 1 or max_preview_size > 2048:
            return OperationResult.fail(
                operation="observe_document_state",
                error="max_preview_size must be between 1 and 2048",
            ).model_dump()

        try:
            result = await bridge.async_execute_python(_document_state_code())
            data = _json_payload(result)
            warnings = (
                list(data.get("warnings", [])) if isinstance(data.get("warnings", []), list) else []
            )

            if include_thumbnail:
                bitmap = await bridge.async_get_image_bitmap(
                    max_width=max_preview_size,
                    max_height=max_preview_size,
                )
                if bitmap.get("status") == "success":
                    data["thumbnail"] = bitmap.get("results", {})
                else:
                    warnings.append({"thumbnail": bitmap.get("error", "thumbnail capture failed")})
            if include_layer_previews:
                warnings.append(
                    {"layer_previews": "per-layer previews are reserved for a follow-up feature"}
                )
            data["warnings"] = warnings
            return OperationResult.ok(
                operation="observe_document_state",
                message="Document state observed",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="observe_document_state", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def get_layer_tree_detailed(
        image_id: int | None = None,
        include_pixel_bounds: bool = True,
        include_text_metadata: bool = True,
    ) -> ToolResult:
        """Return detailed layer, group, visibility, lock, and bounds metadata.

        Notes:
            Use this before mutating layers. It identifies hidden or content-locked
            layers and returns stable IDs, names, indices, dimensions, offsets,
            opacity, mode, alpha, type hints, and group hints where GIMP exposes them.

        Args:
            image_id: Optional image ID hint. Current implementation observes the active image.
            include_pixel_bounds: Include layer pixel bounds when available.
            include_text_metadata: Include text-layer metadata when available.

        Returns:
            Operation result with layers, groups, and editability warnings.
        """
        try:
            result = await bridge.async_execute_python(
                _layer_tree_code(image_id, include_pixel_bounds, include_text_metadata)
            )
            data = _json_payload(result)
            return OperationResult.ok(
                operation="get_layer_tree_detailed",
                message=f"Observed {len(data.get('layers', []))} layer(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="get_layer_tree_detailed", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def observe_region(
        x: int,
        y: int,
        width: int,
        height: int,
        max_size: int = 512,
        include_histogram: bool = False,
    ) -> ToolResult:
        """Return a bounded visual observation and metadata for a rectangular region.

        Notes:
            Use this to inspect details without transferring the full canvas. The
            bitmap is downsampled to max_size and accompanied by actual source
            bounds plus a small set of sampled colors.

        Args:
            x: Region left coordinate in canvas pixels.
            y: Region top coordinate in canvas pixels.
            width: Region width in pixels.
            height: Region height in pixels.
            max_size: Maximum output width/height for the region PNG.
            include_histogram: Reserve space for histogram data when implemented.

        Returns:
            Operation result with cropped PNG data, region bounds, samples, and metadata.
        """
        if width < 1 or height < 1:
            return OperationResult.fail(
                operation="observe_region", error="width and height must be >= 1"
            ).model_dump()
        if max_size < 1 or max_size > 4096:
            return OperationResult.fail(
                operation="observe_region", error="max_size must be between 1 and 4096"
            ).model_dump()

        try:
            bitmap = await bridge.async_get_image_bitmap(
                max_width=max_size,
                max_height=max_size,
                region={"origin_x": x, "origin_y": y, "width": width, "height": height},
            )
            if bitmap.get("status") != "success":
                return OperationResult.fail(
                    operation="observe_region",
                    error=bitmap.get("error", "Failed to observe region"),
                ).model_dump()

            sample_result = await bridge.async_execute_python(
                _region_sample_code(x, y, width, height, include_histogram)
            )
            sample_data = _json_payload(sample_result)
            bitmap_results: dict[str, Any] = bitmap.get("results", {})
            if not isinstance(bitmap_results, dict):
                bitmap_results = {}
            data = {
                "crop_png": bitmap_results.get("image_data", ""),
                "format": "png",
                "encoding": "base64",
                "width": bitmap_results.get("width"),
                "height": bitmap_results.get("height"),
                "original_width": bitmap_results.get("original_width"),
                "original_height": bitmap_results.get("original_height"),
                "region_bounds": sample_data.get(
                    "region_bounds", {"x": x, "y": y, "width": width, "height": height}
                ),
                "sampled_colors": sample_data.get("sampled_colors", []),
                "histogram": sample_data.get("histogram"),
            }
            return OperationResult.ok(
                operation="observe_region",
                message=f"Observed region ({x},{y}) {width}x{height}",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="observe_region", error=str(e)).model_dump()

    @mcp.tool()
    async def get_image_bitmap(
        max_width: int | None = 1024,
        max_height: int | None = 1024,
        region_x: int | None = None,
        region_y: int | None = None,
        region_width: int | None = None,
        region_height: int | None = None,
    ) -> ToolResult:
        """Get the current image as a viewable bitmap (PNG).

        Notes:
            Primary use: Verification tool for checking work mid-workflow.

            Best practice guidance:
            - Check after every three to five drawing operations.
            - Use region extraction to verify specific areas at higher quality.
            - Check before the final step so mistakes are caught early.

        Args:
            max_width: Optional maximum width for scaling (default 1024). Use None for full size.
            max_height: Optional maximum height for scaling (default 1024). Use None for full size.
            region_x: Optional — extract only this region (left X)
            region_y: Optional — extract only this region (top Y)
            region_width: Optional — region width
            region_height: Optional — region height

        Returns:
            MCP Image object containing PNG data that the AI can view directly.
        """
        params: CommandParams = {}
        if max_width is not None:
            params["max_width"] = max_width
        if max_height is not None:
            params["max_height"] = max_height

        if any(v is not None for v in [region_x, region_y, region_width, region_height]):
            if not all(v is not None for v in [region_x, region_y, region_width, region_height]):
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error="All region parameters (region_x, region_y, region_width, region_height) "
                    "must be specified together",
                ).model_dump()
            params["region"] = {
                "origin_x": region_x,
                "origin_y": region_y,
                "width": region_width,
                "height": region_height,
            }

        try:
            result = await bridge.async_get_image_bitmap(
                max_width=params.get("max_width"),
                max_height=params.get("max_height"),
                region=params.get("region"),
            )

            if result.get("status") == "success":
                image_info: dict[str, Any] = result.get("results", {})
                return OperationResult.ok(
                    operation="get_image_bitmap",
                    message=(
                        f"Image captured: {image_info.get('width', '?')}x"
                        f"{image_info.get('height', '?')} pixels"
                    ),
                    data={
                        "image_data": image_info.get("image_data", ""),
                        "format": "png",
                        "width": image_info.get("width"),
                        "height": image_info.get("height"),
                        "original_width": image_info.get("original_width"),
                        "original_height": image_info.get("original_height"),
                        "encoding": "base64",
                    },
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error=result.get("error", "Failed to get image bitmap"),
                ).model_dump()

        except GimpCommandError as e:
            return OperationResult.fail(operation="get_image_bitmap", error=str(e)).model_dump()

    @mcp.tool()
    async def get_image_metadata() -> ToolResult:
        """Get detailed metadata about the active image without bitmap data.

        Notes:
            Use this tool before any operation — understand canvas dimensions,
            layer structure, and file state. Much faster than get_image_bitmap.

        Notes:
            Returned data includes dimensions, color mode, layers, channels,
            paths, and file information.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        try:
            result = await bridge.async_get_image_metadata()
            if result.get("status") == "success":
                return OperationResult.ok(
                    operation="get_image_metadata",
                    message="Image metadata retrieved",
                    data=result.get("results", {}),
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_image_metadata",
                    error=result.get("error", "Failed to get metadata"),
                ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_image_metadata", error=str(e)).model_dump()

    @mcp.tool()
    async def get_context_state() -> ToolResult:
        """Get current GIMP context state (colors, brush, opacity, settings).

        Warnings:
            Important: Context can be changed by the user in GIMP's UI at any time.
            Check before operations that depend on specific settings.

        Notes:
            Returned data includes foreground and background colors, brush info,
            opacity, paint mode, feather state, and antialiasing state.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        try:
            result = await bridge.async_get_context_state()
            if result.get("status") == "success":
                return OperationResult.ok(
                    operation="get_context_state",
                    message="Context state retrieved",
                    data=result.get("results", {}),
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_context_state",
                    error=result.get("error", "Failed to get context"),
                ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_context_state", error=str(e)).model_dump()

    @mcp.tool()
    async def get_gimp_info() -> ToolResult:
        """Get GIMP environment info (version, paths, capabilities).

        Notes:
            Use this tool for troubleshooting, environment discovery, or
            understanding what features are available.

        Notes:
            Returned data includes the GIMP version, directories, open images,
            PDB availability, current context, system capabilities, and platform info.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        try:
            result = await bridge.async_get_gimp_info()
            if result.get("status") == "success":
                return OperationResult.ok(
                    operation="get_gimp_info",
                    message="GIMP info retrieved",
                    data=result.get("results", {}),
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_gimp_info",
                    error=result.get("error", "Failed to get GIMP info"),
                ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_gimp_info", error=str(e)).model_dump()
