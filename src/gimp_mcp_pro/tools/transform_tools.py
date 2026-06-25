"""Transform tools for GIMP MCP Pro.

Covers scaling, rotation, flipping, cropping, and perspective transforms
for both images and individual layers.
"""

from __future__ import annotations

import logging

from gimp_mcp_pro.bridge import LONG_TIMEOUT
from gimp_mcp_pro.models.common import OperationResult, py_literal
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.transform")

VALID_SMART_RESIZE_MODES = {"crop", "pad", "resize"}
VALID_SMART_RESIZE_ANCHORS = {"center", "top_left", "top_right", "bottom_left", "bottom_right"}


def _img_preamble() -> list[str]:
    """Standard preamble to get active image."""
    return [
        "from gi.repository import Gimp, Gegl",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
    ]


def _interpolation_expr(interpolation: str) -> tuple[str, str]:
    """Return resolved interpolation key and generated GIMP enum expression."""
    key = interpolation.lower().strip().replace("-", "")
    interpolation_map = {
        "none": "Gimp.InterpolationType.NONE",
        "linear": "Gimp.InterpolationType.LINEAR",
        "cubic": "Gimp.InterpolationType.CUBIC",
        "nohalo": "Gimp.InterpolationType.NOHALO",
        "lohalo": "Gimp.InterpolationType.LOHALO",
    }
    resolved = key if key in interpolation_map else "cubic"
    return resolved, interpolation_map[resolved]


def _transform_resize_expr(resize: str) -> tuple[str, str]:
    """Return resolved transform-resize key and generated GIMP enum expression."""
    key = resize.lower().strip().replace("-", "_").replace(" ", "_")
    resize_map = {
        "adjust": "Gimp.TransformResize.ADJUST",
        "clip": "Gimp.TransformResize.CLIP",
        "crop": "Gimp.TransformResize.CROP",
        "crop_with_aspect": "Gimp.TransformResize.CROP_WITH_ASPECT",
    }
    resolved = key if key in resize_map else "adjust"
    return resolved, resize_map[resolved]


def _layer_target(layer_name: str | None, layer_index: int | None) -> list[str]:
    """Code to resolve a layer target."""
    if layer_name is not None:
        layer_name_expr = py_literal(layer_name)
        layer_error_expr = py_literal(f"Layer {layer_name!r} not found")
        return [
            f"target = image.get_layer_by_name({layer_name_expr})",
            f"if target is None: raise RuntimeError({layer_error_expr})",
        ]
    elif layer_index is not None:
        return [
            "layers = image.get_layers()",
            f"if {layer_index} >= len(layers): raise RuntimeError('Layer index out of range')",
            f"target = layers[{layer_index}]",
        ]
    else:
        return [
            "sel = image.get_selected_layers()",
            "if not sel: raise RuntimeError('No active layer')",
            "target = sel[0]",
        ]



def _anchor_offsets_code() -> str:
    """Return generated helper code for explicit anchor offsets."""
    return (
        "def anchor_offsets(old_width, old_height, target_width, target_height, anchor):\n"
        "    dx = target_width - old_width\n"
        "    dy = target_height - old_height\n"
        "    if anchor == 'top_left':\n"
        "        return 0, 0\n"
        "    if anchor == 'top_right':\n"
        "        return dx, 0\n"
        "    if anchor == 'bottom_left':\n"
        "        return 0, dy\n"
        "    if anchor == 'bottom_right':\n"
        "        return dx, dy\n"
        "    return dx // 2, dy // 2"
    )


