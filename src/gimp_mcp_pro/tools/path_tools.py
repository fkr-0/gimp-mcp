"""Vector path tools for GIMP MCP Pro."""

from __future__ import annotations

import logging
from typing import Any

from gimp_mcp_pro.models.common import Color, OperationResult, SelectionOp, py_literal
from gimp_mcp_pro.tools.roadmap_tools import SUPPORTED_PATH_ACTIONS, _execute_json_tool
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError
from gimp_mcp_pro.utils.gimp_constants import SELECTION_OP_MAP

logger = logging.getLogger("gimp_mcp_pro.tools.path")


def _op_expr(op: str) -> str:
    """Convert selection op string to GIMP expression."""
    return SELECTION_OP_MAP.get(SelectionOp(op), "Gimp.ChannelOps.REPLACE")


def _path_lookup_code(path_name: str | None, path_index: int | None) -> list[str]:
    """Generate Python code to look up a vector path by name/index/selection."""
    code = [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
    ]
    if path_name is not None:
        code += [
            f"target = image.get_path_by_name({py_literal(path_name)})",
            f"if target is None: raise RuntimeError({py_literal(f'Path {path_name!r} not found')})",
        ]
    elif path_index is not None:
        code += [
            "paths = image.get_paths()",
            f"if {path_index} >= len(paths): raise RuntimeError('Path index {path_index} out of range')",
            f"target = paths[{path_index}]",
        ]
    else:
        code += [
            "paths = image.get_selected_paths()",
            "if not paths: paths = image.get_paths()",
            "if not paths: raise RuntimeError('No path available')",
            "target = paths[0]",
        ]
    return code


def _drawable_lookup_code(layer_name: str | None, layer_index: int | None) -> list[str]:
    """Generate Python code to resolve the drawable used to stroke a path."""
    if layer_name is not None:
        return [
            f"drawable = image.get_layer_by_name({py_literal(layer_name)})",
            f"if drawable is None: raise RuntimeError({py_literal(f'Layer {layer_name!r} not found')})",
        ]
    if layer_index is not None:
        return [
            "layers = image.get_layers()",
            f"if {layer_index} >= len(layers): raise RuntimeError('Layer index {layer_index} out of range')",
            f"drawable = layers[{layer_index}]",
        ]
    return [
        "selected_layers = image.get_selected_layers()",
        "if not selected_layers: raise RuntimeError('No active layer')",
        "drawable = selected_layers[0]",
    ]


