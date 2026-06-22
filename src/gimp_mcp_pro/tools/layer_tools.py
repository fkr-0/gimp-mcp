"""Layer management tools for GIMP MCP Pro."""

from __future__ import annotations

import logging

from gimp_mcp_pro.models.common import OperationResult, py_literal
from gimp_mcp_pro.models.layer import CreateLayerParams
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError
from gimp_mcp_pro.utils.gimp_constants import BLEND_MODE_MAP, FILL_TYPE_MAP

logger = logging.getLogger("gimp_mcp_pro.tools.layer")

LAYER_MASK_TYPE_MAP: dict[str, str] = {
    "white": "Gimp.AddMaskType.WHITE",
    "black": "Gimp.AddMaskType.BLACK",
    "alpha": "Gimp.AddMaskType.ALPHA",
    "alpha_transfer": "Gimp.AddMaskType.ALPHA_TRANSFER",
    "selection": "Gimp.AddMaskType.SELECTION",
    "copy": "Gimp.AddMaskType.COPY",
}


def _layer_lookup_code(layer_name: str | None, layer_index: int | None) -> list[str]:
    """Generate Python code to look up a layer by name or index."""
    code = [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
    ]
    if layer_name is not None:
        code += [
            f"target = image.get_layer_by_name({py_literal(layer_name)})",
            f"if target is None: raise RuntimeError({py_literal(f'Layer {layer_name!r} not found')})",
        ]
    elif layer_index is not None:
        code += [
            "layers = image.get_layers()",
            f"if {layer_index} >= len(layers): raise RuntimeError('Layer index {layer_index} out of range')",
            f"target = layers[{layer_index}]",
        ]
    else:
        code += [
            "sel = image.get_selected_layers()",
            "if not sel: raise RuntimeError('No active layer')",
            "target = sel[0]",
        ]
    return code