def _smart_crop_or_resize_code(
    mode: str,
    target_width: int,
    target_height: int,
    anchor: str,
    preserve_layers: bool,
    background: str | None,
    dry_run: bool,
) -> list[str]:
    """Generate code for dry-run-aware smart crop/pad/resize operations."""
    code = _img_preamble() + [
        "import json",
        "# __gimp_mcp_smart_crop_or_resize__",
        f"mode = {py_literal(mode)}",
        f"target_width = {target_width}",
        f"target_height = {target_height}",
        f"anchor = {py_literal(anchor)}",
        f"preserve_layers = {preserve_layers!r}",
        f"dry_run = {dry_run!r}",
        _anchor_offsets_code(),
        "old_width = image.get_width()",
        "old_height = image.get_height()",
        "offset_x, offset_y = anchor_offsets(old_width, old_height, target_width, target_height, anchor)",
        "would_clip = target_width < old_width or target_height < old_height",
        "warnings = []",
        "if would_clip:\n"
        "    warnings.append({'code': 'would_clip', 'severity': 'warning', 'old_dimensions': {'width': old_width, 'height': old_height}, 'new_dimensions': {'width': target_width, 'height': target_height}})",
        "old_dimensions = {'width': old_width, 'height': old_height}",
        "new_dimensions = {'width': target_width, 'height': target_height}",
    ]
    if background is not None:
        code.append(f"Gimp.context_set_background(Gegl.Color.new({py_literal(background)}))")
    code += [
        "if not dry_run:\n"
        "    if mode == 'resize':\n"
        "        image.scale(target_width, target_height)\n"
        "    else:\n"
        "        image.resize(target_width, target_height, offset_x, offset_y)\n"
        "    Gimp.displays_flush()",
        "result = {'mode': mode, 'dry_run': dry_run, 'anchor': anchor, 'preserve_layers': preserve_layers, 'old_dimensions': old_dimensions, 'new_dimensions': new_dimensions, 'offset': {'x': offset_x, 'y': offset_y}, 'would_clip': would_clip, 'warnings': warnings}",
        "print(json.dumps(result))",
    ]
    return code