def register_path_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register vector path tools with the MCP server."""

    @mcp.tool()
    async def create_path(
        points: list[float],
        name: str = "Path",
        closed: bool = False,
        position: int = 0,
    ) -> ToolResult:
        """Create a vector path from a flat point list.

        Args:
            points: Flat list [x1, y1, x2, y2, ...]. Minimum 3 vertices.
            name: New path name.
            closed: Whether to close the path stroke.
            position: Path stack position.

        Returns:
            Operation result with created path metadata.
        """
        if len(points) < 6 or len(points) % 2 != 0:
            return OperationResult.fail(
                operation="create_path",
                error="Need at least 3 points (6 values) with even count",
            ).model_dump()

        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            f"path = Gimp.Path.new(image, {py_literal(name)})",
            f"stroke_id = path.stroke_new_from_points(Gimp.PathStrokeType.BEZIER, {points}, {closed})",
            "if stroke_id < 0: raise RuntimeError('Could not create path stroke')",
            f"if not image.insert_path(path, None, {position}): raise RuntimeError('Could not insert path')",
            "image.set_selected_paths([path])",
            "Gimp.displays_flush()",
            "print(path.get_name())",
        ]
        try:
            result = await bridge.async_execute_python(code)
            path_name = name
            for out in result.get("results", []):
                if out and str(out).strip():
                    path_name = str(out).strip()
            return OperationResult.ok(
                operation="create_path",
                message=f"Created path '{path_name}' with {len(points) // 2} vertices",
                data={"name": path_name, "vertices": len(points) // 2, "closed": closed},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="create_path", error=str(e)).model_dump()

    @mcp.tool()
    async def list_paths() -> ToolResult:
        """List vector paths in the active image.

        Returns:
            Operation result dictionary with path names, indexes, stroke counts, and total count.
        """
        code = [
            "import json",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "result = []",
            "for i, path in enumerate(image.get_paths()):\n"
            "    strokes = path.get_strokes()\n"
            "    result.append({'index': i, 'name': path.get_name(), 'stroke_count': len(strokes)})",
            "print(json.dumps(result))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            paths_data = []
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        paths_data = _json.loads(str(out).strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="list_paths",
                message=f"Found {len(paths_data)} path(s)",
                data={"paths": paths_data, "count": len(paths_data)},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="list_paths", error=str(e)).model_dump()

    @mcp.tool()
    async def path_to_selection(
        path_name: str | None = None,
        path_index: int | None = None,
        operation: str = "replace",
    ) -> ToolResult:
        """Convert a vector path to the current selection.

        Args:
            path_name: Target path by name.
            path_index: Target path by index. Uses selected or first path if neither specified.
            operation: "replace", "add", "subtract", or "intersect".

        Returns:
            Operation result dictionary with selection conversion metadata.
        """
        try:
            op_expr = _op_expr(operation)
        except ValueError:
            return OperationResult.fail(
                operation="path_to_selection",
                error="operation must be one of: replace, add, subtract, intersect",
            ).model_dump()
        code = _path_lookup_code(path_name, path_index) + [
            f"image.select_item({op_expr}, target)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="path_to_selection",
                message=f"Converted path to selection using {operation}",
                data={"operation": operation},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="path_to_selection", error=str(e)).model_dump()

    @mcp.tool()
    async def stroke_path(
        path_name: str | None = None,
        path_index: int | None = None,
        color: str | None = None,
        brush_size: float | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Stroke a vector path onto a layer using the current or supplied context.

        Args:
            path_name: Target path by name.
            path_index: Target path by index. Uses selected or first path if neither specified.
            color: Optional foreground color to use before stroking.
            brush_size: Optional line width in pixels.
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with path stroke metadata.
        """
        if brush_size is not None and brush_size <= 0:
            return OperationResult.fail(
                operation="stroke_path", error="brush_size must be greater than 0"
            ).model_dump()
        color_expr = None
        if color is not None:
            try:
                color_expr = Color(value=color).to_gegl_code()
            except ValueError as exc:
                return OperationResult.fail(operation="stroke_path", error=str(exc)).model_dump()

        code = ["from gi.repository import Gimp, Gegl"] + _path_lookup_code(path_name, path_index)
        code += _drawable_lookup_code(layer_name, layer_index)
        if color_expr is not None:
            code.append(f"Gimp.context_set_foreground({color_expr})")
        if brush_size is not None:
            code.append(f"Gimp.context_set_line_width({brush_size})")
        code += [
            "drawable.edit_stroke_item(target)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="stroke_path",
                message="Path stroked",
                data={"path_name": path_name, "path_index": path_index},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="stroke_path", error=str(e)).model_dump()

    @mcp.tool()
    async def remove_path(
        path_name: str | None = None,
        path_index: int | None = None,
    ) -> ToolResult:
        """Remove a vector path from the active image.

        Args:
            path_name: Target path by name.
            path_index: Target path by index. Uses selected or first path if neither specified.

        Returns:
            Operation result dictionary with removed path metadata.
        """
        code = _path_lookup_code(path_name, path_index) + [
            "removed_name = target.get_name()",
            "image.remove_path(target)",
            "Gimp.displays_flush()",
            "print(removed_name)",
        ]
        try:
            result = await bridge.async_execute_python(code)
            removed_name = path_name or ""
            for out in result.get("results", []):
                if out and str(out).strip():
                    removed_name = str(out).strip()
            return OperationResult.ok(
                operation="remove_path",
                message=f"Removed path '{removed_name}'",
                data={"name": removed_name or None},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="remove_path", error=str(e)).model_dump()

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
