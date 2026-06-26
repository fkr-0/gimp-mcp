"""Context and document-state inspection tool registrations."""

from __future__ import annotations

import json
import logging
from typing import Any

from gimp_mcp_pro import __version__
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.inspect")

VALID_CONTEXT_DETAIL_LEVELS = {"low", "medium", "high"}


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


def _context_explanation_code(detail_level: str, include_recommendations: bool) -> list[str]:
    """Return generated Python code that summarizes current canvas context."""
    return [
        "import json",
        "# __gimp_mcp_explain_current_context__",
        f"detail_level = {detail_level!r}",
        f"include_recommendations = {include_recommendations!r}",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def layer_fact(layer, index):\n"
        "    return {\n"
        "        'id': safe_call(lambda: int(layer.get_id()), None),\n"
        "        'index': index,\n"
        "        'name': safe_call(lambda: layer.get_name(), ''),\n"
        "        'visible': bool(safe_call(lambda: layer.get_visible(), True)),\n"
        "        'width': safe_call(lambda: layer.get_width(), None),\n"
        "        'height': safe_call(lambda: layer.get_height(), None),\n"
        "        'opacity': safe_call(lambda: layer.get_opacity(), None),\n"
        "    }",
        "images = Gimp.get_images()",
        "warnings = []",
        "recommendations = []",
        "if not images:\n"
        "    facts = {'has_image': False, 'layers': [], 'selection': {'non_empty': False}}\n"
        "    warnings.append({'code': 'no_open_image', 'message': 'No image is open'})\n"
        "    summary = 'No image is currently open.'\n"
        "else:\n"
        "    image = images[0]\n"
        "    layers = list(safe_call(lambda: image.get_layers(), []) or [])\n"
        "    selected = list(safe_call(lambda: image.get_selected_layers(), []) or [])\n"
        "    selection_bounds = safe_call(lambda: Gimp.Selection.bounds(image), None)\n"
        "    selection = {'non_empty': bool(getattr(selection_bounds, 'non_empty', False)) if selection_bounds is not None else False}\n"
        "    layer_facts = [layer_fact(layer, index) for index, layer in enumerate(layers)]\n"
        "    hidden = [layer for layer in layer_facts if not layer.get('visible', True)]\n"
        "    if hidden:\n"
        "        warnings.append({'code': 'hidden_layers', 'count': len(hidden)})\n"
        "    if include_recommendations and selection.get('non_empty'):\n"
        "        recommendations.append('There is an active selection; edits may be selection-limited.')\n"
        "    if include_recommendations and hidden:\n"
        "        recommendations.append('Review hidden layers before export or flattening.')\n"
        "    facts = {\n"
        "        'has_image': True,\n"
        "        'image': {'width': safe_call(lambda: image.get_width(), None), 'height': safe_call(lambda: image.get_height(), None), 'base_type': str(safe_call(lambda: image.get_base_type(), 'unknown'))},\n"
        "        'layer_count': len(layers),\n"
        "        'selected_layer_count': len(selected),\n"
        "        'layers': layer_facts if detail_level == 'high' else layer_facts[:5],\n"
        "        'selection': selection,\n"
        "    }\n"
        "    summary = f\"Image {facts['image']['width']}x{facts['image']['height']} with {len(layers)} layer(s); selection active={selection.get('non_empty')}\"",
        "result = {'summary': summary, 'facts': facts, 'warnings': warnings, 'recommendations': recommendations if include_recommendations else [], 'detail_level': detail_level}",
        "print(json.dumps(result))",
    ]


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


def register_context_inspect_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register this focused inspect tool subset."""

    @mcp.tool()
    async def explain_current_context(
        detail_level: str = "medium",
        include_recommendations: bool = False,
    ) -> ToolResult:
        """Explain the current canvas state as an LLM-oriented context packet.

        Args:
            detail_level: low, medium, or high detail for machine-readable facts.
            include_recommendations: Include a separate recommendations list.

        Returns:
            Operation result with summary, facts, warnings, and optional recommendations.

        Contract:
            Facts remain machine-readable. Recommendations are explicitly separated
            from raw inspection facts and this tool is read-only.
        """
        if detail_level not in VALID_CONTEXT_DETAIL_LEVELS:
            return OperationResult.fail(
                operation="explain_current_context",
                error="detail_level must be one of: low, medium, high",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _context_explanation_code(detail_level, include_recommendations)
            )
            data = _json_payload(result)
            data.setdefault("summary", "")
            data.setdefault("facts", {})
            data.setdefault("warnings", [])
            data.setdefault("recommendations", [])
            return OperationResult.ok(
                operation="explain_current_context",
                message="Current context explained",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="explain_current_context", error=str(e)
            ).model_dump()

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