def register_layer_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all layer management tools with the MCP server."""

    @mcp.tool()
    async def create_layer(
        name: str = "New Layer",
        opacity: float = 100.0,
        blend_mode: str = "normal",
        fill: str = "transparent",
        has_alpha: bool = True,
        position: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> ToolResult:
        """Create a new layer in the active image.

        Notes:
            Use this tool before drawing new elements. Professional workflows use
            separate layers for background, main subject, details, etc.

        Notes:
            Best practice: Create layers BEFORE drawing. Plan your layer structure:
            background -> body -> head -> details -> texture.

        Args:
            name: Layer name (e.g., "Background", "Eyes", "Shadow")
            opacity: Layer opacity 0-100 (100 = fully opaque)
            blend_mode: Blend mode — "normal", "multiply", "screen", "overlay", etc.
            fill: Initial fill — "transparent", "white", "foreground", "background"
            has_alpha: Whether layer has transparency (usually True)
            position: Stack position (0 = top of stack)
            width: Layer width (defaults to image width)
            height: Layer height (defaults to image height)

        Returns:
            Operation result with layer info.
        """
        params = CreateLayerParams(
            name=name,
            opacity=opacity,
            blend_mode=blend_mode,
            fill=fill,
            has_alpha=has_alpha,
            position=position,
            width=width,
            height=height,
            image_id=None,
        )
        mode_expr = BLEND_MODE_MAP.get(params.blend_mode, "Gimp.LayerMode.NORMAL")
        fill_expr = FILL_TYPE_MAP.get(params.fill, "Gimp.FillType.TRANSPARENT")
        img_type = "Gimp.ImageType.RGBA_IMAGE" if params.has_alpha else "Gimp.ImageType.RGB_IMAGE"
        w = f"{params.width}" if params.width else "image.get_width()"
        h = f"{params.height}" if params.height else "image.get_height()"

        code = [
            "from gi.repository import Gimp, Gegl",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open in GIMP')",
            "image = images[0]",
            f"layer = Gimp.Layer.new(image, {py_literal(params.name)}, {w}, {h}, "
            f"{img_type}, {params.opacity}, {mode_expr})",
            f"image.insert_layer(layer, None, {params.position})",
            f"Gimp.Drawable.edit_fill(layer, {fill_expr})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="create_layer",
                message=f"Created layer '{params.name}'",
                data={
                    "name": params.name,
                    "opacity": params.opacity,
                    "blend_mode": params.blend_mode.value,
                    "position": params.position,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="create_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def list_layers() -> ToolResult:
        """List all layers in the active image with their properties.

        Notes:
            Use this tool before drawing (to find the right layer), when debugging
            visual issues, or to understand image structure.

        Returns:
            Layer list with name, visibility, opacity, blend mode, dimensions.
        """
        code = [
            "import json",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "layers = image.get_layers()",
            "result = []",
            "for i, layer in enumerate(layers):\n"
            "    info = {'index': i, 'name': layer.get_name(), 'visible': layer.get_visible(),\n"
            "            'opacity': layer.get_opacity(), 'width': layer.get_width(),\n"
            "            'height': layer.get_height(), 'has_alpha': layer.has_alpha()}\n"
            "    try: info['blend_mode'] = str(layer.get_mode())\n"
            "    except: info['blend_mode'] = 'unknown'\n"
            "    result.append(info)",
            "print(json.dumps(result))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            layers_data = []
            for out in result.get("results", []):
                if out and out.strip():
                    try:
                        layers_data = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="list_layers",
                message=f"Found {len(layers_data)} layer(s)",
                data={"layers": layers_data, "count": len(layers_data)},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="list_layers", error=str(e)).model_dump()

    @mcp.tool()
    async def set_active_layer(
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Set which layer is active (the one drawing tools operate on).

        Notes:
            Use this tool before any drawing or editing operation, switch to the
            correct layer. Drawing on the wrong layer is the most common mistake.

        Args:
            layer_name: Layer name to activate (e.g., "Background")
            layer_index: Layer index (0 = topmost). Alternative to name.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if layer_name is None and layer_index is None:
            return OperationResult.fail(
                operation="set_active_layer",
                error="Must specify either layer_name or layer_index",
            ).model_dump()

        code = _layer_lookup_code(layer_name, layer_index) + [
            "image.set_selected_layers([target])",
            "Gimp.displays_flush()",
            "print(target.get_name())",
        ]
        try:
            result = await bridge.async_execute_python(code)
            name = ""
            for out in result.get("results", []):
                if out and out.strip():
                    name = out.strip()
            return OperationResult.ok(
                operation="set_active_layer",
                message=f"Active layer set to '{name}'",
                data={"layer_name": name},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_active_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def delete_layer(
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Delete a layer from the active image.

        Args:
            layer_name: Name of layer to delete.
            layer_index: Index of layer to delete (0 = topmost).

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if layer_name is None and layer_index is None:
            return OperationResult.fail(
                operation="delete_layer", error="Must specify layer_name or layer_index"
            ).model_dump()

        code = _layer_lookup_code(layer_name, layer_index) + [
            "name = target.get_name()",
            "image.remove_layer(target)",
            "Gimp.displays_flush()",
            "print(name)",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="delete_layer", message="Layer deleted"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="delete_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def set_layer_opacity(
        opacity: float,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Set a layer's opacity.

        Args:
            opacity: Opacity 0-100 (0 = fully transparent, 100 = fully opaque)
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if not 0.0 <= opacity <= 100.0:
            return OperationResult.fail(
                operation="set_layer_opacity", error=f"Opacity must be 0-100, got {opacity}"
            ).model_dump()

        code = _layer_lookup_code(layer_name, layer_index) + [
            f"target.set_opacity({opacity})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="set_layer_opacity",
                message=f"Layer opacity set to {opacity}%",
                data={"opacity": opacity},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_layer_opacity", error=str(e)).model_dump()

    @mcp.tool()
    async def set_layer_visibility(
        visible: bool,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Show or hide a layer.

        Args:
            visible: True to show, False to hide.
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _layer_lookup_code(layer_name, layer_index) + [
            f"target.set_visible({visible})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            state = "visible" if visible else "hidden"
            return OperationResult.ok(
                operation="set_layer_visibility",
                message=f"Layer is now {state}",
                data={"visible": visible},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_layer_visibility", error=str(e)).model_dump()

    @mcp.tool()
    async def set_layer_mode(
        blend_mode: str,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Set a layer's blend mode (normal, multiply, screen, overlay, etc.).

        Args:
            blend_mode: Blend mode name — "normal", "dissolve", "multiply",
                "screen", "overlay", "soft_light", "hard_light", "color_dodge",
                "color_burn", "darken_only", "lighten_only", "difference",
                "exclusion", "hue", "saturation", "color", "luminosity",
                "addition", "subtract", "grain_extract", "grain_merge", "divide"
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        from gimp_mcp_pro.models.common import BlendMode as _BM

        try:
            bm = _BM(blend_mode)
        except ValueError:
            valid = ", ".join(m.value for m in _BM)
            return OperationResult.fail(
                operation="set_layer_mode",
                error=f"Unknown blend mode '{blend_mode}'. Valid: {valid}",
            ).model_dump()

        mode_expr = BLEND_MODE_MAP.get(bm, "Gimp.LayerMode.NORMAL")
        code = _layer_lookup_code(layer_name, layer_index) + [
            f"target.set_mode({mode_expr})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="set_layer_mode",
                message=f"Layer blend mode set to '{blend_mode}'",
                data={"blend_mode": blend_mode},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_layer_mode", error=str(e)).model_dump()

    @mcp.tool()
    async def duplicate_layer(
        layer_name: str | None = None,
        layer_index: int | None = None,
        new_name: str | None = None,
    ) -> ToolResult:
        """Duplicate a layer.

        Args:
            layer_name: Source layer name.
            layer_index: Source layer index. Uses active layer if neither specified.
            new_name: Name for the duplicate. Defaults to "Copy of <original>".

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _layer_lookup_code(layer_name, layer_index) + [
            "dup = target.copy()",
        ]
        if new_name:
            code.append(f"dup.set_name('{new_name}')")
        else:
            code.append("dup.set_name('Copy of ' + target.get_name())")
        code += [
            "image.insert_layer(dup, None, 0)",
            "Gimp.displays_flush()",
            "print(dup.get_name())",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="duplicate_layer", message="Layer duplicated"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="duplicate_layer", error=str(e)).model_dump()

    @mcp.tool()
    async def merge_visible_layers() -> ToolResult:
        """Merge all visible layers into one.

        Notes:
            Use this tool when consolidate visible work while preserving hidden layers.

        Warnings:
            Destructive operation — consider using undo groups.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="merge_visible_layers", message="Visible layers merged"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="merge_visible_layers", error=str(e)).model_dump()


    @mcp.tool()
    async def add_layer_mask(
        mask_type: str = "white",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Add a layer mask to a layer.

        Args:
            mask_type: "white", "black", "alpha", "alpha_transfer", "selection", or "copy".
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result with mask metadata.
        """
        mask_expr = LAYER_MASK_TYPE_MAP.get(mask_type)
        if mask_expr is None:
            valid = ", ".join(sorted(LAYER_MASK_TYPE_MAP))
            return OperationResult.fail(
                operation="add_layer_mask",
                error=f"Unknown mask_type '{mask_type}'. Valid: {valid}",
            ).model_dump()
        code = _layer_lookup_code(layer_name, layer_index) + [
            "if target.get_mask() is not None: raise RuntimeError('Layer already has a mask')",
            f"mask = target.create_mask({mask_expr})",
            "if mask is None: raise RuntimeError('Could not create layer mask')",
            "if not target.add_mask(mask): raise RuntimeError('Could not add layer mask')",
            "Gimp.displays_flush()",
            "print(target.get_name())",
        ]
        try:
            result = await bridge.async_execute_python(code)
            name = layer_name or ""
            for out in result.get("results", []):
                if out and str(out).strip():
                    name = str(out).strip()
            return OperationResult.ok(
                operation="add_layer_mask",
                message=f"Added {mask_type} layer mask",
                data={"layer_name": name or None, "mask_type": mask_type},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="add_layer_mask", error=str(e)).model_dump()

    @mcp.tool()
    async def get_layer_mask_info(
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Get layer mask status for a layer.

        Args:
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with layer mask status metadata.
        """
        code = _layer_lookup_code(layer_name, layer_index) + [
            "import json",
            "mask = target.get_mask()",
            "info = {'layer_name': target.get_name(), 'has_mask': mask is not None}",
            "if mask is not None:\n"
            "    info.update({'mask_name': mask.get_name(), 'edit_mask': target.get_edit_mask(),\n"
            "                 'show_mask': target.get_show_mask(), 'apply_mask': target.get_apply_mask()})",
            "print(json.dumps(info))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            info: dict[str, object] = {}
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        info = _json.loads(str(out).strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="get_layer_mask_info",
                message="Layer has a mask" if info.get("has_mask") else "Layer has no mask",
                data=info,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_layer_mask_info", error=str(e)).model_dump()

    @mcp.tool()
    async def set_layer_mask_state(
        edit_mask: bool | None = None,
        show_mask: bool | None = None,
        apply_mask: bool | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Set layer mask editing/display/apply flags.

        Args:
            edit_mask: If True, painting/editing targets the mask.
            show_mask: If True, display the mask itself.
            apply_mask: If True, layer renders with the mask applied.
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with the updated mask state metadata.
        """
        if edit_mask is None and show_mask is None and apply_mask is None:
            return OperationResult.fail(
                operation="set_layer_mask_state",
                error="Specify at least one of edit_mask, show_mask, or apply_mask",
            ).model_dump()
        code = _layer_lookup_code(layer_name, layer_index) + [
            "if target.get_mask() is None: raise RuntimeError('Layer has no mask')",
        ]
        if edit_mask is not None:
            code.append(f"target.set_edit_mask({edit_mask})")
        if show_mask is not None:
            code.append(f"target.set_show_mask({show_mask})")
        if apply_mask is not None:
            code.append(f"target.set_apply_mask({apply_mask})")
        code += ["Gimp.displays_flush()"]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="set_layer_mask_state",
                message="Layer mask state updated",
                data={"edit_mask": edit_mask, "show_mask": show_mask, "apply_mask": apply_mask},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_layer_mask_state", error=str(e)).model_dump()

    @mcp.tool()
    async def remove_layer_mask(
        apply: bool = False,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Remove a layer mask, optionally applying it first.

        Args:
            apply: True applies the mask to the layer; False discards it.
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with removal/apply status metadata.
        """
        mode_expr = "Gimp.MaskApplyMode.APPLY" if apply else "Gimp.MaskApplyMode.DISCARD"
        code = _layer_lookup_code(layer_name, layer_index) + [
            "if target.get_mask() is None: raise RuntimeError('Layer has no mask')",
            f"target.remove_mask({mode_expr})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="remove_layer_mask",
                message="Layer mask applied and removed" if apply else "Layer mask discarded",
                data={"applied": apply},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="remove_layer_mask", error=str(e)).model_dump()

    @mcp.tool()
    async def add_alpha_channel(
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Add an alpha (transparency) channel to a layer.

        Notes:
            Use this tool before using transparent fills or edit_clear on a layer
            that was created without alpha (e.g., the default Background layer).

        Args:
            layer_name: Target layer by name.
            layer_index: Target layer by index. Uses active layer if neither specified.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _layer_lookup_code(layer_name, layer_index) + [
            "if not target.has_alpha():\n    target.add_alpha()",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="add_alpha_channel", message="Alpha channel added"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="add_alpha_channel", error=str(e)).model_dump()
