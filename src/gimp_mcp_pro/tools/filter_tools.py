"""Filter and effects tools for GIMP MCP Pro.

Covers blur, sharpen, noise, edge detection, and artistic effects.
All filters use Gimp.DrawableFilter which wraps GEGL safely in plugin context.
(Direct GEGL graph construction crashes in GIMP 3.0 plugin context.)
"""

from __future__ import annotations

import logging

from gimp_mcp_pro.bridge import LONG_TIMEOUT
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.filter")


def py_literal(value: str) -> str:
    """Return a safe Python string literal for generated GIMP code."""
    return repr(value)


def _filter_preamble(layer_name: str | None, layer_index: int | None) -> list[str]:
    """Standard preamble for filter tools — get image and target drawable."""
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


def _apply_drawable_filter(gegl_op: str, props: dict[str, str]) -> list[str]:
    """Generate code to apply a GEGL filter via Gimp.DrawableFilter.

    This is the safe, stable way to apply filters in GIMP 3.0 plugin context.
    The pattern is: create filter → set config props → append → merge.

    Args:
        gegl_op: GEGL operation name (e.g. 'gegl:gaussian-blur')
        props: dict mapping property name to Python expression string
    """
    prop_lines = []
    for k, v in props.items():
        prop_lines.append(f"cfg.set_property('{k}', {v})")

    return (
        [
            f"df = Gimp.DrawableFilter.new(drawable, '{gegl_op}', '')",
            "cfg = df.get_config()",
        ]
        + prop_lines
        + [
            "drawable.append_filter(df)",
            "drawable.merge_filter(df)",
            "Gimp.displays_flush()",
        ]
    )


def _preview_filter_code(
    gegl_op: str,
    props: dict[str, str],
    layer_name: str | None,
    layer_index: int | None,
) -> list[str]:
    """Generate code that applies a filter to a temporary preview layer."""
    code = _filter_preamble(layer_name, layer_index)
    code += [
        "preview_layer = drawable.copy()",
        f"preview_layer.set_name({py_literal('Preview: ' + gegl_op)})",
        "layers = image.get_layers()",
        "position = list(layers).index(drawable) + 1 if drawable in layers else 0",
        "image.insert_layer(preview_layer, None, position)",
    ]
    prop_lines = [f"cfg.set_property('{key}', {value})" for key, value in props.items()]
    code += [
        f"df = Gimp.DrawableFilter.new(preview_layer, '{gegl_op}', '')",
        "cfg = df.get_config()",
        *prop_lines,
        "preview_layer.append_filter(df)",
        "preview_layer.merge_filter(df)",
        "Gimp.displays_flush()",
    ]
    return code


def _preview_filter_spec(
    filter_name: str, parameters: dict[str, object]
) -> tuple[str, dict[str, str], dict[str, object]]:
    """Resolve a supported preview filter into GEGL op/properties."""
    key = filter_name.strip().lower().replace("-", "_")
    if key in {"gaussian_blur", "gaussian"}:
        radius_x = float(parameters.get("radius_x", parameters.get("radius", 5.0)))
        radius_y = float(parameters.get("radius_y", radius_x))
        return (
            "gegl:gaussian-blur",
            {"std-dev-x": str(radius_x), "std-dev-y": str(radius_y)},
            {"filter": "gaussian_blur", "radius_x": radius_x, "radius_y": radius_y},
        )
    if key in {"unsharp_mask", "sharpen"}:
        amount = float(parameters.get("amount", 0.5))
        radius = float(parameters.get("radius", 3.0))
        threshold = float(parameters.get("threshold", 0.0))
        return (
            "gegl:unsharp-mask",
            {"scale": str(amount), "std-dev": str(radius), "threshold": str(threshold)},
            {"filter": "unsharp_mask", "amount": amount, "radius": radius, "threshold": threshold},
        )
    if key in {"motion_blur", "motion_blur_linear"}:
        length = float(parameters.get("length", 10.0))
        angle = float(parameters.get("angle", 0.0))
        return (
            "gegl:motion-blur-linear",
            {"length": str(length), "angle": str(angle)},
            {"filter": "motion_blur_linear", "length": length, "angle": angle},
        )
    raise ValueError(f"Unsupported filter: {filter_name}")



