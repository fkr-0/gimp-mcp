"""Drawing tools for GIMP MCP Pro."""

from __future__ import annotations

import logging

from gimp_mcp_pro.models.common import Color, FillType, OperationResult, py_literal
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError
from gimp_mcp_pro.utils.gimp_constants import FILL_TYPE_MAP

logger = logging.getLogger("gimp_mcp_pro.tools.drawing")


GRADIENT_TYPE_MAP: dict[str, str] = {
    "linear": "Gimp.GradientType.LINEAR",
    "bilinear": "Gimp.GradientType.BILINEAR",
    "radial": "Gimp.GradientType.RADIAL",
    "square": "Gimp.GradientType.SQUARE",
    "conical_symmetric": "Gimp.GradientType.CONICAL_SYMMETRIC",
    "conical-asymmetric": "Gimp.GradientType.CONICAL_ASYMMETRIC",
    "conical_asymmetric": "Gimp.GradientType.CONICAL_ASYMMETRIC",
    "shapeburst_angular": "Gimp.GradientType.SHAPEBURST_ANGULAR",
    "shapeburst_spherical": "Gimp.GradientType.SHAPEBURST_SPHERICAL",
    "shapeburst_dimpled": "Gimp.GradientType.SHAPEBURST_DIMPLED",
    "spiral_clockwise": "Gimp.GradientType.SPIRAL_CLOCKWISE",
    "spiral_anticlockwise": "Gimp.GradientType.SPIRAL_ANTICLOCKWISE",
}

TEXT_JUSTIFICATION_MAP: dict[str, str] = {
    "left": "Gimp.TextJustification.LEFT",
    "right": "Gimp.TextJustification.RIGHT",
    "center": "Gimp.TextJustification.CENTER",
    "fill": "Gimp.TextJustification.FILL",
}


def _set_color_code(color: Color | None, target: str = "foreground") -> list[str]:
    """Generate code to set foreground or background color."""
    if color is None:
        return []
    gegl_expr = color.to_gegl_code()
    if target == "foreground":
        return [
            "from gi.repository import Gegl",
            f"_color = {gegl_expr}",
            "Gimp.context_set_foreground(_color)",
        ]
    else:
        return [
            "from gi.repository import Gegl",
            f"_color = {gegl_expr}",
            "Gimp.context_set_background(_color)",
        ]


def _get_drawable_code() -> list[str]:
    """Generate code to get the current drawable."""
    return [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "sel = image.get_selected_layers()",
        "if not sel: raise RuntimeError('No active layer')",
        "drawable = sel[0]",
    ]


def _create_text_box_code(
    text: str,
    rectangle: dict[str, int],
    style: dict[str, object],
    name: str | None,
) -> list[str]:
    """Return generated code that creates a styled text layer in a rectangle."""
    x = int(rectangle["x"])
    y = int(rectangle["y"])
    width = int(rectangle["width"])
    height = int(rectangle["height"])
    font = str(style.get("font", "Sans"))
    font_size = float(style.get("font_size", style.get("size", 24.0)))
    color = str(style.get("color", "#000000"))
    justify = str(style.get("justify", "left")).lower().replace("-", "_")
    justify_expr = TEXT_JUSTIFICATION_MAP.get(justify, "Gimp.TextJustification.LEFT")
    layer_name = name or (text[:32] if text else "Text box")
    return [
        "from gi.repository import Gimp, Gegl",
        "import json",
        "# __gimp_mcp_create_text_box__",
        f"text = {py_literal(text)}",
        f"x = {x}",
        f"y = {y}",
        f"width = {width}",
        f"height = {height}",
        f"font_name = {py_literal(font)}",
        f"font_size = {font_size!r}",
        f"layer_name = {py_literal(layer_name)}",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "fonts = Gimp.fonts_get_list('')",
        "font_values = fonts[-1] if isinstance(fonts, tuple) else fonts",
        "font_names = [str(item.get_name() if hasattr(item, 'get_name') else item) for item in (font_values or [])]",
        "warnings = []",
        "if font_name not in font_names and font_names:\n"
        "    warnings.append({'code': 'font_fallback', 'requested': font_name})",
        "text_layer = Gimp.TextLayer.new(image, text, font_name, font_size, Gimp.Unit.pixel())",
        "text_layer.set_name(layer_name)",
        "image.insert_layer(text_layer, None, 0)",
        "text_layer.set_offsets(x, y)",
        "text_layer.resize(width, height)",
        f"text_layer.set_justification({justify_expr})",
        f"text_layer.set_color(Gegl.Color.new({py_literal(color)}))",
        "Gimp.displays_flush()",
        "result = {'layer_id': int(text_layer.get_id()) if hasattr(text_layer, 'get_id') else None, 'bounds': {'x': x, 'y': y, 'width': width, 'height': height}, 'warnings': warnings}",
        "print(json.dumps(result))",
    ]


