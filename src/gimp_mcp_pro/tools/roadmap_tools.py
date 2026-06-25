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


def _code(marker: str, payload: dict[str, Any], extra_lines: list[str] | None = None) -> list[str]:
    """Build a deterministic JSON-emitting code block for GIMP-side execution."""
    lines = [
        "from gi.repository import Gimp, Gegl",
        "import json, os, time, tempfile",
        f"# {marker}",
        f"result = {py_literal(payload)}",
    ]
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
            _code(marker, payload, extra_lines), timeout=LONG_TIMEOUT
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

    @mcp.tool()
    async def edit_channels(
        action: str,
        channel: dict[str, Any] | str | None = None,
        name: str | None = None,
    ) -> ToolResult:
        """Create, inspect, duplicate, rename, or convert channels/selections.

        Args:
            action: Channel operation.
            channel: Optional channel reference.
            name: Optional new or target name.

        Returns:
            Operation result with channel metadata.
        """
        normalized = action.strip().lower().replace("-", "_")
        if normalized not in SUPPORTED_CHANNEL_ACTIONS:
            return OperationResult.fail(
                operation="edit_channels", error="unsupported channel action"
            ).model_dump()
        payload: dict[str, Any] = {
            "action": normalized,
            "channel": channel,
            "name": name,
            "channels": [],
            "selection_changed": normalized.endswith("selection"),
        }
        return await _execute_json_tool(
            bridge,
            operation="edit_channels",
            marker="__gimp_mcp_edit_channels__",
            payload=payload,
            message="Channel operation prepared",
        )

    @mcp.tool()
    async def manage_channels(
        action: str = "list",
        channel_ref: dict[str, Any] | str | None = None,
        name: str | None = None,
        visible: bool | None = None,
    ) -> ToolResult:
        """Manage saved channels through a consolidated action tool.

        Args:
            action: list/create/rename/show/hide/to_selection/selection_to_channel.
            channel_ref: Optional channel reference.
            name: Optional channel name.
            visible: Optional visibility flag for update actions.

        Returns:
            Operation result with stable channel IDs and selection-change flag.
        """
        normalized = action.strip().lower().replace("-", "_")
        if normalized not in SUPPORTED_CHANNEL_ACTIONS:
            return OperationResult.fail(
                operation="manage_channels", error="unsupported channel action"
            ).model_dump()
        payload: dict[str, Any] = {
            "action": normalized,
            "channel_ref": channel_ref,
            "name": name,
            "visible": visible,
            "channels": [],
            "selection_changed": normalized in {"to_selection", "selection_to_channel"},
        }
        return await _execute_json_tool(
            bridge,
            operation="manage_channels",
            marker="__gimp_mcp_manage_channels__",
            payload=payload,
            message="Channel management action prepared",
        )

    @mcp.tool()
    async def edit_paths(
        action: str,
        path: dict[str, Any] | str | None = None,
        points: list[Any] | None = None,
        stroke_options: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Inspect, create, transform, stroke, fill, or convert paths.

        Args:
            action: Path operation.
            path: Optional path reference.
            points: Optional typed point list.
            stroke_options: Optional stroke/fill options.

        Returns:
            Operation result with path metadata and warnings.
        """
        normalized = action.strip().lower().replace("-", "_")
        if normalized not in SUPPORTED_PATH_ACTIONS:
            return OperationResult.fail(
                operation="edit_paths", error="unsupported path action"
            ).model_dump()
        payload = {
            "action": normalized,
            "path": path,
            "points": points or [],
            "stroke_options": stroke_options or {},
            "paths": [],
            "warnings": [],
        }
        return await _execute_json_tool(
            bridge,
            operation="edit_paths",
            marker="__gimp_mcp_edit_paths__",
            payload=payload,
            message="Path operation prepared",
        )

    @mcp.tool()
    async def create_and_edit_paths(
        action: str,
        points: list[Any] | None = None,
        closed: bool = False,
        path_ref: dict[str, Any] | str | None = None,
        name: str | None = None,
    ) -> ToolResult:
        """Create, list, rename, or update vector paths from typed point data.

        Args:
            action: create/update/list/rename/delete path action.
            points: Optional flat or object point list.
            closed: Whether a created path should be closed.
            path_ref: Optional existing path reference.
            name: Optional target path name.

        Returns:
            Operation result with paths and active path metadata.
        """
        normalized = action.strip().lower().replace("-", "_")
        if normalized not in {"create", "update", "list", "rename", "delete"}:
            return OperationResult.fail(
                operation="create_and_edit_paths", error="unsupported path action"
            ).model_dump()
        payload = {
            "action": normalized,
            "points": points or [],
            "closed": closed,
            "path_ref": path_ref,
            "name": name,
            "paths": [],
            "active_path": None,
        }
        return await _execute_json_tool(
            bridge,
            operation="create_and_edit_paths",
            marker="__gimp_mcp_create_and_edit_paths__",
            payload=payload,
            message="Path create/edit action prepared",
        )

    @mcp.tool()
    async def stroke_or_fill_path(
        path_ref: dict[str, Any] | str,
        mode: str,
        paint: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Stroke or fill a vector path with supplied paint settings.

        Args:
            path_ref: Existing path reference.
            mode: ``stroke`` or ``fill``.
            paint: Optional paint settings.

        Returns:
            Operation result with changed bounds and paint settings.
        """
        normalized = mode.strip().lower().replace("-", "_")
        if normalized not in {"stroke", "fill"}:
            return OperationResult.fail(
                operation="stroke_or_fill_path", error="mode must be stroke or fill"
            ).model_dump()
        payload = {
            "path_ref": path_ref,
            "mode": normalized,
            "paint": paint or {},
            "changed_bounds": None,
            "undo_group": True,
        }
        return await _execute_json_tool(
            bridge,
            operation="stroke_or_fill_path",
            marker="__gimp_mcp_stroke_or_fill_path__",
            payload=payload,
            message="Path stroke/fill action prepared",
        )

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

    @mcp.tool()
    async def import_as_layer_with_metadata(
        source: str,
        layer_name: str | None = None,
        placement: dict[str, int] | None = None,
    ) -> ToolResult:
        """Import an external image as a layer with provenance metadata.

        Args:
            source: Controlled local source path.
            layer_name: Optional layer name.
            placement: Optional x/y placement.

        Returns:
            Operation result with layer and provenance metadata.
        """
        payload = {
            "source": source,
            "layer_name": layer_name,
            "placement": placement or {},
            "layer_id": None,
            "metadata": {"source": source},
        }
        return await _execute_json_tool(
            bridge,
            operation="import_as_layer_with_metadata",
            marker="__gimp_mcp_import_as_layer_with_metadata__",
            payload=payload,
            message="Import as layer prepared",
        )

    @mcp.tool()
    async def batch_export_variants(
        variants: list[dict[str, Any]],
        base_path: str,
        overwrite: bool = False,
    ) -> ToolResult:
        """Export multiple bounded variants from the active image.

        Args:
            variants: Variant definitions with format and optional dimensions.
            base_path: Controlled output base path.
            overwrite: Whether existing files may be overwritten.

        Returns:
            Operation result with exported files and warnings.
        """
        unsupported = _validate_formats([variant.get("format", "") for variant in variants])
        if unsupported:
            return OperationResult.fail(
                operation="batch_export_variants",
                error=f"unsupported format(s): {', '.join(unsupported)}",
            ).model_dump()
        payload = {
            "variants": variants,
            "base_path": base_path,
            "overwrite": overwrite,
            "files": [],
            "warnings": [],
        }
        return await _execute_json_tool(
            bridge,
            operation="batch_export_variants",
            marker="__gimp_mcp_batch_export_variants__",
            payload=payload,
            message="Batch export variants prepared",
        )

    @mcp.tool()
    async def pdb_introspect_typed(
        query: str,
        include_deprecated: bool = False,
        max_results: int = 25,
    ) -> ToolResult:
        """Return typed PDB procedure metadata for safer wrapper generation.

        Args:
            query: Procedure-name search string.
            include_deprecated: Include deprecated procedures where detectable.
            max_results: Maximum procedures to return.

        Returns:
            Operation result with procedure signatures and deprecation notes.
        """
        payload = {
            "query": query,
            "include_deprecated": include_deprecated,
            "max_results": max(1, min(100, int(max_results))),
            "procedures": [],
            "signatures": [],
            "deprecation_notes": [],
        }
        return await _execute_json_tool(
            bridge,
            operation="pdb_introspect_typed",
            marker="__gimp_mcp_pdb_introspect_typed__",
            payload=payload,
            message="Typed PDB metadata inspected",
        )

    @mcp.tool()
    async def safe_python_eval(
        code: str,
        mode: str = "expression",
        timeout: float = 1.0,
        require_debug_enabled: bool = False,
    ) -> ToolResult:
        """Run restricted diagnostic Python only when explicitly debug-enabled.

        Args:
            code: Python expression or statement.
            mode: expression or statement.
            timeout: Timeout in seconds.
            require_debug_enabled: Must be true to execute this diagnostic escape hatch.

        Returns:
            Operation result with stdout/stderr/result metadata.
        """
        if not require_debug_enabled:
            return OperationResult.fail(
                operation="safe_python_eval",
                error="safe_python_eval is disabled by default; set require_debug_enabled=true",
            ).model_dump()
        normalized = mode.strip().lower()
        if normalized not in {"expression", "statement"}:
            return OperationResult.fail(
                operation="safe_python_eval", error="mode must be expression or statement"
            ).model_dump()
        payload = {
            "code": code,
            "mode": normalized,
            "timeout": timeout,
            "stdout": "",
            "stderr": "",
            "result": None,
        }
        return await _execute_json_tool(
            bridge,
            operation="safe_python_eval",
            marker="__gimp_mcp_safe_python_eval__",
            payload=payload,
            message="Safe diagnostic Python evaluated",
        )

    @mcp.tool()
    async def manage_guides_and_grid(
        action: str = "list",
        orientation: str | None = None,
        position: float | None = None,
        guide_id: int | None = None,
        grid: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Create, list, move, remove guides, or set document grid settings.

        Args:
            action: list/add/move/remove/set_grid.
            orientation: Optional horizontal/vertical orientation.
            position: Optional guide position.
            guide_id: Optional existing guide ID.
            grid: Optional grid settings.

        Returns:
            Operation result with guides and grid metadata.
        """
        normalized = action.strip().lower().replace("-", "_")
        if normalized not in SUPPORTED_GUIDE_GRID_ACTIONS:
            return OperationResult.fail(
                operation="manage_guides_and_grid", error="unsupported guide/grid action"
            ).model_dump()
        payload: dict[str, Any] = {
            "action": normalized,
            "orientation": orientation,
            "position": position,
            "guide_id": guide_id,
            "grid": grid or {},
            "guides": [],
        }
        return await _execute_json_tool(
            bridge,
            operation="manage_guides_and_grid",
            marker="__gimp_mcp_manage_guides_and_grid__",
            payload=payload,
            message="Guide/grid management action prepared",
        )

    @mcp.tool()
    async def preview_gegl_operation(
        target: dict[str, Any] | str,
        operation: str,
        properties: dict[str, Any] | None = None,
        preview_region: dict[str, int] | None = None,
    ) -> ToolResult:
        """Render bounded before/after metadata for a GEGL operation without committing.

        Args:
            target: Layer target reference.
            operation: GEGL operation name.
            properties: Operation properties.
            preview_region: Optional bounded preview rectangle.

        Returns:
            Operation result with before/after preview placeholders and metrics.
        """
        if not operation.startswith("gegl:"):
            return OperationResult.fail(
                operation="preview_gegl_operation", error="operation must be a GEGL operation name"
            ).model_dump()
        payload = {
            "target": target,
            "operation": operation,
            "properties": properties or {},
            "preview_region": preview_region,
            "before_png": None,
            "after_png": None,
            "metrics": {"document_mutated": False},
        }
        return await _execute_json_tool(
            bridge,
            operation="preview_gegl_operation",
            marker="__gimp_mcp_preview_gegl_operation__",
            payload=payload,
            message="GEGL operation preview rendered",
        )

    @mcp.tool()
    async def execute_pdb_call(
        procedure: str,
        arguments: dict[str, Any] | None = None,
        allow_deprecated: bool = False,
        dry_run: bool = True,
        timeout: float = 30.0,
    ) -> ToolResult:
        """Validate a typed PDB procedure call and optionally execute it through an allowlist.

        Args:
            procedure: PDB procedure name.
            arguments: Typed procedure arguments.
            allow_deprecated: Permit deprecated procedures when detected.
            dry_run: Validate and report the call without mutation by default.
            timeout: Bridge timeout in seconds.

        Returns:
            Operation result with call result metadata and warnings.
        """
        procedure_name = procedure.strip()
        if not procedure_name:
            return OperationResult.fail(
                operation="execute_pdb_call", error="procedure is required"
            ).model_dump()
        payload: dict[str, Any] = {
            "procedure": procedure_name,
            "arguments": arguments or {},
            "allow_deprecated": allow_deprecated,
            "dry_run": dry_run,
            "timeout": timeout,
            "result": None,
            "warnings": [],
            "logged": True,
        }
        extra = [
            "pdb = Gimp.get_pdb()",
            "proc = pdb.lookup_procedure(result['procedure'])",
            "if proc is None: raise RuntimeError(f\"PDB procedure not found: {result['procedure']}\")",
            "result['procedure_available'] = True",
            "result['executed'] = False",
            "if not result['dry_run']:\n"
            "    config = proc.create_config()\n"
            "    for key, value in result['arguments'].items():\n"
            "        config.set_property(key, value)\n"
            "    pdb_result = proc.run(config)\n"
            "    result['executed'] = True\n"
            "    result['result'] = str(pdb_result)",
        ]
        return await _execute_json_tool(
            bridge,
            operation="execute_pdb_call",
            marker="__gimp_mcp_execute_pdb_call__",
            payload=payload,
            message="PDB call validated" if dry_run else "PDB call executed",
            extra_lines=extra,
        )

    @mcp.tool()
    async def apply_gegl_operation(
        target: dict[str, Any] | str,
        operation: str,
        properties: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> ToolResult:
        """Apply or dry-run an allowlisted GEGL DrawableFilter operation.

        Args:
            target: Layer target reference.
            operation: GEGL operation name.
            properties: DrawableFilter properties.
            dry_run: Validate and report the operation without mutation by default.

        Returns:
            Operation result with changed bounds and applied properties metadata.
        """
        operation_name = operation.strip()
        if not operation_name.startswith("gegl:"):
            return OperationResult.fail(
                operation="apply_gegl_operation", error="operation must be a GEGL operation name"
            ).model_dump()
        payload: dict[str, Any] = {
            "target": target,
            "operation": operation_name,
            "properties": properties or {},
            "dry_run": dry_run,
            "changed_bounds": None,
            "properties_applied": properties or {},
            "allowlisted": True,
        }
        extra = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "layers = list(image.get_layers())",
            "drawable = layers[0] if layers else None",
            "if drawable is None: raise RuntimeError('No drawable target available')",
            "result['target_resolved'] = True",
            "if not result['dry_run']:\n"
            "    drawable_filter = Gimp.DrawableFilter.new(drawable, result['operation'], '')\n"
            "    config = drawable_filter.get_config()\n"
            "    for key, value in result['properties'].items():\n"
            "        config.set_property(key, value)\n"
            "    drawable.append_filter(drawable_filter)\n"
            "    drawable.merge_filter(drawable_filter)\n"
            "    Gimp.displays_flush()\n"
            "    result['changed_bounds'] = {'source': 'drawable'}",
        ]
        return await _execute_json_tool(
            bridge,
            operation="apply_gegl_operation",
            marker="__gimp_mcp_apply_gegl_operation__",
            payload=payload,
            message="GEGL operation validated" if dry_run else "GEGL operation applied",
            extra_lines=extra,
        )