def _commit_filter_preview_code(
    preview_id: str,
    action: str,
    committed_name: str | None,
) -> list[str]:
    """Generate action-specific code that commits or discards a preview layer."""
    code = [
        "from gi.repository import Gimp",
        "import json",
        "# __gimp_mcp_commit_filter_preview__",
        f"preview_id = {py_literal(preview_id)}",
        f"action = {py_literal(action)}",
        f"committed_name = {py_literal(committed_name or preview_id)}",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "layers = list(image.get_layers())",
        "preview_layer = None",
        "for layer in layers:\n"
        "    layer_name = layer.get_name()\n"
        "    layer_id = str(layer.get_id()) if hasattr(layer, 'get_id') else ''\n"
        "    if layer_name == preview_id or layer_id == preview_id:\n"
        "        preview_layer = layer\n"
        "        break",
        "if preview_layer is None: raise RuntimeError(f'Preview layer not found: {preview_id}')",
    ]
    if action == "discard":
        code += [
            "image.remove_layer(preview_layer)",
            "result = {'status': 'discarded', 'preview_id': preview_id, 'temporary_layer_removed': True}",
        ]
    else:
        code += [
            "image.undo_group_start()",
            "try:",
            f"    preview_layer.set_name({py_literal(committed_name or preview_id)})",
            "    result = {'status': 'committed', 'preview_id': preview_id, 'committed_name': committed_name, 'transaction_wrapped': True}",
            "finally:",
            "    image.undo_group_end()",
        ]
    code += [
        "Gimp.displays_flush()",
        "print(json.dumps(result))",
    ]
    return code


