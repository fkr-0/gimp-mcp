"""Layer management tools for GIMP MCP Pro."""

from __future__ import annotations

import logging
from typing import Any

from gimp_mcp_pro.models.common import BlendMode, OperationResult, SelectionOp, py_literal
from gimp_mcp_pro.models.layer import CreateLayerParams
from gimp_mcp_pro.tools.native_backend import SUPPORTED_CHANNEL_ACTIONS, execute_json_tool
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError
from gimp_mcp_pro.utils.gimp_constants import BLEND_MODE_MAP, FILL_TYPE_MAP, SELECTION_OP_MAP

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


def _selection_op_expr(operation: str) -> str:
    """Convert selection operation text into a GIMP ChannelOps expression."""
    return SELECTION_OP_MAP.get(SelectionOp(operation), "Gimp.ChannelOps.REPLACE")


def _group_lookup_code(
    group_name: str | None,
    group_index: int | None,
    *,
    variable: str = "group",
) -> list[str]:
    """Generate Python code to look up a group layer by name or index."""
    if group_name is not None:
        return [
            f"{variable} = image.get_layer_by_name({py_literal(group_name)})",
            f"if {variable} is None or not {variable}.is_group(): "
            f"raise RuntimeError({py_literal(f'Layer group {group_name!r} not found')})",
        ]
    if group_index is not None:
        return [
            "groups = [layer for layer in image.get_layers() if layer.is_group()]",
            f"if {group_index} >= len(groups): raise RuntimeError('Layer group index {group_index} out of range')",
            f"{variable} = groups[{group_index}]",
        ]
    return [f"{variable} = None"]