def register_drawing_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all drawing tools with the MCP server."""

    @mcp.tool()
    async def set_foreground_color(color: str) -> ToolResult:
        """Set the foreground color used for drawing operations.

        Notes:
            Use this tool before any drawing, fill, or stroke operation that
            uses the foreground color.

        Args:
            color: Color as name ("red"), hex ("#FF0000"), or rgb("rgb(255,0,0)")

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        c = Color(value=color)
        code = [
            "from gi.repository import Gimp, Gegl",
            f"_color = {c.to_gegl_code()}",
            "Gimp.context_set_foreground(_color)",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="set_foreground_color",
                message=f"Foreground color set to {color}",
                data={"color": color},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_foreground_color", error=str(e)).model_dump()

    @mcp.tool()
    async def set_background_color(color: str) -> ToolResult:
        """Set the background color.

        Args:
            color: Color as name ("white"), hex ("#FFFFFF"), or rgb("rgb(255,255,255)")

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        c = Color(value=color)
        code = [
            "from gi.repository import Gimp, Gegl",
            f"_color = {c.to_gegl_code()}",
            "Gimp.context_set_background(_color)",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="set_background_color",
                message=f"Background color set to {color}",
                data={"color": color},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_background_color", error=str(e)).model_dump()

    @mcp.tool()
    async def fill_selection(
        fill_type: str = "foreground",
        color: str | None = None,
    ) -> ToolResult:
        """Fill the current selection (or entire layer if no selection) with color.

        Notes:
            Use this tool after creating a selection (rectangle, ellipse, polygon),
            fill it with a color to create shapes.

            Best practice guidance:
            - Use polygon selection plus fill for solid shapes instead of paintbrush strokes.
            - Clear the selection after filling; this tool calls select_none automatically.
            - Avoid feathering unless soft edges are intentional.

        Args:
            fill_type: "foreground", "background", "white", "transparent", or "pattern"
            color: Optional color to set before filling (sets foreground color).
                   Uses current foreground if not specified.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        fill_expr = FILL_TYPE_MAP.get(FillType(fill_type), "Gimp.FillType.FOREGROUND")
        code = ["from gi.repository import Gimp, Gegl"]

        if color:
            c = Color(value=color)
            code += [
                f"_color = {c.to_gegl_code()}",
                "Gimp.context_set_foreground(_color)",
            ]

        code += _get_drawable_code() + [
            f"Gimp.Drawable.edit_fill(drawable, {fill_expr})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="fill_selection",
                message=f"Filled with {fill_type}" + (f" ({color})" if color else ""),
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="fill_selection", error=str(e)).model_dump()

    @mcp.tool()
    async def draw_line(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: str | None = None,
        brush_size: float = 2.0,
    ) -> ToolResult:
        """Draw a straight line between two points.

        Args:
            x1, y1: Start coordinates
            x2, y2: End coordinates
            color: Line color. Uses current foreground if not specified.
            brush_size: Line width in pixels (default 2.0)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = ["from gi.repository import Gimp, Gegl"]
        if color:
            c = Color(value=color)
            code += [f"Gimp.context_set_foreground({c.to_gegl_code()})"]

        code += _get_drawable_code() + [
            f"Gimp.context_set_brush_size({brush_size})",
            f"Gimp.pencil(drawable, [{x1}, {y1}, {x2}, {y2}])",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="draw_line",
                message=f"Drew line from ({x1},{y1}) to ({x2},{y2})",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="draw_line", error=str(e)).model_dump()

    @mcp.tool()
    async def draw_brush_stroke(
        points: list[float],
        tool: str = "pencil",
        color: str | None = None,
        brush_size: float = 2.0,
    ) -> ToolResult:
        """Draw a stroke along a series of points.

        Use 'pencil' for hard-edged lines, 'paintbrush' for soft brush strokes.

        Notes:
            For filling shapes, do NOT use brush strokes — use polygon
            selection + fill_selection instead. Brush strokes create outlines only.

        Args:
            points: Flat list of coordinates [x1, y1, x2, y2, x3, y3, ...]
            tool: "pencil" (hard edge) or "paintbrush" (soft)
            color: Stroke color. Uses current foreground if not specified.
            brush_size: Brush width in pixels

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if len(points) < 4 or len(points) % 2 != 0:
            return OperationResult.fail(
                operation="draw_brush_stroke",
                error="points must have at least 4 values and an even count",
            ).model_dump()

        code = ["from gi.repository import Gimp, Gegl"]
        if color:
            c = Color(value=color)
            code += [f"Gimp.context_set_foreground({c.to_gegl_code()})"]

        code += _get_drawable_code() + [
            f"Gimp.context_set_brush_size({brush_size})",
        ]

        points_str = str(points)
        if tool == "paintbrush":
            code.append(f"Gimp.paintbrush_default(drawable, {points_str})")
        else:
            code.append(f"Gimp.pencil(drawable, {points_str})")

        code.append("Gimp.displays_flush()")

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="draw_brush_stroke",
                message=f"Drew {tool} stroke with {len(points) // 2} points",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="draw_brush_stroke", error=str(e)).model_dump()

    @mcp.tool()
    async def draw_rectangle(
        x: float,
        y: float,
        width: float,
        height: float,
        filled: bool = True,
        color: str | None = None,
        line_width: float = 2.0,
    ) -> ToolResult:
        """Draw a rectangle (filled or outline only).

        Notes:
            Best practice: Uses selection + fill for filled rectangles (not brush).
            This produces clean, solid shapes.

        Args:
            x, y: Top-left corner coordinates
            width, height: Rectangle dimensions
            filled: True for solid fill, False for outline only
            color: Shape color. Uses current foreground if not specified.
            line_width: Outline width for non-filled rectangles

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = ["from gi.repository import Gimp, Gegl"]
        if color:
            c = Color(value=color)
            code += [f"Gimp.context_set_foreground({c.to_gegl_code()})"]

        code += _get_drawable_code() + [
            f"Gimp.Image.select_rectangle(image, Gimp.ChannelOps.REPLACE, {x}, {y}, {width}, {height})",
        ]

        if filled:
            code += [
                "Gimp.Drawable.edit_fill(drawable, Gimp.FillType.FOREGROUND)",
            ]
        else:
            code += [
                f"Gimp.context_set_line_width({line_width})",
                "Gimp.Drawable.edit_stroke_selection(drawable)",
            ]

        code += [
            "Gimp.Selection.none(image)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            mode = "filled" if filled else "outline"
            return OperationResult.ok(
                operation="draw_rectangle",
                message=f"Drew {mode} rectangle at ({x},{y}) size {width}x{height}",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="draw_rectangle", error=str(e)).model_dump()

    @mcp.tool()
    async def draw_ellipse(
        x: float,
        y: float,
        width: float,
        height: float,
        filled: bool = True,
        color: str | None = None,
        line_width: float = 2.0,
    ) -> ToolResult:
        """Draw an ellipse/circle (filled or outline only).

        For a circle, set width == height.

        Args:
            x, y: Bounding box top-left corner
            width, height: Bounding box dimensions
            filled: True for solid fill, False for outline only
            color: Shape color. Uses current foreground if not specified.
            line_width: Outline width for non-filled ellipses

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = ["from gi.repository import Gimp, Gegl"]
        if color:
            c = Color(value=color)
            code += [f"Gimp.context_set_foreground({c.to_gegl_code()})"]

        code += _get_drawable_code() + [
            f"Gimp.Image.select_ellipse(image, Gimp.ChannelOps.REPLACE, {x}, {y}, {width}, {height})",
        ]

        if filled:
            code += ["Gimp.Drawable.edit_fill(drawable, Gimp.FillType.FOREGROUND)"]
        else:
            code += [
                f"Gimp.context_set_line_width({line_width})",
                "Gimp.Drawable.edit_stroke_selection(drawable)",
            ]

        code += [
            "Gimp.Selection.none(image)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            mode = "filled" if filled else "outline"
            return OperationResult.ok(
                operation="draw_ellipse",
                message=f"Drew {mode} ellipse at ({x},{y}) size {width}x{height}",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="draw_ellipse", error=str(e)).model_dump()

    @mcp.tool()
    async def draw_polygon(
        points: list[float],
        filled: bool = True,
        color: str | None = None,
        line_width: float = 2.0,
    ) -> ToolResult:
        """Draw a polygon (filled or outline).

        Notes:
            Best practice: This is THE correct way to draw filled shapes in GIMP.
            Uses polygon selection + fill, producing clean solid shapes.

        Args:
            points: Flat list of vertex coordinates [x1,y1, x2,y2, x3,y3, ...]
                    Minimum 3 vertices (6 values).
            filled: True for solid fill, False for outline only
            color: Shape color. Uses current foreground if not specified.
            line_width: Outline width for non-filled polygons

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if len(points) < 6 or len(points) % 2 != 0:
            return OperationResult.fail(
                operation="draw_polygon",
                error="Need at least 3 points (6 values) with even count",
            ).model_dump()

        code = ["from gi.repository import Gimp, Gegl"]
        if color:
            c = Color(value=color)
            code += [f"Gimp.context_set_foreground({c.to_gegl_code()})"]

        code += _get_drawable_code() + [
            f"Gimp.Image.select_polygon(image, Gimp.ChannelOps.REPLACE, {points})",
        ]

        if filled:
            code += ["Gimp.Drawable.edit_fill(drawable, Gimp.FillType.FOREGROUND)"]
        else:
            code += [
                f"Gimp.context_set_line_width({line_width})",
                "Gimp.Drawable.edit_stroke_selection(drawable)",
            ]

        code += [
            "Gimp.Selection.none(image)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            n_verts = len(points) // 2
            mode = "filled" if filled else "outline"
            return OperationResult.ok(
                operation="draw_polygon",
                message=f"Drew {mode} polygon with {n_verts} vertices",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="draw_polygon", error=str(e)).model_dump()

    @mcp.tool()
    async def create_text_box(
        text: str,
        rectangle: dict[str, int],
        style: dict[str, object] | None = None,
        name: str | None = None,
    ) -> ToolResult:
        """Create a new text layer at an explicit rectangle with styling.

        Args:
            text: Text content for the new layer.
            rectangle: Mapping with x, y, width, and height.
            style: Optional font, font_size, color, and justification settings.
            name: Optional layer name.

        Returns:
            Operation result with requested text-box bounds and style metadata.
        """
        if not text:
            return OperationResult.fail(
                operation="create_text_box", error="text must not be empty"
            ).model_dump()
        try:
            int(rectangle["x"])
            int(rectangle["y"])
            width = int(rectangle["width"])
            height = int(rectangle["height"])
        except (KeyError, TypeError, ValueError):
            return OperationResult.fail(
                operation="create_text_box",
                error="rectangle must include integer x, y, width, height",
            ).model_dump()
        if width <= 0 or height <= 0:
            return OperationResult.fail(
                operation="create_text_box", error="rectangle width and height must be positive"
            ).model_dump()
        try:
            await bridge.async_execute_python(
                _create_text_box_code(text, rectangle, style or {}, name)
            )
            return OperationResult.ok(
                operation="create_text_box",
                message="Text box created",
                data={"text": text, "rectangle": rectangle, "style": style or {}, "name": name},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="create_text_box", error=str(e)).model_dump()

    @mcp.tool()
    async def add_text(
        text: str,
        x: float = 0.0,
        y: float = 0.0,
        font_name: str = "Sans",
        font_size: float = 24.0,
        color: str | None = None,
        layer_name: str = "Text",
    ) -> ToolResult:
        """Add a text layer to the image.

        Creates a new floating text layer at the specified position.

        Args:
            text: The text content to add.
            x: X position for text placement.
            y: Y position for text placement.
            font_name: Font name (e.g., "Sans", "Serif", "Monospace").
            font_size: Font size in pixels.
            color: Text color. Uses current foreground if not specified.
            layer_name: Name for the text layer.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = ["from gi.repository import Gimp, Gegl"]
        if color:
            c = Color(value=color)
            code += [f"Gimp.context_set_foreground({c.to_gegl_code()})"]

        # Use Python literals for all user-controlled strings inside generated code.
        text_expr = py_literal(text)
        layer_name_expr = py_literal(layer_name)

        # Map common font names to GIMP 3.0 font names
        font_map = {
            "sans": "Sans-serif",
            "sans-serif": "Sans-serif",
            "serif": "Serif",
            "mono": "Monospace",
            "monospace": "Monospace",
        }
        resolved_font = font_map.get(font_name.lower(), font_name)

        code += [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            f"font = Gimp.Font.get_by_name({py_literal(resolved_font)})",
            "if font is None: font = Gimp.context_get_font()",
            "unit = Gimp.Unit.pixel()",
            f"text_layer = Gimp.TextLayer.new(image, {text_expr}, font, {font_size}, unit)",
            "image.insert_layer(text_layer, None, 0)",
            f"text_layer.set_offsets({int(x)}, {int(y)})",
            f"text_layer.set_name({layer_name_expr})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="add_text",
                message=f'Text layer added: "{text[:50]}..."'
                if len(text) > 50
                else f'Text layer added: "{text}"',
                data={"text": text, "x": x, "y": y, "font": font_name, "size": font_size},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="add_text", error=str(e)).model_dump()

    @mcp.tool()
    async def gradient_fill(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        gradient_type: str = "linear",
        foreground_color: str | None = None,
        background_color: str | None = None,
        offset: float = 0.0,
        dither: bool = True,
        supersample: bool = False,
        supersample_max_depth: int = 3,
        supersample_threshold: float = 0.2,
    ) -> ToolResult:
        """Fill the current drawable/selection with a gradient between two points.

        Args:
            x1, y1: Gradient start coordinate.
            x2, y2: Gradient end coordinate.
            gradient_type: linear, bilinear, radial, square, conical_symmetric,
                conical_asymmetric, shapeburst_angular, shapeburst_spherical,
                shapeburst_dimpled, spiral_clockwise, or spiral_anticlockwise.
            foreground_color: Optional foreground color for FG/BG gradients.
            background_color: Optional background color for FG/BG gradients.
            offset: Mode-dependent gradient offset.
            dither: Whether to dither to reduce banding.
            supersample: Whether to use adaptive supersampling.
            supersample_max_depth: Maximum supersampling recursion depth.
            supersample_threshold: Supersampling threshold.

        Returns:
            Operation result dictionary with status, message, and gradient metadata.
        """
        gradient_key = gradient_type.lower().strip().replace("-", "_")
        gradient_expr = GRADIENT_TYPE_MAP.get(gradient_key)
        if gradient_expr is None:
            return OperationResult.fail(
                operation="gradient_fill",
                error="gradient_type must be one of: " + ", ".join(sorted(GRADIENT_TYPE_MAP)),
            ).model_dump()
        if supersample_max_depth < 1:
            return OperationResult.fail(
                operation="gradient_fill", error="supersample_max_depth must be greater than 0"
            ).model_dump()
        if supersample_threshold < 0:
            return OperationResult.fail(
                operation="gradient_fill", error="supersample_threshold must be non-negative"
            ).model_dump()

        code = ["from gi.repository import Gimp, Gegl"]
        if foreground_color:
            try:
                fg = Color(value=foreground_color)
            except ValueError as exc:
                return OperationResult.fail(operation="gradient_fill", error=str(exc)).model_dump()
            code.append(f"Gimp.context_set_foreground({fg.to_gegl_code()})")
        if background_color:
            try:
                bg = Color(value=background_color)
            except ValueError as exc:
                return OperationResult.fail(operation="gradient_fill", error=str(exc)).model_dump()
            code.append(f"Gimp.context_set_background({bg.to_gegl_code()})")

        code += _get_drawable_code() + [
            f"Gimp.Drawable.edit_gradient_fill(drawable, {gradient_expr}, {offset}, {supersample}, {supersample_max_depth}, {supersample_threshold}, {dither}, {x1}, {y1}, {x2}, {y2})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="gradient_fill",
                message=f"Applied {gradient_key} gradient from ({x1},{y1}) to ({x2},{y2})",
                data={
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "gradient_type": gradient_key,
                    "dither": dither,
                    "supersample": supersample,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="gradient_fill", error=str(e)).model_dump()

    @mcp.tool()
    async def edit_text_layer(
        text: str | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
        font_name: str | None = None,
        font_size: float | None = None,
        color: str | None = None,
        justification: str | None = None,
    ) -> ToolResult:
        """Edit an existing text layer's content and core text properties.

        Args:
            text: New text content. Leave unset to keep existing text.
            layer_name: Text layer name to edit.
            layer_index: Text layer index to edit. Uses active layer if neither specified.
            font_name: Optional new font name.
            font_size: Optional new font size in pixels.
            color: Optional text color.
            justification: Optional alignment: left, right, center, or fill.

        Returns:
            Operation result dictionary with status, message, and edited fields.
        """
        if (
            text is None
            and font_name is None
            and font_size is None
            and color is None
            and justification is None
        ):
            return OperationResult.fail(
                operation="edit_text_layer",
                error="provide at least one text property to change",
            ).model_dump()
        if font_size is not None and font_size <= 0:
            return OperationResult.fail(
                operation="edit_text_layer", error="font_size must be greater than 0"
            ).model_dump()

        justification_expr = None
        if justification is not None:
            justification_key = justification.lower().strip()
            justification_expr = TEXT_JUSTIFICATION_MAP.get(justification_key)
            if justification_expr is None:
                return OperationResult.fail(
                    operation="edit_text_layer",
                    error="justification must be one of: left, right, center, fill",
                ).model_dump()

        color_expr = None
        if color is not None:
            try:
                color_expr = Color(value=color).to_gegl_code()
            except ValueError as exc:
                return OperationResult.fail(
                    operation="edit_text_layer", error=str(exc)
                ).model_dump()

        code = [
            "from gi.repository import Gimp, Gegl",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
        ]
        if layer_name is not None:
            code += [
                f"layer = image.get_layer_by_name({py_literal(layer_name)})",
                f"if layer is None: raise RuntimeError({py_literal(f'Layer {layer_name!r} not found')})",
            ]
        elif layer_index is not None:
            code += [
                "layers = image.get_layers()",
                f"if {layer_index} >= len(layers): raise RuntimeError('Layer index {layer_index} out of range')",
                f"layer = layers[{layer_index}]",
            ]
        else:
            code += [
                "selected_layers = image.get_selected_layers()",
                "if not selected_layers: raise RuntimeError('No active layer')",
                "layer = selected_layers[0]",
            ]
        code += [
            "text_layer = Gimp.TextLayer.get_by_id(layer.get_id())",
            "if text_layer is None: raise RuntimeError('Target layer is not a text layer')",
        ]
        changed: list[str] = []
        if text is not None:
            code.append(f"text_layer.set_text({py_literal(text)})")
            changed.append("text")
        if font_name is not None:
            code += [
                f"font = Gimp.Font.get_by_name({py_literal(font_name)})",
                f"if font is None: raise RuntimeError({py_literal(f'Font {font_name!r} not found')})",
                "text_layer.set_font(font)",
            ]
            changed.append("font_name")
        if font_size is not None:
            code.append(f"text_layer.set_font_size({font_size}, Gimp.Unit.pixel())")
            changed.append("font_size")
        if color_expr is not None:
            code.append(f"text_layer.set_color({color_expr})")
            changed.append("color")
        if justification_expr is not None:
            code.append(f"text_layer.set_justification({justification_expr})")
            changed.append("justification")
        code.append("Gimp.displays_flush()")

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="edit_text_layer",
                message="Edited text layer",
                data={"changed": changed, "layer_name": layer_name, "layer_index": layer_index},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="edit_text_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def edit_clear() -> ToolResult:
        """Clear the current selection area (make it transparent).

        Notes:
            Use this tool to erase part of a layer. The cleared area becomes
            transparent if the layer has an alpha channel.

        Requires: Active layer must have an alpha channel. Use
        add_alpha_channel first if needed.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _get_drawable_code() + [
            "Gimp.Drawable.edit_clear(drawable)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="edit_clear", message="Selection cleared"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="edit_clear", error=str(e)).model_dump()