def register_filter_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all filter/effect tools with the MCP server."""

    @mcp.tool()
    async def preview_filter(
        filter: str,
        parameters: dict[str, object] | None = None,
        preview_mode: str = "temporary_layer",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply a supported filter to a temporary preview layer.

        Args:
            filter: Supported filter name such as ``gaussian_blur``.
            parameters: Filter-specific parameter dictionary.
            preview_mode: Currently ``temporary_layer``.
            layer_name: Target layer by name.
            layer_index: Target layer by index.

        Returns:
            Operation result with preview metadata and warnings.

        Contract:
            The original drawable is not filtered. A copied preview layer receives
            the GEGL filter so the caller can inspect before committing.
        """
        if preview_mode != "temporary_layer":
            return OperationResult.fail(
                operation="preview_filter",
                error="preview_mode must be temporary_layer",
            ).model_dump()
        params = parameters or {}
        try:
            gegl_op, props, applied = _preview_filter_spec(filter, params)
        except (TypeError, ValueError) as e:
            return OperationResult.fail(operation="preview_filter", error=str(e)).model_dump()
        code = _preview_filter_code(gegl_op, props, layer_name, layer_index)
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="preview_filter",
                message=f"Preview layer created for {applied['filter']}",
                data={
                    "preview_layer_id": None,
                    "preview_png": None,
                    "preview_mode": preview_mode,
                    "gegl_operation": gegl_op,
                    "parameters": applied,
                    "warnings": [
                        "preview layer must be committed or discarded by a follow-up workflow"
                    ],
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="preview_filter", error=str(e)).model_dump()

    @mcp.tool()
    async def commit_filter_preview(
        preview_id: str,
        action: str,
        committed_name: str | None = None,
    ) -> ToolResult:
        """Commit or discard a temporary filter preview layer.

        Args:
            preview_id: Preview layer name or ID returned by a preview workflow.
            action: ``commit`` to promote the layer, or ``discard`` to remove it.
            committed_name: Optional final layer name when committing.

        Returns:
            Operation result with commit/discard metadata.

        Contract:
            Discard always removes the temporary preview layer. Commit is wrapped
            in a GIMP undo group transaction and never calls export or save APIs.
        """
        normalized_action = action.strip().lower().replace("-", "_")
        if normalized_action not in {"commit", "discard"}:
            return OperationResult.fail(
                operation="commit_filter_preview",
                error="action must be commit or discard",
            ).model_dump()
        if not preview_id.strip():
            return OperationResult.fail(
                operation="commit_filter_preview",
                error="preview_id is required",
            ).model_dump()
        code = _commit_filter_preview_code(
            preview_id.strip(), normalized_action, committed_name
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="commit_filter_preview",
                message=f"Filter preview {normalized_action} requested",
                data={
                    "preview_id": preview_id,
                    "action": normalized_action,
                    "committed_name": committed_name,
                    "transaction_wrapped": normalized_action == "commit",
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="commit_filter_preview", error=str(e)
            ).model_dump()


    @mcp.tool()
    async def apply_gaussian_blur(
        radius_x: float = 5.0,
        radius_y: float | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply Gaussian blur to a layer.

        Notes:
            Use this tool when softening images, creating depth-of-field effects,
            blurring backgrounds, smoothing noise.

        Args:
            radius_x: Horizontal blur radius in pixels (0.0-500.0)
            radius_y: Vertical blur radius. Defaults to radius_x for uniform blur.
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if radius_y is None:
            radius_y = radius_x

        code = _filter_preamble(layer_name, layer_index)
        code += _apply_drawable_filter(
            "gegl:gaussian-blur",
            {
                "std-dev-x": str(radius_x),
                "std-dev-y": str(radius_y),
            },
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_gaussian_blur",
                message=f"Gaussian blur applied (radius {radius_x}x{radius_y})",
                data={"radius_x": radius_x, "radius_y": radius_y},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_gaussian_blur", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_motion_blur(
        blur_type: str = "linear",
        length: float = 10.0,
        angle: float = 0.0,
        center_x: float = 0.0,
        center_y: float = 0.0,
        factor: float = 0.1,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply linear, circular, or zoom motion blur to a layer.

        Args:
            blur_type: "linear", "circular", or "zoom".
            length: Linear blur length in pixels.
            angle: Linear/circular blur angle in degrees.
            center_x: Circular/zoom blur center X coordinate.
            center_y: Circular/zoom blur center Y coordinate.
            factor: Zoom blur factor.
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and applied blur settings.
        """
        blur_key = blur_type.lower().strip().replace("-", "_")
        code = _filter_preamble(layer_name, layer_index)
        if blur_key == "zoom":
            applied = {
                "blur_type": "zoom",
                "center_x": float(center_x),
                "center_y": float(center_y),
                "factor": float(factor),
            }
            code += _apply_drawable_filter(
                "gegl:motion-blur-zoom",
                {
                    "center-x": str(applied["center_x"]),
                    "center-y": str(applied["center_y"]),
                    "factor": str(applied["factor"]),
                },
            )
        elif blur_key == "circular":
            applied = {
                "blur_type": "circular",
                "center_x": float(center_x),
                "center_y": float(center_y),
                "angle": float(angle),
            }
            code += _apply_drawable_filter(
                "gegl:motion-blur-circular",
                {
                    "center-x": str(applied["center_x"]),
                    "center-y": str(applied["center_y"]),
                    "angle": str(applied["angle"]),
                },
            )
        else:
            applied = {
                "blur_type": "linear",
                "length": float(length),
                "angle": float(angle),
            }
            code += _apply_drawable_filter(
                "gegl:motion-blur-linear",
                {
                    "length": str(applied["length"]),
                    "angle": str(applied["angle"]),
                },
            )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_motion_blur",
                message=f"{applied['blur_type'].title()} motion blur applied",
                data=applied,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_motion_blur", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_unsharp_mask(
        amount: float = 0.5,
        radius: float = 3.0,
        threshold: float = 0.0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Sharpen a layer using unsharp mask.

        Notes:
            Use this tool when enhancing image detail, sharpening after resize,
            recovering slightly out-of-focus images.

        Args:
            amount: Sharpening strength (0.0-5.0, typical 0.3-1.0)
            radius: Detail radius in pixels (0.1-120.0, typical 1.0-5.0)
            threshold: Minimum difference threshold (0.0-1.0, higher = less sharpening of subtle detail)
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _filter_preamble(layer_name, layer_index)
        code += _apply_drawable_filter(
            "gegl:unsharp-mask",
            {
                "scale": str(amount),
                "std-dev": str(radius),
                "threshold": str(threshold),
            },
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_unsharp_mask",
                message=f"Unsharp mask applied (amount={amount}, radius={radius})",
                data={"amount": amount, "radius": radius, "threshold": threshold},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_unsharp_mask", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_pixelize(
        block_width: int = 10,
        block_height: int | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply pixelization (mosaic) effect to a layer.

        Notes:
            Use this tool when censoring faces/text, retro pixel art effect, privacy masking.

        Args:
            block_width: Pixel block width (1-1024)
            block_height: Pixel block height. Defaults to block_width for square blocks.
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if block_height is None:
            block_height = block_width

        code = _filter_preamble(layer_name, layer_index)
        code += _apply_drawable_filter(
            "gegl:pixelize",
            {
                "size-x": str(block_width),
                "size-y": str(block_height),
            },
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_pixelize",
                message=f"Pixelized with {block_width}x{block_height} blocks",
                data={"block_width": block_width, "block_height": block_height},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_pixelize", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_edge_detect(
        method: str = "sobel",
        amount: float = 1.0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply edge detection to a layer.

        Notes:
            Use this tool when artistic outlines, finding contours, image analysis,
            creating line-art effects.

        Args:
            method: Detection algorithm — "sobel", "prewitt", "laplace"
            amount: Edge detection strength (0.0-10.0)
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        method = method.lower().strip()
        if method == "laplace":
            gegl_op = "gegl:edge-laplace"
            props = {}
        else:
            gegl_op = "gegl:edge"
            props = {"amount": str(amount)}

        code = _filter_preamble(layer_name, layer_index)
        code += _apply_drawable_filter(gegl_op, props)
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_edge_detect",
                message=f"Edge detection applied ({method})",
                data={"method": method, "amount": amount},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_edge_detect", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_emboss(
        azimuth: float = 315.0,
        elevation: float = 45.0,
        depth: int = 2,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply emboss effect to a layer.

        Creates a raised/carved appearance.

        Args:
            azimuth: Light angle in degrees (0-360, default 315 = upper-left)
            elevation: Light elevation in degrees (0-180)
            depth: Emboss depth (1-100)
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _filter_preamble(layer_name, layer_index)
        code += _apply_drawable_filter(
            "gegl:emboss",
            {
                "azimuth": str(azimuth),
                "elevation": str(elevation),
                "depth": str(depth),
            },
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_emboss",
                message=f"Emboss applied (azimuth={azimuth}°, depth={depth})",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_emboss", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_noise(
        amount: float = 0.2,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Add random noise to a layer.

        Notes:
            Use this tool when adding film grain, texture, or breaking up smooth gradients.

        Args:
            amount: Noise intensity (0.0-1.0)
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _filter_preamble(layer_name, layer_index)
        code += _apply_drawable_filter(
            "gegl:noise-hsv",
            {
                "holdness": "2",
                "value-distance": str(amount),
            },
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_noise",
                message=f"Noise added (amount={amount})",
                data={"amount": amount},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_noise", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_median(
        radius: int = 3,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply median filter (denoise) to a layer.

        Good for removing salt-and-pepper noise while preserving edges.

        Args:
            radius: Filter radius (1-20)
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _filter_preamble(layer_name, layer_index)
        code += _apply_drawable_filter(
            "gegl:median-blur",
            {
                "radius": str(radius),
            },
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_median",
                message=f"Median filter applied (radius={radius})",
                data={"radius": radius},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_median", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_drop_shadow(
        offset_x: float = 4.0,
        offset_y: float = 4.0,
        blur_radius: float = 8.0,
        color: str = "black",
        opacity: float = 60.0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply a drop shadow effect to a layer.

        Creates a shadow behind the layer content.

        Args:
            offset_x: Shadow horizontal offset (positive = right)
            offset_y: Shadow vertical offset (positive = down)
            blur_radius: Shadow blur amount
            color: Shadow color (default "black")
            opacity: Shadow opacity 0-100
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        from gimp_mcp_pro.models.common import Color

        Color(value=color)

        normalized_opacity = max(0.0, min(100.0, opacity)) / 100.0
        code = _filter_preamble(layer_name, layer_index)
        code += _apply_drawable_filter(
            "gegl:dropshadow",
            {
                "x": str(offset_x),
                "y": str(offset_y),
                "radius": str(blur_radius),
                "color": f"Gegl.Color.new({py_literal(color)})",
                "opacity": str(normalized_opacity),
            },
        )
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="apply_drop_shadow",
                message=f"Drop shadow applied (offset {offset_x},{offset_y}, blur {blur_radius})",
                data={
                    "offset_x": offset_x,
                    "offset_y": offset_y,
                    "blur_radius": blur_radius,
                    "color": color,
                    "opacity": normalized_opacity,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_drop_shadow", error=str(e)).model_dump()
