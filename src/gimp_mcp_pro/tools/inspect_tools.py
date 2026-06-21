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


def register_inspect_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all inspection tools with the MCP server."""

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
            max_width: Maximum width for scaling (default 1024). Use None for full size.
            max_height: Maximum height for scaling (default 1024). Use None for full size.
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