def register_transform_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all transform tools with the MCP server."""

    @mcp.tool()
    async def scale_image(
        new_width: int,
        new_height: int,
        interpolation: str = "cubic",
    ) -> ToolResult:
        """Scale the entire image (all layers) to new dimensions.

        Notes:
            Use this tool when resizing the final image for output, or changing
            overall canvas dimensions while scaling content.

        Args:
            new_width: Target width in pixels (1-32768)
            new_height: Target height in pixels (1-32768)
            interpolation: Quality — "none", "linear", "cubic" (recommended),
                          "nohalo", "lohalo"

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if new_width < 1 or new_width > 32768 or new_height < 1 or new_height > 32768:
            return OperationResult.fail(
                operation="scale_image",
                error=f"Dimensions must be 1-32768, got {new_width}x{new_height}",
            ).model_dump()

        interp_map = {
            "none": "Gimp.InterpolationType.NONE",
            "linear": "Gimp.InterpolationType.LINEAR",
            "cubic": "Gimp.InterpolationType.CUBIC",
            "nohalo": "Gimp.InterpolationType.NOHALO",
            "lohalo": "Gimp.InterpolationType.LOHALO",
        }
        interp_expr = interp_map.get(interpolation.lower(), "Gimp.InterpolationType.CUBIC")

        code = _img_preamble() + [
            f"Gimp.context_set_interpolation({interp_expr})",
            f"image.scale({new_width}, {new_height})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="scale_image",
                message=f"Image scaled to {new_width}x{new_height}",
                data={"width": new_width, "height": new_height},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="scale_image", error=str(e)).model_dump()

    @mcp.tool()
    async def scale_layer(
        new_width: int,
        new_height: int,
        interpolation: str = "cubic",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Scale a single layer to new dimensions.

        Notes:
            This changes the layer's pixel content, not the canvas.
            The layer may become larger or smaller than the image canvas.

        Args:
            new_width: Target width in pixels
            new_height: Target height in pixels
            interpolation: "none", "linear", "cubic", "nohalo", "lohalo"
            layer_name: Target layer by name. Uses active layer if neither specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        interp_map = {
            "none": "Gimp.InterpolationType.NONE",
            "linear": "Gimp.InterpolationType.LINEAR",
            "cubic": "Gimp.InterpolationType.CUBIC",
            "nohalo": "Gimp.InterpolationType.NOHALO",
            "lohalo": "Gimp.InterpolationType.LOHALO",
        }
        interp_expr = interp_map.get(interpolation.lower(), "Gimp.InterpolationType.CUBIC")

        code = (
            _img_preamble()
            + _layer_target(layer_name, layer_index)
            + [
                f"Gimp.context_set_interpolation({interp_expr})",
                f"target.scale({new_width}, {new_height}, True)",
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="scale_layer",
                message=f"Layer scaled to {new_width}x{new_height}",
                data={"width": new_width, "height": new_height},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="scale_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def rotate_image(angle: int) -> ToolResult:
        """Rotate the entire image by 90, 180, or 270 degrees.

        Args:
            angle: Rotation angle — must be 90, 180, or 270.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        rotation_map = {
            90: "Gimp.RotationType.DEGREES90",
            180: "Gimp.RotationType.DEGREES180",
            270: "Gimp.RotationType.DEGREES270",
        }
        if angle not in rotation_map:
            return OperationResult.fail(
                operation="rotate_image",
                error=f"angle must be 90, 180, or 270 (got {angle})",
            ).model_dump()

        code = _img_preamble() + [
            f"image.rotate({rotation_map[angle]})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="rotate_image",
                message=f"Image rotated {angle}°",
                data={"angle": angle},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="rotate_image", error=str(e)).model_dump()

    @mcp.tool()
    async def rotate_layer(
        angle_degrees: float,
        auto_resize: bool = True,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Rotate a layer by an arbitrary angle.

        Args:
            angle_degrees: Rotation angle in degrees (positive = counter-clockwise)
            auto_resize: If True, resize layer to fit rotated content
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        import math

        angle_rad = math.radians(angle_degrees)

        code = (
            _img_preamble()
            + _layer_target(layer_name, layer_index)
            + [
                "import math",
                f"angle_rad = {angle_rad}",
                "off = target.get_offsets()",
                "cx = off.offset_x + target.get_width() / 2.0",
                "cy = off.offset_y + target.get_height() / 2.0",
                f"Gimp.Item.transform_rotate(target, angle_rad, {'True' if auto_resize else 'False'}, cx, cy)",
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="rotate_layer",
                message=f"Layer rotated {angle_degrees}°",
                data={"angle_degrees": angle_degrees},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="rotate_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def perspective_layer(
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
        interpolation: str = "cubic",
        resize: str = "adjust",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Perspective-transform a layer by remapping its four bounding-box corners.

        Args:
            x0, y0: New upper-left corner.
            x1, y1: New upper-right corner.
            x2, y2: New lower-left corner.
            x3, y3: New lower-right corner.
            interpolation: "none", "linear", "cubic", "nohalo", or "lohalo".
            resize: Transform resize policy: "adjust", "clip", "crop", or "crop_with_aspect".
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and applied corner coordinates.
        """
        corners = [float(v) for v in (x0, y0, x1, y1, x2, y2, x3, y3)]
        resolved_interpolation, interp_expr = _interpolation_expr(interpolation)
        resolved_resize, resize_expr = _transform_resize_expr(resize)

        code = (
            _img_preamble()
            + _layer_target(layer_name, layer_index)
            + [
                f"Gimp.context_set_interpolation({interp_expr})",
                f"Gimp.context_set_transform_resize({resize_expr})",
                "Gimp.Item.transform_perspective(target, "
                f"{corners[0]}, {corners[1]}, {corners[2]}, {corners[3]}, "
                f"{corners[4]}, {corners[5]}, {corners[6]}, {corners[7]})",
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="perspective_layer",
                message="Layer perspective transform applied",
                data={
                    "corners": corners,
                    "interpolation": resolved_interpolation,
                    "resize": resolved_resize,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="perspective_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def shear_layer(
        direction: str = "horizontal",
        magnitude: float = 0.0,
        interpolation: str = "cubic",
        resize: str = "adjust",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Shear a layer horizontally or vertically by a pixel magnitude.

        Args:
            direction: "horizontal"/"h" or "vertical"/"v".
            magnitude: Shear magnitude in pixels; may be negative.
            interpolation: "none", "linear", "cubic", "nohalo", or "lohalo".
            resize: Transform resize policy: "adjust", "clip", "crop", or "crop_with_aspect".
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and applied shear settings.
        """
        direction_key = direction.lower().strip()
        resolved_direction = "vertical" if direction_key in {"v", "vertical"} else "horizontal"
        shear_expr = (
            "Gimp.OrientationType.VERTICAL"
            if resolved_direction == "vertical"
            else "Gimp.OrientationType.HORIZONTAL"
        )
        magnitude = float(magnitude)
        resolved_interpolation, interp_expr = _interpolation_expr(interpolation)
        resolved_resize, resize_expr = _transform_resize_expr(resize)

        code = (
            _img_preamble()
            + _layer_target(layer_name, layer_index)
            + [
                f"Gimp.context_set_interpolation({interp_expr})",
                f"Gimp.context_set_transform_resize({resize_expr})",
                f"Gimp.Item.transform_shear(target, {shear_expr}, {magnitude})",
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="shear_layer",
                message=f"Layer sheared {resolved_direction} by {magnitude}px",
                data={
                    "direction": resolved_direction,
                    "magnitude": magnitude,
                    "interpolation": resolved_interpolation,
                    "resize": resolved_resize,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="shear_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def flip_image(direction: str = "horizontal") -> ToolResult:
        """Flip the entire image.

        Args:
            direction: "horizontal" (mirror left/right) or "vertical" (mirror top/bottom)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        direction = direction.lower().strip()
        if direction not in ("horizontal", "vertical"):
            return OperationResult.fail(
                operation="flip_image",
                error="direction must be 'horizontal' or 'vertical'",
            ).model_dump()

        flip_type = (
            "Gimp.OrientationType.HORIZONTAL"
            if direction == "horizontal"
            else "Gimp.OrientationType.VERTICAL"
        )
        code = _img_preamble() + [
            f"image.flip({flip_type})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="flip_image",
                message=f"Image flipped {direction}",
                data={"direction": direction},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="flip_image", error=str(e)).model_dump()

    @mcp.tool()
    async def flip_layer(
        direction: str = "horizontal",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Flip a single layer.

        Args:
            direction: "horizontal" or "vertical"
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        direction = direction.lower().strip()
        if direction not in ("horizontal", "vertical"):
            return OperationResult.fail(
                operation="flip_layer", error="direction must be 'horizontal' or 'vertical'"
            ).model_dump()

        flip_type = (
            "Gimp.OrientationType.HORIZONTAL"
            if direction == "horizontal"
            else "Gimp.OrientationType.VERTICAL"
        )
        code = (
            _img_preamble()
            + _layer_target(layer_name, layer_index)
            + [
                f"Gimp.Item.transform_flip_simple(target, {flip_type}, True, 0)",
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="flip_layer",
                message=f"Layer flipped {direction}",
                data={"direction": direction},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="flip_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def crop_to_selection() -> ToolResult:
        """Crop the image to the current selection bounds.

        Notes:
            Use this tool after making a selection around the area you want to keep.
            The image canvas will be resized to fit the selection.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _img_preamble() + [
            "bounds = Gimp.Selection.bounds(image)",
            "if not bounds.non_empty: raise RuntimeError('No selection — select an area first')",
            "image.crop(bounds.x2 - bounds.x1, bounds.y2 - bounds.y1, bounds.x1, bounds.y1)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="crop_to_selection", message="Image cropped to selection"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="crop_to_selection", error=str(e)).model_dump()

    @mcp.tool()
    async def smart_crop_or_resize(
        mode: str,
        target_size: dict[str, int],
        anchor: str = "center",
        preserve_layers: bool = True,
        background: str | None = None,
        dry_run: bool = True,
    ) -> ToolResult:
        """Safely crop, pad, or resize with explicit anchors and dry-run support.

        Args:
            mode: ``crop``, ``pad``, or ``resize``.
            target_size: Mapping with integer ``width`` and ``height``.
            anchor: center, top_left, top_right, bottom_left, or bottom_right.
            preserve_layers: Keep layer structure where the selected operation supports it.
            background: Optional background color used when padding.
            dry_run: Report planned changes and clipping warnings without mutation.

        Returns:
            Operation result with old/new dimensions, offset, would_clip, and warnings.

        Contract:
            Dry-run mode never mutates GIMP. Destructive crop/pad operations report
            clipping risk in the result for verification.
        """
        normalized_mode = mode.strip().lower().replace("-", "_")
        normalized_anchor = anchor.strip().lower().replace("-", "_")
        if normalized_mode not in VALID_SMART_RESIZE_MODES:
            return OperationResult.fail(
                operation="smart_crop_or_resize",
                error="mode must be crop, pad, or resize",
            ).model_dump()
        if normalized_anchor not in VALID_SMART_RESIZE_ANCHORS:
            return OperationResult.fail(
                operation="smart_crop_or_resize",
                error="anchor must be center, top_left, top_right, bottom_left, or bottom_right",
            ).model_dump()
        try:
            target_width = int(target_size["width"])
            target_height = int(target_size["height"])
        except (KeyError, TypeError, ValueError):
            return OperationResult.fail(
                operation="smart_crop_or_resize",
                error="target_size must include integer width and height",
            ).model_dump()
        if target_width < 1 or target_height < 1:
            return OperationResult.fail(
                operation="smart_crop_or_resize",
                error="target width and height must be >= 1",
            ).model_dump()
        code = _smart_crop_or_resize_code(
            normalized_mode,
            target_width,
            target_height,
            normalized_anchor,
            preserve_layers,
            background,
            dry_run,
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="smart_crop_or_resize",
                message="Smart crop/resize plan generated" if dry_run else "Smart crop/resize applied",
                data={
                    "mode": normalized_mode,
                    "target_size": {"width": target_width, "height": target_height},
                    "anchor": normalized_anchor,
                    "preserve_layers": preserve_layers,
                    "dry_run": dry_run,
                    "warnings": [],
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="smart_crop_or_resize", error=str(e)
            ).model_dump()


    @mcp.tool()
    async def crop_image(
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> ToolResult:
        """Crop the image to a specific rectangle.

        Args:
            x: Left edge X coordinate
            y: Top edge Y coordinate
            width: Crop width in pixels
            height: Crop height in pixels

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if width < 1 or height < 1:
            return OperationResult.fail(
                operation="crop_image", error="width and height must be >= 1"
            ).model_dump()

        code = _img_preamble() + [
            f"image.crop({width}, {height}, {x}, {y})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="crop_image",
                message=f"Image cropped to {width}x{height} at ({x},{y})",
                data={"x": x, "y": y, "width": width, "height": height},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="crop_image", error=str(e)).model_dump()

    @mcp.tool()
    async def autocrop_image() -> ToolResult:
        """Automatically crop the image to remove border whitespace/transparency.

        Notes:
            Use this tool after drawing, to trim unused canvas around the content.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _img_preamble() + [
            "pdb = Gimp.get_pdb()",
            "proc = pdb.lookup_procedure('gimp-image-autocrop')",
            "if not proc: raise RuntimeError('Autocrop procedure not found')",
            "cfg = proc.create_config()",
            "cfg.set_property('image', image)",
            "sel = image.get_selected_layers()\nif sel:\n    try: cfg.set_property('drawable', sel[0])\n    except: pass",
            "proc.run(cfg)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="autocrop_image", message="Image auto-cropped"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="autocrop_image", error=str(e)).model_dump()

    @mcp.tool()
    async def resize_canvas(
        new_width: int,
        new_height: int,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> ToolResult:
        """Resize the image canvas without scaling content.

        Content stays the same size; canvas grows or shrinks around it.
        Use offsets to position existing content within the new canvas.

        Args:
            new_width: New canvas width
            new_height: New canvas height
            offset_x: Horizontal offset for existing content (can be negative)
            offset_y: Vertical offset for existing content (can be negative)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _img_preamble() + [
            f"image.resize({new_width}, {new_height}, {offset_x}, {offset_y})",
            "# Resize all layers to canvas",
            "for layer in image.get_layers():\n    layer.resize_to_image_size()",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="resize_canvas",
                message=f"Canvas resized to {new_width}x{new_height}",
                data={
                    "width": new_width,
                    "height": new_height,
                    "offset_x": offset_x,
                    "offset_y": offset_y,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="resize_canvas", error=str(e)).model_dump()

    @mcp.tool()
    async def offset_layer(
        offset_x: int,
        offset_y: int,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Move a layer by an offset (reposition within the canvas).

        Args:
            offset_x: Horizontal offset in pixels (positive = right)
            offset_y: Vertical offset in pixels (positive = down)
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = (
            _img_preamble()
            + _layer_target(layer_name, layer_index)
            + [
                f"target.set_offsets(target.get_offsets().offset_x + {offset_x}, "
                f"target.get_offsets().offset_y + {offset_y})",
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="offset_layer",
                message=f"Layer moved by ({offset_x}, {offset_y})",
                data={"offset_x": offset_x, "offset_y": offset_y},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="offset_layer", error=str(e)).model_dump()