def _channel_lookup_code(channel_name: str | None, channel_index: int | None) -> list[str]:
    """Generate Python code to look up a channel by name or index."""
    code = [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
    ]
    if channel_name is not None:
        code += [
            f"target = image.get_channel_by_name({py_literal(channel_name)})",
            f"if target is None: raise RuntimeError({py_literal(f'Channel {channel_name!r} not found')})",
        ]
    elif channel_index is not None:
        code += [
            "channels = image.get_channels()",
            f"if {channel_index} >= len(channels): raise RuntimeError('Channel index {channel_index} out of range')",
            f"target = channels[{channel_index}]",
        ]
    else:
        code += [
            "channels = image.get_channels()",
            "if not channels: raise RuntimeError('No channels available')",
            "target = channels[0]",
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
        activate: bool = True,
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
            activate: If True (default), make the new layer active so drawing/fill tools target it.

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

        lifecycle_lines = [
            "# __gimp_mcp_layer_create_lifecycle__",
            "layer = None",
            "inserted_layer = False",
            "try:",
            f"    layer = Gimp.Layer.new(image, {py_literal(params.name)}, {w}, {h}, {img_type}, {params.opacity}, {mode_expr})",
            "    if layer is None: raise RuntimeError('Could not create layer')",
            f"    image.insert_layer(layer, None, {params.position})",
            "    inserted_layer = True",
            f"    Gimp.Drawable.edit_fill(layer, {fill_expr})",
            f"    if {activate!r}: image.set_selected_layers([layer])",
            "except Exception:",
            "    try:",
            "        if inserted_layer and layer is not None:",
            "            image.remove_layer(layer)",
            "    except Exception:",
            "        pass",
            "    raise",
            "finally:",
            "    try:",
            "        del layer",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
        ]
        code = [
            "from gi.repository import Gimp, Gegl",
            "import gc",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open in GIMP')",
            "image = images[0]",
            "\n".join(lifecycle_lines),
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
                    "active": activate,
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

        lifecycle_lines = [
            "# __gimp_mcp_layer_active_lifecycle__",
            "previous_selected_layers = image.get_selected_layers()",
            "try:",
            "    image.set_selected_layers([target])",
            "    result_name = target.get_name()",
            "except Exception:",
            "    try:",
            "        image.set_selected_layers(previous_selected_layers)",
            "    except Exception:",
            "        pass",
            "    raise",
            "finally:",
            "    gc.collect()",
        ]
        code = (
            ["import gc"]
            + _layer_lookup_code(layer_name, layer_index)
            + [
                "\n".join(lifecycle_lines),
                "Gimp.displays_flush()",
                "print(result_name)",
            ]
        )
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
            "# __gimp_mcp_layer_delete_lifecycle__",
            "layers = image.get_layers()",
            "if len(layers) <= 1: raise RuntimeError('Cannot delete the only layer')",
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

        lifecycle_lines = [
            "# __gimp_mcp_layer_opacity_lifecycle__",
            "previous_opacity = target.get_opacity()",
            "try:",
            f"    target.set_opacity({opacity})",
            "except Exception:",
            "    try:",
            "        target.set_opacity(previous_opacity)",
            "    except Exception:",
            "        pass",
            "    raise",
            "finally:",
            "    gc.collect()",
        ]
        code = (
            ["import gc"]
            + _layer_lookup_code(layer_name, layer_index)
            + [
                "\n".join(lifecycle_lines),
                "Gimp.displays_flush()",
            ]
        )
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
        try:
            bm = BlendMode(blend_mode)
        except ValueError:
            valid = ", ".join(m.value for m in BlendMode)
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
    async def set_layer_blend_mode(
        blend_mode: str,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Alias for set_layer_mode with discoverable blend-mode naming."""
        try:
            bm = BlendMode(blend_mode)
        except ValueError:
            valid = ", ".join(m.value for m in BlendMode)
            return OperationResult.fail(
                operation="set_layer_blend_mode",
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
                operation="set_layer_blend_mode",
                message=f"Layer blend mode set to '{blend_mode}'",
                data={"blend_mode": blend_mode},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_layer_blend_mode", error=str(e)).model_dump()

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
        lifecycle_lines = [
            "# __gimp_mcp_layer_duplicate_lifecycle__",
            "dup = None",
            "inserted_duplicate = False",
            "try:",
            "    dup = target.copy()",
            "    if dup is None: raise RuntimeError('Could not duplicate layer')",
        ]
        if new_name:
            lifecycle_lines.append(f"    dup.set_name({py_literal(new_name)})")
        else:
            lifecycle_lines.append("    dup.set_name('Copy of ' + target.get_name())")
        lifecycle_lines += [
            "    image.insert_layer(dup, None, 0)",
            "    inserted_duplicate = True",
            "    result_name = dup.get_name()",
            "except Exception:",
            "    try:",
            "        if inserted_duplicate and dup is not None:",
            "            image.remove_layer(dup)",
            "    except Exception:",
            "        pass",
            "    raise",
            "finally:",
            "    try:",
            "        del dup",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
        ]
        code = (
            ["import gc"]
            + _layer_lookup_code(layer_name, layer_index)
            + [
                "\n".join(lifecycle_lines),
                "Gimp.displays_flush()",
                "print(result_name)",
            ]
        )
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
        lifecycle_lines = [
            "# __gimp_mcp_layer_merge_lifecycle__",
            "visible_layers = [layer for layer in image.get_layers() if layer.get_visible()]",
            "if len(visible_layers) < 2: raise RuntimeError('Need at least two visible layers to merge')",
            "undo_started = False",
            "try:",
            "    image.undo_group_start()",
            "    undo_started = True",
            "    image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)",
            "finally:",
            "    try:",
            "        if undo_started:",
            "            image.undo_group_end()",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
        ]
        code = [
            "import gc",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "\n".join(lifecycle_lines),
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
    async def new_layer_from_visible(
        name: str = "Visible",
        position: int = 0,
        activate: bool = True,
    ) -> ToolResult:
        """Create a new layer from the current visible composite without merging originals."""
        lifecycle_lines = [
            "# __gimp_mcp_layer_new_from_visible_lifecycle__",
            f"layer = Gimp.Layer.new_from_visible(image, image, {py_literal(name)})",
            "if layer is None: raise RuntimeError('Could not create layer from visible')",
            f"image.insert_layer(layer, None, {position})",
            f"if {activate!r}: image.set_selected_layers([layer])",
            "result_name = layer.get_name()",
        ]
        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "\n".join(lifecycle_lines),
            "Gimp.displays_flush()",
            "print(result_name)",
        ]
        try:
            result = await bridge.async_execute_python(code)
            layer_name = name
            for out in result.get("results", []):
                if out and str(out).strip():
                    layer_name = str(out).strip()
            return OperationResult.ok(
                operation="new_layer_from_visible",
                message=f"Created layer from visible '{layer_name}'",
                data={"name": layer_name, "position": position, "active": activate},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="new_layer_from_visible", error=str(e)).model_dump()

    @mcp.tool()
    async def merge_down(
        layer_name: str | None = None,
        layer_index: int | None = None,
        merge_type: str = "clip_to_image",
    ) -> ToolResult:
        """Merge a layer down into the layer below it."""
        merge_types = {
            "expand_as_necessary": "Gimp.MergeType.EXPAND_AS_NECESSARY",
            "clip_to_image": "Gimp.MergeType.CLIP_TO_IMAGE",
            "clip_to_bottom_layer": "Gimp.MergeType.CLIP_TO_BOTTOM_LAYER",
        }
        merge_expr = merge_types.get(merge_type)
        if merge_expr is None:
            return OperationResult.fail(
                operation="merge_down",
                error=f"Unknown merge_type '{merge_type}'. Valid: {', '.join(sorted(merge_types))}",
            ).model_dump()
        code = _layer_lookup_code(layer_name, layer_index) + [
            f"merged = image.merge_down(target, {merge_expr})",
            "if merged is None: raise RuntimeError('Could not merge layer down')",
            "image.set_selected_layers([merged])",
            "Gimp.displays_flush()",
            "print(merged.get_name())",
        ]
        try:
            result = await bridge.async_execute_python(code)
            merged_name = ""
            for out in result.get("results", []):
                if out and str(out).strip():
                    merged_name = str(out).strip()
            return OperationResult.ok(
                operation="merge_down",
                message="Layer merged down",
                data={"merged_layer_name": merged_name or None, "merge_type": merge_type},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="merge_down", error=str(e)).model_dump()

    @mcp.tool()
    async def copy_layer_alpha_to_mask(
        source_layer_name: str | None = None,
        source_layer_index: int | None = None,
        target_layer_name: str | None = None,
        target_layer_index: int | None = None,
        replace_existing: bool = True,
    ) -> ToolResult:
        """Copy a source layer's alpha silhouette into the target layer mask."""
        if source_layer_name is None and source_layer_index is None:
            return OperationResult.fail(
                operation="copy_layer_alpha_to_mask",
                error="Specify source_layer_name or source_layer_index",
            ).model_dump()
        if target_layer_name is None and target_layer_index is None:
            return OperationResult.fail(
                operation="copy_layer_alpha_to_mask",
                error="Specify target_layer_name or target_layer_index",
            ).model_dump()
        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
        ]
        code += _layer_lookup_code(source_layer_name, source_layer_index)
        code += ["source = target"]
        code += _layer_lookup_code(target_layer_name, target_layer_index)
        code += [
            "saved_selection = Gimp.Selection.save(image)",
            "undo_started = False",
            "try:",
            "    image.undo_group_start(); undo_started = True",
            "    image.select_item(Gimp.ChannelOps.REPLACE, source)",
            "    existing_mask = target.get_mask()",
            f"    if existing_mask is not None and {replace_existing!r}: target.remove_mask(Gimp.MaskApplyMode.DISCARD)",
            "    elif existing_mask is not None: raise RuntimeError('Target layer already has a mask')",
            "    mask = target.create_mask(Gimp.AddMaskType.SELECTION)",
            "    if mask is None: raise RuntimeError('Could not create layer mask from source alpha')",
            "    if not target.add_mask(mask): raise RuntimeError('Could not add layer mask')",
            "finally:",
            "    try:",
            "        if saved_selection is not None: image.select_item(Gimp.ChannelOps.REPLACE, saved_selection)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        if saved_selection is not None: image.remove_channel(saved_selection)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        if undo_started: image.undo_group_end()",
            "    except Exception:",
            "        pass",
            "Gimp.displays_flush()",
            "print(source.get_name() + ' -> ' + target.get_name())",
        ]
        try:
            result = await bridge.async_execute_python(code)
            mapping = ""
            for out in result.get("results", []):
                if out and str(out).strip():
                    mapping = str(out).strip()
            return OperationResult.ok(
                operation="copy_layer_alpha_to_mask",
                message="Copied source layer alpha into target mask",
                data={"mapping": mapping or None, "replace_existing": replace_existing},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="copy_layer_alpha_to_mask", error=str(e)).model_dump()

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
    async def create_layer_group(
        name: str = "Group",
        position: int = 0,
        parent_group_name: str | None = None,
        parent_group_index: int | None = None,
    ) -> ToolResult:
        """Create a group layer in the active image.

        Args:
            name: Name for the new group layer.
            position: Stack position inside the image or parent group.
            parent_group_name: Optional parent group layer name.
            parent_group_index: Optional parent group index when name is not supplied.

        Returns:
            Operation result dictionary with created group metadata.
        """
        if parent_group_name is not None and parent_group_index is not None:
            return OperationResult.fail(
                operation="create_layer_group",
                error="Specify only one of parent_group_name or parent_group_index",
            ).model_dump()
        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
        ]
        code += _group_lookup_code(parent_group_name, parent_group_index, variable="parent")
        code += [
            f"group = Gimp.GroupLayer.new(image, {py_literal(name)})",
            "if group is None: raise RuntimeError('Could not create layer group')",
            f"if not image.insert_layer(group, parent, {position}): raise RuntimeError('Could not insert layer group')",
            "image.set_selected_layers([group])",
            "Gimp.displays_flush()",
            "print(group.get_name())",
        ]
        try:
            result = await bridge.async_execute_python(code)
            group_name = name
            for out in result.get("results", []):
                if out and str(out).strip():
                    group_name = str(out).strip()
            return OperationResult.ok(
                operation="create_layer_group",
                message=f"Created layer group '{group_name}'",
                data={
                    "name": group_name,
                    "position": position,
                    "parent_group_name": parent_group_name,
                    "parent_group_index": parent_group_index,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="create_layer_group", error=str(e)).model_dump()

    @mcp.tool()
    async def move_layer_to_group(
        layer_name: str | None = None,
        layer_index: int | None = None,
        group_name: str | None = None,
        group_index: int | None = None,
        position: int = 0,
    ) -> ToolResult:
        """Move a layer or group under a target layer group.

        Args:
            layer_name: Layer name to move.
            layer_index: Layer index to move. Uses active layer if neither layer selector is supplied.
            group_name: Destination group layer name.
            group_index: Destination group index when name is not supplied.
            position: Position inside the destination group.

        Returns:
            Operation result dictionary with move metadata.
        """
        if group_name is None and group_index is None:
            return OperationResult.fail(
                operation="move_layer_to_group",
                error="Specify group_name or group_index",
            ).model_dump()
        if group_name is not None and group_index is not None:
            return OperationResult.fail(
                operation="move_layer_to_group",
                error="Specify only one of group_name or group_index",
            ).model_dump()
        code = _layer_lookup_code(layer_name, layer_index)
        code += _group_lookup_code(group_name, group_index, variable="group")
        code += [
            f"if not image.reorder_item(target, group, {position}): raise RuntimeError('Could not move layer into group')",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="move_layer_to_group",
                message="Layer moved into group",
                data={
                    "layer_name": layer_name,
                    "layer_index": layer_index,
                    "group_name": group_name,
                    "group_index": group_index,
                    "position": position,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="move_layer_to_group", error=str(e)).model_dump()

    @mcp.tool()
    async def list_channels() -> ToolResult:
        """List custom channels in the active image.

        Returns:
            Operation result dictionary with channel names, indexes, visibility, and total count.
        """
        code = [
            "import json",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "channels = image.get_channels()",
            "result = []",
            "for i, channel in enumerate(channels):\n"
            "    info = {'index': i, 'id': channel.get_id(), 'name': channel.get_name(),\n"
            "            'visible': channel.get_visible()}\n"
            "    try: info['opacity'] = channel.get_opacity()\n"
            "    except Exception: info['opacity'] = None\n"
            "    result.append(info)",
            "print(json.dumps(result))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            channels_data = []
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        channels_data = _json.loads(str(out).strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="list_channels",
                message=f"Found {len(channels_data)} channel(s)",
                data={"channels": channels_data, "count": len(channels_data)},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="list_channels", error=str(e)).model_dump()

    @mcp.tool()
    async def save_selection_to_channel(name: str = "Selection") -> ToolResult:
        """Save the current selection mask as a named custom channel.

        Args:
            name: Name for the created channel.

        Returns:
            Operation result dictionary with created channel metadata.
        """
        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "channel = Gimp.Selection.save(image)",
            "if channel is None: raise RuntimeError('Could not save selection to channel')",
            f"channel.set_name({py_literal(name)})",
            "Gimp.displays_flush()",
            "print(channel.get_name())",
        ]
        try:
            result = await bridge.async_execute_python(code)
            channel_name = name
            for out in result.get("results", []):
                if out and str(out).strip():
                    channel_name = str(out).strip()
            return OperationResult.ok(
                operation="save_selection_to_channel",
                message=f"Saved selection to channel '{channel_name}'",
                data={"name": channel_name},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="save_selection_to_channel", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def channel_to_selection(
        channel_name: str | None = None,
        channel_index: int | None = None,
        operation: str = "replace",
    ) -> ToolResult:
        """Convert a custom channel into the current selection.

        Args:
            channel_name: Channel name to select from.
            channel_index: Channel index to select from. Uses the first channel if neither selector is supplied.
            operation: Selection operation: "replace", "add", "subtract", or "intersect".

        Returns:
            Operation result dictionary with channel-to-selection metadata.
        """
        try:
            op_expr = _selection_op_expr(operation)
        except ValueError:
            return OperationResult.fail(
                operation="channel_to_selection",
                error="operation must be one of: replace, add, subtract, intersect",
            ).model_dump()
        code = ["from gi.repository import Gimp"] + _channel_lookup_code(
            channel_name, channel_index
        )
        code += [
            f"image.select_item({op_expr}, target)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="channel_to_selection",
                message=f"Converted channel to selection using {operation}",
                data={
                    "channel_name": channel_name,
                    "channel_index": channel_index,
                    "operation": operation,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="channel_to_selection", error=str(e)).model_dump()

    @mcp.tool()
    async def create_visual_annotation_layer(
        annotations: list[dict[str, object]],
        layer_name: str | None = None,
        temporary: bool = True,
    ) -> ToolResult:
        """Create an MCP-tagged temporary visual annotation layer.

        Args:
            annotations: Typed annotation definitions such as boxes, arrows, or labels.
            layer_name: Optional annotation layer name.
            temporary: Mark the layer as a removable MCP annotation.

        Returns:
            Operation result with annotation layer metadata.
        """
        name = layer_name or "MCP Annotations"
        code = [
            "from gi.repository import Gimp, Gegl",
            "import gc",
            "import json",
            "# __gimp_mcp_create_visual_annotation_layer__",
            "# __gimp_mcp_layer_annotation_lifecycle__",
            f"annotations = {py_literal(annotations)}",
            f"layer_name = {py_literal(name)}",
            f"temporary = {temporary!r}",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "layer = None",
            "parasite = None",
            "try:",
            "    layer = Gimp.Layer.new(image, layer_name, image.get_width(), image.get_height(), Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.NORMAL)",
            "    if layer is None: raise RuntimeError('Could not create annotation layer')",
            "    image.insert_layer(layer, None, 0)",
            "    try:",
            "        layer.add_alpha()",
            "    except Exception:",
            "        pass",
            "    parasite = Gimp.Parasite.new('gimp-mcp-annotation', 0, json.dumps({'temporary': temporary, 'annotations': annotations}).encode('utf-8'))",
            "    layer.attach_parasite(parasite)",
            "    for annotation in annotations:",
            "        color = annotation.get('color', '#ff0000')",
            "        Gimp.context_set_foreground(Gegl.Color.new(color))",
            "    annotation_layer_id = int(layer.get_id()) if hasattr(layer, 'get_id') else None",
            "    result = {'annotation_layer_id': annotation_layer_id, 'layer_name': layer_name, 'temporary': temporary, 'annotation_count': len(annotations), 'tag': 'gimp-mcp-annotation'}",
            "except Exception:",
            "    try:",
            "        if layer is not None:",
            "            image.remove_layer(layer)",
            "    except Exception:",
            "        pass",
            "    raise",
            "finally:",
            "    try:",
            "        del parasite",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
            "Gimp.displays_flush()",
            "print(json.dumps(result, sort_keys=True))",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="create_visual_annotation_layer",
                message=f"Created annotation layer '{name}'",
                data={
                    "layer_name": name,
                    "annotation_count": len(annotations),
                    "temporary": temporary,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="create_visual_annotation_layer", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def remove_visual_annotations(
        annotation_layer_ids: list[int] | None = None,
        remove_all_mcp_annotations: bool = False,
    ) -> ToolResult:
        """Remove MCP-managed annotation layers only.

        Args:
            annotation_layer_ids: Explicit annotation layer IDs to remove.
            remove_all_mcp_annotations: Remove all layers tagged as MCP annotations.

        Returns:
            Operation result with removed layer IDs.
        """
        if not annotation_layer_ids and not remove_all_mcp_annotations:
            return OperationResult.fail(
                operation="remove_visual_annotations",
                error="provide annotation_layer_ids or remove_all_mcp_annotations=true",
            ).model_dump()
        ids = [int(value) for value in (annotation_layer_ids or [])]
        code = [
            "from gi.repository import Gimp",
            "import json",
            "# __gimp_mcp_remove_visual_annotations__",
            f"annotation_layer_ids = {ids!r}",
            f"remove_all_mcp_annotations = {remove_all_mcp_annotations!r}",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "removed_layer_ids = []",
            "for layer in list(image.get_layers()):\n"
            "    layer_id = int(layer.get_id()) if hasattr(layer, 'get_id') else None\n"
            "    layer_name = layer.get_name()\n"
            "    is_mcp_annotation = 'gimp-mcp-annotation' in layer_name.lower() or layer_name.lower().startswith('mcp annotation')\n"
            "    if layer_id in annotation_layer_ids or (remove_all_mcp_annotations and is_mcp_annotation):\n"
            "        image.remove_layer(layer)\n"
            "        removed_layer_ids.append(layer_id)",
            "result = {'removed_layer_ids': removed_layer_ids, 'remove_all_mcp_annotations': remove_all_mcp_annotations, 'tag': 'gimp-mcp-annotation'}",
            "Gimp.displays_flush()",
            "print(json.dumps(result, sort_keys=True))",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="remove_visual_annotations",
                message="Removed visual annotation layers",
                data={
                    "annotation_layer_ids": ids,
                    "remove_all_mcp_annotations": remove_all_mcp_annotations,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="remove_visual_annotations", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def layer_version_stamp(
        target: dict[str, object] | str,
        metadata: dict[str, object],
        merge: bool = True,
    ) -> ToolResult:
        """Attach namespaced MCP provenance metadata to a layer.

        Args:
            target: Layer target reference, commonly {"layer_name": "..."}.
            metadata: Metadata payload to attach.
            merge: Merge with existing MCP metadata where possible.

        Returns:
            Operation result with stamped metadata namespace.
        """
        code = [
            "from gi.repository import Gimp",
            "import gc",
            "import json",
            "# __gimp_mcp_layer_version_stamp__",
            "# __gimp_mcp_layer_version_lifecycle__",
            f"target = {py_literal(target)}",
            f"metadata = {py_literal(metadata)}",
            f"merge = {merge!r}",
            "metadata_namespace = 'gimp-mcp-pro'",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "old_parasite = None",
            "parasite = None",
            "if isinstance(target, dict) and target.get('layer_name'):",
            "    layer = image.get_layer_by_name(target.get('layer_name'))",
            "else:",
            "    selected = image.get_selected_layers()",
            "    layer = selected[0] if selected else None",
            "if layer is None: raise RuntimeError('Target layer not found')",
            "existing_metadata = {}",
            "try:",
            "    if merge:",
            "        try:",
            "            old_parasite = layer.get_parasite(metadata_namespace)",
            "            if old_parasite:",
            "                existing_metadata = json.loads(bytes(old_parasite.get_data()).decode('utf-8'))",
            "        except Exception:",
            "            existing_metadata = {}",
            "    merged_metadata = dict(existing_metadata)",
            "    merged_metadata.update(metadata)",
            "    if old_parasite is not None:",
            "        try:",
            "            layer.detach_parasite(metadata_namespace)",
            "        except Exception:",
            "            pass",
            "    parasite = Gimp.Parasite.new(metadata_namespace, 0, json.dumps(merged_metadata, sort_keys=True).encode('utf-8'))",
            "    layer.attach_parasite(parasite)",
            "    result = {'target': target, 'metadata_namespace': metadata_namespace, 'existing_metadata': existing_metadata, 'metadata': merged_metadata}",
            "finally:",
            "    try:",
            "        del old_parasite",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del parasite",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
            "print(json.dumps(result, sort_keys=True))",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="layer_version_stamp",
                message="Layer version metadata stamped",
                data={
                    "target": target,
                    "metadata_namespace": "gimp-mcp-pro",
                    "metadata": metadata,
                    "merge": merge,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="layer_version_stamp", error=str(e)).model_dump()

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
        lifecycle_lines = [
            "# __gimp_mcp_layer_alpha_lifecycle__",
            "already_had_alpha = target.has_alpha()",
            "try:",
            "    if not already_had_alpha:",
            "        target.add_alpha()",
            "finally:",
            "    gc.collect()",
        ]
        code = (
            ["import gc"]
            + _layer_lookup_code(layer_name, layer_index)
            + [
                "\n".join(lifecycle_lines),
                "Gimp.displays_flush()",
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="add_alpha_channel", message="Alpha channel added"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="add_alpha_channel", error=str(e)).model_dump()

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
        return await execute_json_tool(
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
        return await execute_json_tool(
            bridge,
            operation="manage_channels",
            marker="__gimp_mcp_manage_channels__",
            payload=payload,
            message="Channel management action prepared",
        )
