"""Selection tools for GIMP MCP Pro."""

from __future__ import annotations

import logging

from gimp_mcp_pro.models.common import Color, OperationResult, SelectionOp, py_literal
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError
from gimp_mcp_pro.utils.gimp_constants import SELECTION_OP_MAP

logger = logging.getLogger("gimp_mcp_pro.tools.selection")


def _op_expr(op: str) -> str:
    """Convert selection op string to GIMP expression."""
    return SELECTION_OP_MAP.get(SelectionOp(op), "Gimp.ChannelOps.REPLACE")


def register_selection_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all selection tools with the MCP server."""

    @mcp.tool()
    async def select_rectangle(
        x: float,
        y: float,
        width: float,
        height: float,
        operation: str = "replace",
        feather_radius: float = 0.0,
    ) -> ToolResult:
        """Create a rectangular selection.

        Notes:
            Use this tool before filling a rectangular area, or to constrain
            operations to a specific region.

        Args:
            x, y: Top-left corner
            width, height: Selection dimensions
            operation: "replace", "add", "subtract", or "intersect"
            feather_radius: Edge feather radius (0 = sharp edges, recommended default)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            f"Gimp.Image.select_rectangle(image, {_op_expr(operation)}, {x}, {y}, {width}, {height})",
        ]
        if feather_radius > 0:
            code.append(f"Gimp.Selection.feather(image, {feather_radius})")
        code.append("Gimp.displays_flush()")

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="select_rectangle",
                message=f"Selected rectangle ({x},{y}) {width}x{height}",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_rectangle", error=str(e)).model_dump()

    @mcp.tool()
    async def select_ellipse(
        x: float,
        y: float,
        width: float,
        height: float,
        operation: str = "replace",
        feather_radius: float = 0.0,
    ) -> ToolResult:
        """Create an elliptical selection.

        For a circular selection, set width == height.

        Args:
            x, y: Bounding box top-left corner
            width, height: Bounding box dimensions
            operation: "replace", "add", "subtract", or "intersect"
            feather_radius: Edge feather radius (0 = sharp, recommended)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            f"Gimp.Image.select_ellipse(image, {_op_expr(operation)}, {x}, {y}, {width}, {height})",
        ]
        if feather_radius > 0:
            code.append(f"Gimp.Selection.feather(image, {feather_radius})")
        code.append("Gimp.displays_flush()")

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="select_ellipse",
                message=f"Selected ellipse at ({x},{y}) {width}x{height}",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_ellipse", error=str(e)).model_dump()

    @mcp.tool()
    async def select_polygon(
        points: list[float],
        operation: str = "replace",
        feather_radius: float = 0.0,
    ) -> ToolResult:
        """Create a polygon (freeform) selection.

        Notes:
            Best practice: Use polygon selection + fill_selection for solid shapes.
            This is the recommended way to draw filled shapes in GIMP.

        Args:
            points: Flat list [x1,y1, x2,y2, x3,y3, ...]. Min 3 vertices (6 values).
            operation: "replace", "add", "subtract", or "intersect"
            feather_radius: Edge feather radius (0 = sharp, recommended)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if len(points) < 6 or len(points) % 2 != 0:
            return OperationResult.fail(
                operation="select_polygon",
                error="Need at least 3 points (6 values) with even count",
            ).model_dump()

        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            f"Gimp.Image.select_polygon(image, {_op_expr(operation)}, {points})",
        ]
        if feather_radius > 0:
            code.append(f"Gimp.Selection.feather(image, {feather_radius})")
        code.append("Gimp.displays_flush()")

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="select_polygon",
                message=f"Selected polygon with {len(points) // 2} vertices",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_polygon", error=str(e)).model_dump()

    @mcp.tool()
    async def select_all() -> ToolResult:
        """Select the entire image.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "Gimp.Selection.all(images[0])",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(operation="select_all", message="Selected all").model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_all", error=str(e)).model_dump()

    @mcp.tool()
    async def select_none() -> ToolResult:
        """Clear all selections.

        Warnings:
            Important: Always call this after fill/stroke operations on selections
            to avoid unexpected behavior on subsequent operations.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "Gimp.Selection.none(images[0])",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="select_none", message="Selection cleared"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_none", error=str(e)).model_dump()

    @mcp.tool()
    async def select_invert() -> ToolResult:
        """Invert the current selection (select everything NOT currently selected).

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "Gimp.Selection.invert(images[0])",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="select_invert", message="Selection inverted"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_invert", error=str(e)).model_dump()

    @mcp.tool()
    async def select_by_color(
        x: float,
        y: float,
        threshold: float = 15.0,
        operation: str = "replace",
        sample_merged: bool = False,
    ) -> ToolResult:
        """Select all pixels similar in color to the sampled point.

        Notes:
            Useful for selecting uniform backgrounds, solid-color regions, or
            isolating objects by their surrounding color.

        Args:
            x: Sample point X coordinate (pixel to sample color from)
            y: Sample point Y coordinate
            threshold: Color similarity threshold 0-255 (lower = more exact match,
                higher = more tolerance). Default 15.
            operation: "replace", "add", "subtract", or "intersect"
            sample_merged: If True, sample color from all visible layers merged.
                If False (default), sample from active layer only.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "import json",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "sel = image.get_selected_layers()",
            "if not sel: raise RuntimeError('No active layer')",
            "drawable = sel[0]",
            f"Gimp.context_set_sample_threshold({threshold / 255.0})",
            f"Gimp.context_set_sample_merged({sample_merged})",
            f"Gimp.Image.select_contiguous_color(image, {_op_expr(operation)}, drawable, {x}, {y})",
            "Gimp.displays_flush()",
            "bounds = Gimp.Selection.bounds(image)",
            "if len(bounds) == 6:\n"
            "    _, non_empty, x1, y1, x2, y2 = bounds\n"
            "else:\n"
            "    non_empty, x1, y1, x2, y2 = bounds",
            "print(json.dumps({'has_selection': bool(non_empty), "
            "'bounds': {'x': x1, 'y': y1, 'width': x2 - x1, 'height': y2 - y1}}))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            sel_info = {}
            for out in result.get("results", []):
                if out and out.strip():
                    try:
                        sel_info = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="select_by_color",
                message=f"Selected by color at ({x},{y}) threshold={threshold}",
                data=sel_info,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_by_color", error=str(e)).model_dump()

    @mcp.tool()
    async def feather_selection(radius: float) -> ToolResult:
        """Feather the current selection by a radius in pixels.

        Args:
            radius: Feather radius. Use 0 for no feather; positive values soften edges.

        Returns:
            Operation result dictionary with status, message, and radius metadata.
        """
        if radius < 0:
            return OperationResult.fail(
                operation="feather_selection", error="radius must be non-negative"
            ).model_dump()
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            f"Gimp.Selection.feather(images[0], {radius})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="feather_selection",
                message=f"Selection feathered by {radius}px",
                data={"radius": radius},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="feather_selection", error=str(e)).model_dump()

    @mcp.tool()
    async def border_selection(radius: int) -> ToolResult:
        """Replace the current selection with its border.

        Args:
            radius: Border radius in pixels. Must be greater than 0.

        Returns:
            Operation result dictionary with status, message, and radius metadata.
        """
        if radius <= 0:
            return OperationResult.fail(
                operation="border_selection", error="radius must be greater than 0"
            ).model_dump()
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            f"Gimp.Selection.border(images[0], {radius})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="border_selection",
                message=f"Selection border created with radius {radius}px",
                data={"radius": radius},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="border_selection", error=str(e)).model_dump()

    @mcp.tool()
    async def stroke_selection(
        color: str | None = None,
        brush_size: float | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Stroke the current selection onto a layer.

        Args:
            color: Optional foreground color to use for the stroke.
            brush_size: Optional stroke line width in pixels.
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and stroke metadata.
        """
        if brush_size is not None and brush_size <= 0:
            return OperationResult.fail(
                operation="stroke_selection", error="brush_size must be greater than 0"
            ).model_dump()
        color_expr = None
        if color is not None:
            try:
                color_expr = Color(value=color).to_gegl_code()
            except ValueError as exc:
                return OperationResult.fail(
                    operation="stroke_selection", error=str(exc)
                ).model_dump()

        code = [
            "from gi.repository import Gegl",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
        ]
        if layer_name is not None:
            from gimp_mcp_pro.models.common import py_literal as _py_literal

            code += [
                f"drawable = image.get_layer_by_name({_py_literal(layer_name)})",
                f"if drawable is None: raise RuntimeError({_py_literal(f'Layer {layer_name!r} not found')})",
            ]
        elif layer_index is not None:
            code += [
                "layers = image.get_layers()",
                f"if {layer_index} >= len(layers): raise RuntimeError('Layer index {layer_index} out of range')",
                f"drawable = layers[{layer_index}]",
            ]
        else:
            code += [
                "sel = image.get_selected_layers()",
                "if not sel: raise RuntimeError('No active layer')",
                "drawable = sel[0]",
            ]
        stroke_color_expr = color_expr or "None"
        line_width_expr = repr(brush_size) if brush_size is not None else "None"
        lifecycle_lines = [
            "# __gimp_mcp_selection_stroke_lifecycle__",
            "previous_foreground = Gimp.context_get_foreground()",
            "previous_line_width = Gimp.context_get_line_width()",
            "stroke_color = None",
            "try:",
            f"    stroke_color = {stroke_color_expr}",
            "    if stroke_color is not None:",
            f"        Gimp.context_set_foreground({stroke_color_expr})",
            f"    if {line_width_expr} is not None:",
            f"        Gimp.context_set_line_width({line_width_expr})",
            "    Gimp.Drawable.edit_stroke_selection(drawable)",
            "finally:",
            "    try:",
            "        Gimp.context_set_foreground(previous_foreground)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        Gimp.context_set_line_width(previous_line_width)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del stroke_color",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
        ]
        code = (
            ["import gc"]
            + code
            + [
                "\n".join(lifecycle_lines),
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="stroke_selection",
                message="Selection stroked",
                data={"color": color, "brush_size": brush_size},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="stroke_selection", error=str(e)).model_dump()

    @mcp.tool()
    async def bucket_fill(
        x: float,
        y: float,
        color: str | None = None,
        threshold: float = 15.0,
        sample_merged: bool = False,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Bucket-fill a contiguous region from a seed point.

        Args:
            x: Seed point X coordinate.
            y: Seed point Y coordinate.
            color: Optional foreground color to use before filling.
            threshold: Color similarity threshold 0-255.
            sample_merged: If True, sample from merged visible layers.
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and fill metadata.
        """
        if not 0 <= threshold <= 255:
            return OperationResult.fail(
                operation="bucket_fill", error="threshold must be between 0 and 255"
            ).model_dump()
        color_expr = None
        if color is not None:
            try:
                color_expr = Color(value=color).to_gegl_code()
            except ValueError as exc:
                return OperationResult.fail(operation="bucket_fill", error=str(exc)).model_dump()

        code = [
            "from gi.repository import Gegl",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
        ]
        if layer_name is not None:
            code += [
                f"drawable = image.get_layer_by_name({py_literal(layer_name)})",
                f"if drawable is None: raise RuntimeError({py_literal(f'Layer {layer_name!r} not found')})",
            ]
        elif layer_index is not None:
            code += [
                "layers = image.get_layers()",
                f"if {layer_index} >= len(layers): raise RuntimeError('Layer index {layer_index} out of range')",
                f"drawable = layers[{layer_index}]",
            ]
        else:
            code += [
                "sel = image.get_selected_layers()",
                "if not sel: raise RuntimeError('No active layer')",
                "drawable = sel[0]",
            ]
        fill_color_expr = color_expr or "None"
        threshold_expr = repr(threshold / 255.0)
        sample_merged_expr = repr(sample_merged)
        lifecycle_lines = [
            "# __gimp_mcp_selection_bucket_lifecycle__",
            "previous_foreground = Gimp.context_get_foreground()",
            "previous_sample_threshold = Gimp.context_get_sample_threshold()",
            "previous_sample_merged = Gimp.context_get_sample_merged()",
            "fill_color = None",
            "try:",
            f"    fill_color = {fill_color_expr}",
            "    if fill_color is not None:",
            f"        Gimp.context_set_foreground({fill_color_expr})",
            f"    Gimp.context_set_sample_threshold({threshold_expr})",
            f"    Gimp.context_set_sample_merged({sample_merged_expr})",
            "    drawable = locals().get('drawable', locals().get('target'))",
            f"    Gimp.Drawable.edit_bucket_fill(drawable, Gimp.FillType.FOREGROUND, {x}, {y})",
            "finally:",
            "    try:",
            "        Gimp.context_set_foreground(previous_foreground)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        Gimp.context_set_sample_threshold(previous_sample_threshold)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        Gimp.context_set_sample_merged(previous_sample_merged)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del fill_color",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
        ]
        code = (
            ["import gc"]
            + code
            + [
                "\n".join(lifecycle_lines),
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="bucket_fill",
                message=f"Bucket-filled at ({x},{y})",
                data={
                    "x": x,
                    "y": y,
                    "color": color,
                    "threshold": threshold,
                    "sample_merged": sample_merged,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="bucket_fill", error=str(e)).model_dump()

    @mcp.tool()
    async def get_selection_info() -> ToolResult:
        """Get information about the current selection (bounds, whether it exists).

        Notes:
            Use this to check whether a selection is active and where it is
            before performing fill, stroke, or other selection-dependent operations.

        Returns:
            Selection info: has_selection, bounds (x, y, width, height),
            and whether it covers the full image.
        """
        code = [
            "import json",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "bounds = Gimp.Selection.bounds(image)",
            "if len(bounds) == 6:\n"
            "    _, non_empty, x1, y1, x2, y2 = bounds\n"
            "else:\n"
            "    non_empty, x1, y1, x2, y2 = bounds",
            "iw, ih = image.get_width(), image.get_height()",
            "is_all = non_empty and x1 == 0 and y1 == 0 and x2 == iw and y2 == ih",
            "print(json.dumps({"
            "'has_selection': bool(non_empty),"
            "'is_all': bool(is_all),"
            "'bounds': {'x': x1, 'y': y1, 'width': x2 - x1, 'height': y2 - y1},"
            "'image_size': {'width': iw, 'height': ih}"
            "}))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            sel_info = {}
            for out in result.get("results", []):
                if out and out.strip():
                    try:
                        sel_info = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            has = sel_info.get("has_selection", False)
            msg = "Selection active" if has else "No selection"
            if has and not sel_info.get("is_all"):
                b = sel_info.get("bounds", {})
                msg += f" — bounds ({b.get('x')},{b.get('y')}) {b.get('width')}x{b.get('height')}"
            return OperationResult.ok(
                operation="get_selection_info",
                message=msg,
                data=sel_info,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_selection_info", error=str(e)).model_dump()

    @mcp.tool()
    async def select_grow(radius: int) -> ToolResult:
        """Grow the current selection by a number of pixels.

        Args:
            radius: Number of pixels to grow the selection by.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            f"Gimp.Selection.grow(images[0], {radius})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="select_grow", message=f"Selection grown by {radius}px"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_grow", error=str(e)).model_dump()

    @mcp.tool()
    async def select_shrink(radius: int) -> ToolResult:
        """Shrink the current selection by a number of pixels.

        Args:
            radius: Number of pixels to shrink the selection by.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            f"Gimp.Selection.shrink(images[0], {radius})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="select_shrink", message=f"Selection shrunk by {radius}px"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="select_shrink", error=str(e)).model_dump()
