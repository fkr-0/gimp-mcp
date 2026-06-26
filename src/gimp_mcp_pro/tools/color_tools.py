"""Color adjustment tools for GIMP MCP Pro.

Covers brightness/contrast, levels, curves, hue-saturation, desaturation,
color inversion, threshold, posterize, and color-to-alpha.
"""

from __future__ import annotations

import logging
from typing import Any

from gimp_mcp_pro.bridge import LONG_TIMEOUT
from gimp_mcp_pro.models.common import Color, OperationResult, py_literal
from gimp_mcp_pro.tools.color_backend import (
    MAX_AVERAGE_RADIUS,
    PAINT_RESOURCE_ALIASES,
    _brush_inventory_code,
    _color_adjustment_lifecycle,
    _color_preamble,
    _json_from_bridge,
    _normalise_sample_points,
    _palette_analysis_code,
    _resource_catalog_code,
    _sample_pixels_code,
    _set_paint_context_code,
    _set_paint_resource_code,
)
from gimp_mcp_pro.tools.native_backend import execute_json_tool
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.color")


def register_color_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all color adjustment tools with the MCP server."""

    @mcp.tool()
    async def adjust_brightness_contrast(
        brightness: int = 0,
        contrast: int = 0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust brightness and contrast of a layer.

        Args:
            brightness: Brightness adjustment (-127 to 127, 0 = no change)
            contrast: Contrast adjustment (-127 to 127, 0 = no change)
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        brightness = max(-127, min(127, brightness))
        contrast = max(-127, min(127, contrast))

        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            [
                f"Gimp.Drawable.brightness_contrast(drawable, {brightness / 127.0}, {contrast / 127.0})"
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="adjust_brightness_contrast",
                message=f"Brightness={brightness}, Contrast={contrast}",
                data={"brightness": brightness, "contrast": contrast},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="adjust_brightness_contrast", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def adjust_hue_saturation(
        hue: float = 0.0,
        saturation: float = 0.0,
        lightness: float = 0.0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust hue, saturation, and lightness of a layer.

        Args:
            hue: Hue rotation in degrees (-180 to 180, 0 = no change)
            saturation: Saturation adjustment (-100 to 100, 0 = no change)
            lightness: Lightness adjustment (-100 to 100, 0 = no change)
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        hue = max(-180.0, min(180.0, hue))
        saturation = max(-100.0, min(100.0, saturation))
        lightness = max(-100.0, min(100.0, lightness))

        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            [
                f"Gimp.Drawable.hue_saturation(drawable, Gimp.HueRange.ALL, "
                f"{hue}, {lightness}, {saturation}, 0.0)"
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="adjust_hue_saturation",
                message=f"Hue={hue}°, Saturation={saturation}, Lightness={lightness}",
                data={"hue": hue, "saturation": saturation, "lightness": lightness},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="adjust_hue_saturation", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def adjust_color_balance(
        range: str = "midtones",
        cyan_red: float = 0.0,
        magenta_green: float = 0.0,
        yellow_blue: float = 0.0,
        preserve_luminosity: bool = True,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust shadows, midtones, or highlights color balance for a layer.

        Args:
            range: Tonal range to adjust: "shadows", "midtones", or "highlights".
            cyan_red: Cyan-to-red shift (-100 to 100, 0 = no change).
            magenta_green: Magenta-to-green shift (-100 to 100, 0 = no change).
            yellow_blue: Yellow-to-blue shift (-100 to 100, 0 = no change).
            preserve_luminosity: Keep luminance stable while shifting colors.
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        range_key = range.lower().strip().replace("-", "_")
        range_map = {
            "shadows": "Gimp.TransferMode.SHADOWS",
            "shadow": "Gimp.TransferMode.SHADOWS",
            "midtones": "Gimp.TransferMode.MIDTONES",
            "midtone": "Gimp.TransferMode.MIDTONES",
            "highlights": "Gimp.TransferMode.HIGHLIGHTS",
            "highlight": "Gimp.TransferMode.HIGHLIGHTS",
        }
        transfer_expr = range_map.get(range_key, "Gimp.TransferMode.MIDTONES")
        resolved_range = {
            "Gimp.TransferMode.SHADOWS": "shadows",
            "Gimp.TransferMode.MIDTONES": "midtones",
            "Gimp.TransferMode.HIGHLIGHTS": "highlights",
        }[transfer_expr]

        cyan_red = max(-100.0, min(100.0, cyan_red))
        magenta_green = max(-100.0, min(100.0, magenta_green))
        yellow_blue = max(-100.0, min(100.0, yellow_blue))

        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            [
                "Gimp.Drawable.color_balance("
                f"drawable, {transfer_expr}, {preserve_luminosity}, "
                f"{cyan_red / 100.0}, {magenta_green / 100.0}, {yellow_blue / 100.0})"
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="adjust_color_balance",
                message=(
                    f"Color balance adjusted for {resolved_range}: "
                    f"cyan_red={cyan_red}, magenta_green={magenta_green}, yellow_blue={yellow_blue}"
                ),
                data={
                    "range": resolved_range,
                    "cyan_red": cyan_red,
                    "magenta_green": magenta_green,
                    "yellow_blue": yellow_blue,
                    "preserve_luminosity": preserve_luminosity,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="adjust_color_balance", error=str(e)).model_dump()

    @mcp.tool()
    async def adjust_levels(
        input_low: int = 0,
        input_high: int = 255,
        gamma: float = 1.0,
        output_low: int = 0,
        output_high: int = 255,
        channel: str = "value",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust levels for a layer.

        Notes:
            Use this tool when fine-tuning tonal range, fixing underexposed/overexposed
            images, adjusting individual color channels.

        Args:
            input_low: Input black point (0-255)
            input_high: Input white point (0-255)
            gamma: Midtone gamma (0.1-10.0, 1.0 = no change)
            output_low: Output black point (0-255)
            output_high: Output white point (0-255)
            channel: "value" (all), "red", "green", "blue", "alpha"
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        channel_map = {
            "value": "Gimp.HistogramChannel.VALUE",
            "red": "Gimp.HistogramChannel.RED",
            "green": "Gimp.HistogramChannel.GREEN",
            "blue": "Gimp.HistogramChannel.BLUE",
            "alpha": "Gimp.HistogramChannel.ALPHA",
        }
        ch_expr = channel_map.get(channel.lower(), "Gimp.HistogramChannel.VALUE")

        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            [
                f"Gimp.Drawable.levels(drawable, {ch_expr}, "
                f"{input_low / 255.0}, {input_high / 255.0}, False, "
                f"{gamma}, "
                f"{output_low / 255.0}, {output_high / 255.0}, False)"
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="adjust_levels",
                message=f"Levels adjusted ({channel}): input [{input_low}-{input_high}], gamma {gamma}",
                data={
                    "channel": channel,
                    "input_low": input_low,
                    "input_high": input_high,
                    "gamma": gamma,
                    "output_low": output_low,
                    "output_high": output_high,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="adjust_levels", error=str(e)).model_dump()

    @mcp.tool()
    async def adjust_curves(
        control_points: list[float],
        channel: str = "value",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Adjust curves for a layer.

        Notes:
            Use this tool when fine-grained tonal control, creating custom contrast curves,
            cross-processing effects.

        Args:
            control_points: Flat list of input/output pairs [in1,out1, in2,out2, ...].
                           Values are 0.0-1.0 (0=black, 1=white).
                           Example: [0,0, 0.25,0.2, 0.5,0.6, 0.75,0.85, 1,1] for S-curve.
            channel: "value", "red", "green", "blue", "alpha"
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if len(control_points) < 4 or len(control_points) % 2 != 0:
            return OperationResult.fail(
                operation="adjust_curves",
                error="control_points must have at least 2 pairs (4 values) with even count",
            ).model_dump()

        channel_map = {
            "value": "Gimp.HistogramChannel.VALUE",
            "red": "Gimp.HistogramChannel.RED",
            "green": "Gimp.HistogramChannel.GREEN",
            "blue": "Gimp.HistogramChannel.BLUE",
            "alpha": "Gimp.HistogramChannel.ALPHA",
        }
        ch_expr = channel_map.get(channel.lower(), "Gimp.HistogramChannel.VALUE")

        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            [f"Gimp.Drawable.curves_spline(drawable, {ch_expr}, {control_points})"]
        )
        try:
            await bridge.async_execute_python(code)
            n_points = len(control_points) // 2
            return OperationResult.ok(
                operation="adjust_curves",
                message=f"Curves adjusted ({channel}, {n_points} control points)",
                data={"channel": channel, "num_points": n_points},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="adjust_curves", error=str(e)).model_dump()

    @mcp.tool()
    async def desaturate(
        method: str = "luminosity",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Convert a layer to grayscale while keeping it in RGB mode.

        Args:
            method: Desaturation method —
                    "luminosity" (perceptual, recommended),
                    "average" (equal weight),
                    "lightness" (HSL lightness),
                    "luminance" (linear luminance)
            layer_name: Target layer. Uses active layer if not specified.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        method_map = {
            "luminosity": "Gimp.DesaturateMode.LUMA",
            "luma": "Gimp.DesaturateMode.LUMA",
            "average": "Gimp.DesaturateMode.AVERAGE",
            "lightness": "Gimp.DesaturateMode.LIGHTNESS",
            "luminance": "Gimp.DesaturateMode.LUMINANCE",
            "value": "Gimp.DesaturateMode.VALUE",
        }
        m_expr = method_map.get(method.lower().strip(), "Gimp.DesaturateMode.LUMA")

        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            [f"Gimp.Drawable.desaturate(drawable, {m_expr})"]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="desaturate",
                message=f"Desaturated using {method} method",
                data={"method": method},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="desaturate", error=str(e)).model_dump()

    @mcp.tool()
    async def invert_colors(
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Invert all colors in a layer (negative effect).

        Each pixel's color is replaced with its complement.

        Args:
            layer_name: Target layer by name. Uses the active layer when omitted.
            layer_index: Target layer by index. Uses the active layer when omitted.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            ["Gimp.Drawable.invert(drawable, False)"]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="invert_colors", message="Colors inverted"
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="invert_colors", error=str(e)).model_dump()

    @mcp.tool()
    async def apply_threshold(
        low: int = 128,
        high: int = 255,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Apply threshold — convert to pure black and white.

        Pixels darker than `low` become black, lighter than `high` become white.

        Args:
            low: Lower threshold (0-255, default 128)
            high: Upper threshold (0-255, default 255)
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            [
                f"Gimp.Drawable.threshold(drawable, Gimp.HistogramChannel.VALUE, "
                f"{low / 255.0}, {high / 255.0})"
            ]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="apply_threshold",
                message=f"Threshold applied ({low}-{high})",
                data={"low": low, "high": high},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="apply_threshold", error=str(e)).model_dump()

    @mcp.tool()
    async def posterize(
        levels: int = 4,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Reduce the number of color levels (posterization effect).

        Args:
            levels: Number of color levels per channel (2-256, lower = more dramatic)
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        levels = max(2, min(256, levels))

        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            [f"Gimp.Drawable.posterize(drawable, {levels})"]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="posterize",
                message=f"Posterized to {levels} levels",
                data={"levels": levels},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="posterize", error=str(e)).model_dump()

    @mcp.tool()
    async def color_to_alpha(
        color: str = "white",
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Make a specific color transparent (color to alpha).

        Notes:
            Use this tool when removing backgrounds, making white/black transparent
            for compositing, creating cutouts.

        Args:
            color: Color to make transparent — name, hex, or rgb.
            layer_name: Target layer.
            layer_index: Target layer by index.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        c = Color(value=color)

        lifecycle = [
            "import gc",
            "# __gimp_mcp_color_to_alpha_lifecycle__",
            "df = None",
            "cfg = None",
            "try:",
            "    if not drawable.has_alpha(): drawable.add_alpha()",
            f"    gegl_color = {c.to_gegl_code()}",
            "    df = Gimp.DrawableFilter.new(drawable, 'gegl:color-to-alpha', '')",
            "    cfg = df.get_config()",
            "    cfg.set_property('color', gegl_color)",
            "    drawable.append_filter(df)",
            "    drawable.merge_filter(df)",
            "finally:",
            "    try:",
            "        if df is not None and hasattr(drawable, 'remove_filter'):",
            "            drawable.remove_filter(df)",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del cfg",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del df",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
        ]
        code = _color_preamble(layer_name, layer_index) + [
            "\n".join(lifecycle),
            "Gimp.displays_flush()",
        ]

        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="color_to_alpha",
                message=f"Color '{color}' made transparent",
                data={"color": color},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="color_to_alpha", error=str(e)).model_dump()

    @mcp.tool()
    async def replace_color(
        source_color: str,
        replacement_color: str,
        threshold: float = 15.0,
        sample_merged: bool = False,
        layer_name: str | None = None,
        layer_index: int | None = None,
        preserve_selection: bool = True,
    ) -> ToolResult:
        """Replace pixels matching a source color with a replacement color.

        Args:
            source_color: Color to replace, for example "#ffffff" or "white".
            replacement_color: Color to fill into the selected source-color pixels.
            threshold: Color similarity threshold 0-255.
            sample_merged: If True, use GIMP's sample-merged context while selecting.
            layer_name: Target layer by name. Uses active layer if omitted.
            layer_index: Target layer by index. Uses active layer if omitted.
            preserve_selection: Restore the previous selection after replacement.

        Returns:
            Operation result dictionary with replacement metadata.
        """
        try:
            source = Color(value=source_color)
            replacement = Color(value=replacement_color)
        except ValueError as e:
            return OperationResult.fail(operation="replace_color", error=str(e)).model_dump()
        code = _color_preamble(layer_name, layer_index) + [
            "import gc",
            "previous_foreground = Gimp.context_get_foreground()",
            "previous_sample_threshold = Gimp.context_get_sample_threshold()",
            "previous_sample_merged = Gimp.context_get_sample_merged()",
            f"saved_selection = Gimp.Selection.save(image) if {preserve_selection!r} else None",
            "undo_started = False",
            "try:",
            "    image.undo_group_start(); undo_started = True",
            f"    Gimp.context_set_sample_threshold({threshold / 255.0})",
            f"    Gimp.context_set_sample_merged({sample_merged!r})",
            f"    source_color = {source.to_gegl_code()}",
            f"    replacement_color = {replacement.to_gegl_code()}",
            "    Gimp.context_set_foreground(replacement_color)",
            "    image.select_color(Gimp.ChannelOps.REPLACE, drawable, source_color)",
            "    Gimp.Drawable.edit_fill(drawable, Gimp.FillType.FOREGROUND)",
            "finally:",
            "    try: Gimp.context_set_foreground(previous_foreground)",
            "    except Exception: pass",
            "    try: Gimp.context_set_sample_threshold(previous_sample_threshold)",
            "    except Exception: pass",
            "    try: Gimp.context_set_sample_merged(previous_sample_merged)",
            "    except Exception: pass",
            "    try:",
            "        if saved_selection is not None: image.select_item(Gimp.ChannelOps.REPLACE, saved_selection)",
            "    except Exception: pass",
            "    try:",
            "        if saved_selection is not None: image.remove_channel(saved_selection)",
            "    except Exception: pass",
            "    try:",
            "        if undo_started: image.undo_group_end()",
            "    except Exception: pass",
            "    gc.collect()",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code, timeout=LONG_TIMEOUT)
            return OperationResult.ok(
                operation="replace_color",
                message=f"Replaced {source.value} with {replacement.value}",
                data={
                    "source_color": source.value,
                    "replacement_color": replacement.value,
                    "threshold": threshold,
                    "preserve_selection": preserve_selection,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="replace_color", error=str(e)).model_dump()

    @mcp.tool()
    async def auto_white_balance(
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Automatically adjust white balance (stretch colors).

        Performs automatic levels adjustment to normalize color distribution.

        Args:
            layer_name: Target layer by name. Uses the active layer when omitted.
            layer_index: Target layer by index. Uses the active layer when omitted.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = _color_preamble(layer_name, layer_index) + _color_adjustment_lifecycle(
            ["Gimp.Drawable.levels_stretch(drawable)"]
        )
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="auto_white_balance",
                message="Auto white balance applied",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="auto_white_balance", error=str(e)).model_dump()

    @mcp.tool()
    async def brush_inventory(
        asset_types: list[str] | None = None,
        filter: str | None = None,
        limit: int = 100,
        include_current: bool = True,
    ) -> ToolResult:
        """List paint resources with current-context markers.

        Args:
            asset_types: Resource types to list. Supported: brushes, patterns, gradients, fonts, palettes.
            filter: Optional case-insensitive substring filter.
            limit: Maximum entries per requested resource type.
            include_current: Mark resources currently active in GIMP context.

        Returns:
            Operation result with flat ``assets`` list and current resource map.
        """
        requested = asset_types or ["brushes", "patterns", "gradients", "fonts", "palettes"]
        normalised: list[str] = []
        unsupported: list[str] = []
        for item in requested:
            key = PAINT_RESOURCE_ALIASES.get(str(item).lower().strip().replace("-", "_"))
            if key is None:
                unsupported.append(str(item))
            elif key not in normalised:
                normalised.append(key)
        if unsupported:
            return OperationResult.fail(
                operation="brush_inventory",
                error=f"unsupported asset type(s): {', '.join(unsupported)}",
            ).model_dump()
        limit = max(1, min(1000, int(limit)))
        try:
            result = await bridge.async_execute_python(
                _brush_inventory_code(normalised, filter, limit, include_current)
            )
            data = _json_from_bridge(result)
            data.setdefault("assets", [])
            data.setdefault("current", {})
            return OperationResult.ok(
                operation="brush_inventory",
                message=f"Listed paint inventory for {len(normalised)} asset type(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="brush_inventory", error=str(e)).model_dump()

    @mcp.tool()
    async def set_paint_resource(
        resource_type: str,
        name: str,
    ) -> ToolResult:
        """Set one active paint resource by validated name.

        Args:
            resource_type: One of brush, pattern, gradient, font, or palette.
            name: Resource name to validate and activate.

        Returns:
            Operation result with previous_resource and active_resource read-back.
        """
        key = PAINT_RESOURCE_ALIASES.get(resource_type.lower().strip().replace("-", "_"))
        if key is None:
            return OperationResult.fail(
                operation="set_paint_resource",
                error=f"unsupported paint resource type: {resource_type}",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(_set_paint_resource_code(key, name))
            data = _json_from_bridge(result)
            data.setdefault("previous_resource", {})
            data.setdefault("active_resource", {"type": resource_type, "name": name})
            return OperationResult.ok(
                operation="set_paint_resource",
                message=f"Activated {resource_type} resource {name!r}",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_paint_resource", error=str(e)).model_dump()

    @mcp.tool()
    async def set_paint_context(
        brush: str | None = None,
        size: float | None = None,
        opacity: float | None = None,
        dynamics: str | None = None,
        pattern: str | None = None,
        gradient: str | None = None,
        foreground: str | None = None,
        background: str | None = None,
    ) -> ToolResult:
        """Set multiple paint context fields with validation and read-back.

        Args:
            brush: Optional brush name.
            size: Optional brush size.
            opacity: Optional context opacity percent, 0..100.
            dynamics: Optional dynamics name. Applied with read-back warning because GIMP does not expose list validation.
            pattern: Optional pattern name.
            gradient: Optional gradient name.
            foreground: Optional foreground color.
            background: Optional background color.

        Returns:
            Operation result with previous_context, new_context, and warnings.
        """
        if size is not None and float(size) <= 0:
            return OperationResult.fail(
                operation="set_paint_context",
                error="size must be positive",
            ).model_dump()
        if opacity is not None and (float(opacity) < 0 or float(opacity) > 100):
            return OperationResult.fail(
                operation="set_paint_context",
                error="opacity must be between 0 and 100",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _set_paint_context_code(
                    brush,
                    float(size) if size is not None else None,
                    float(opacity) if opacity is not None else None,
                    dynamics,
                    pattern,
                    gradient,
                    foreground,
                    background,
                )
            )
            data = _json_from_bridge(result)
            data.setdefault("previous_context", {})
            data.setdefault("new_context", {})
            data.setdefault("warnings", [])
            return OperationResult.ok(
                operation="set_paint_context",
                message="Paint context updated",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_paint_context", error=str(e)).model_dump()

    @mcp.tool()
    async def resource_catalog(
        resource_type: str,
        query: str | None = None,
        limit: int = 50,
        include_optional: bool = True,
    ) -> ToolResult:
        """List bounded searchable resources with optional capability notes.

        Args:
            resource_type: Resource kind such as brush, pattern, gradient, font, palette, dynamics, or tool preset.
            query: Optional case-insensitive search string.
            limit: Maximum number of resources to return.
            include_optional: Include structured optional-capability notes for missing resource APIs.

        Returns:
            Operation result with resource records, count, and optional-capability metadata.
        """
        aliases = dict(PAINT_RESOURCE_ALIASES)
        aliases.update(
            {
                "dynamic": "dynamics",
                "dynamics": "dynamics",
                "preset": "tool_presets",
                "tool_preset": "tool_presets",
                "tool_presets": "tool_presets",
            }
        )
        key = aliases.get(resource_type.lower().strip().replace("-", "_"))
        if key is None:
            return OperationResult.fail(
                operation="resource_catalog", error=f"unsupported resource_type: {resource_type}"
            ).model_dump()
        limit = max(1, min(1000, int(limit)))
        try:
            result = await bridge.async_execute_python(
                _resource_catalog_code(key, query, limit, include_optional)
            )
            data = _json_from_bridge(result)
            data.setdefault("resources", [])
            data.setdefault("count", len(data.get("resources", [])))
            return OperationResult.ok(
                operation="resource_catalog",
                message=f"Catalogued {data.get('count', 0)} {key} resource(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="resource_catalog", error=str(e)).model_dump()

    @mcp.tool()
    async def list_gimp_resources(
        resource_type: str = "all",
        limit: int = 100,
    ) -> ToolResult:
        """List available GIMP brushes, patterns, fonts, and gradients.

        Args:
            resource_type: One of "all", "brushes", "patterns", "fonts", or "gradients".
            limit: Maximum number of names returned per resource category.

        Returns:
            Operation result dictionary with status, message, and resource name lists.
        """
        resource_key = resource_type.lower().strip().replace("-", "_")
        aliases = {
            "brush": "brushes",
            "brushes": "brushes",
            "pattern": "patterns",
            "patterns": "patterns",
            "font": "fonts",
            "fonts": "fonts",
            "gradient": "gradients",
            "gradients": "gradients",
            "all": "all",
        }
        selected = aliases.get(resource_key, "all")
        limit = max(1, min(1000, limit))
        resource_calls = {
            "brushes": "Gimp.brushes_get_list('')",
            "patterns": "Gimp.patterns_get_list('')",
            "fonts": "Gimp.fonts_get_list('')",
            "gradients": "Gimp.gradients_get_list('')",
        }
        selected_calls = (
            resource_calls if selected == "all" else {selected: resource_calls[selected]}
        )

        code = [
            "import json",
            "from gi.repository import Gimp",
            "resources = {}",
            (
                "def _resource_names(value):\n"
                "    if isinstance(value, tuple):\n"
                "        for part in reversed(value):\n"
                "            if isinstance(part, (list, tuple)):\n"
                "                value = part\n"
                "                break\n"
                "    names = []\n"
                "    for item in (value or []):\n"
                "        get_name = getattr(item, 'get_name', None)\n"
                "        names.append(str(get_name() if get_name else item))\n"
                "    return names"
            ),
        ]
        for kind, call_expr in selected_calls.items():
            code.append(f"resources[{py_literal(kind)}] = _resource_names({call_expr})[:{limit}]")
        code.append("print(json.dumps(resources))")

        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            resources: dict[str, object] = {}
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        resources = _json.loads(str(out).strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            total = sum(len(v) for v in resources.values() if isinstance(v, list))
            return OperationResult.ok(
                operation="list_gimp_resources",
                message=f"Listed {total} GIMP resources",
                data=resources,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="list_gimp_resources", error=str(e)).model_dump()

    @mcp.tool()
    async def get_colors() -> ToolResult:
        """Get the current foreground and background colors.

        Notes:
            Use this tool before drawing to verify colors are set correctly,
            especially since the user can change them in GIMP's UI at any time.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "import json",
            "from gi.repository import Gimp, Gegl",
            "fg = Gimp.context_get_foreground()",
            "bg = Gimp.context_get_background()",
            "result = {}",
            "def color_to_dict(c):\n"
            "    try:\n"
            "        rgba = c.get_rgba()\n"
            "        return {'r': round(rgba.red, 4), 'g': round(rgba.green, 4), 'b': round(rgba.blue, 4), 'a': round(rgba.alpha, 4)}\n"
            "    except:\n"
            "        return str(c)",
            "result['foreground'] = color_to_dict(fg)",
            "result['background'] = color_to_dict(bg)",
            "print(json.dumps(result))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            colors_data = {}
            for out in result.get("results", []):
                if out and out.strip():
                    try:
                        colors_data = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="get_colors",
                message="Current colors retrieved",
                data=colors_data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_colors", error=str(e)).model_dump()

    @mcp.tool()
    async def swap_colors() -> ToolResult:
        """Swap foreground and background colors.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "from gi.repository import Gimp",
            "Gimp.context_swap_colors()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="swap_colors",
                message="Foreground and background colors swapped",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="swap_colors", error=str(e)).model_dump()

    @mcp.tool()
    async def analyze_color_palette(
        max_colors: int = 8,
        ignore_transparent: bool = True,
        region: dict[str, Any] | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Extract a deterministic approximate color palette for a layer or region.

        Args:
            max_colors: Maximum number of dominant colors to return.
            ignore_transparent: Skip fully transparent samples.
            region: Optional ``x/y/width/height`` rectangle in layer coordinates.
            layer_name: Target layer by name.
            layer_index: Target layer by index.

        Returns:
            Operation result with palette entries, coverage, contrast notes, and stats.

        Contract:
            The generated sampler is deterministic for the same pixels and region.
        """
        if max_colors < 1 or max_colors > 64:
            return OperationResult.fail(
                operation="analyze_color_palette",
                error="max_colors must be between 1 and 64",
            ).model_dump()
        if region is not None:
            try:
                width = int(region["width"])
                height = int(region["height"])
            except (KeyError, TypeError, ValueError) as e:
                return OperationResult.fail(
                    operation="analyze_color_palette", error=str(e)
                ).model_dump()
            if width < 1 or height < 1:
                return OperationResult.fail(
                    operation="analyze_color_palette",
                    error="region width and height must be >= 1",
                ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _palette_analysis_code(
                    max_colors, ignore_transparent, region, layer_name, layer_index
                ),
                timeout=LONG_TIMEOUT,
            )
            import json as _json

            data: dict[str, Any] = {}
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        decoded = _json.loads(str(out).strip())
                    except _json.JSONDecodeError:
                        continue
                    if isinstance(decoded, dict):
                        data = decoded
                        break
            data.setdefault("palette", [])
            data.setdefault("coverage", [])
            data.setdefault("contrast_notes", [])
            return OperationResult.ok(
                operation="analyze_color_palette",
                message=f"Analyzed up to {max_colors} palette color(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="analyze_color_palette", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def dominant_colors(
        max_colors: int = 8,
        ignore_transparent: bool = True,
        region: dict[str, Any] | None = None,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Return dominant colors for a layer or region.

        Args:
            max_colors: Maximum number of dominant colors to return.
            ignore_transparent: Skip fully transparent samples.
            region: Optional x/y/width/height rectangle in layer coordinates.
            layer_name: Target layer by name.
            layer_index: Target layer by index.

        Returns:
            Operation result with dominant color entries and coverage metadata.
        """
        if max_colors < 1 or max_colors > 64:
            return OperationResult.fail(
                operation="dominant_colors", error="max_colors must be between 1 and 64"
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _palette_analysis_code(
                    max_colors, ignore_transparent, region, layer_name, layer_index
                ),
                timeout=LONG_TIMEOUT,
            )
            data = _json_from_bridge(result)
            data.setdefault("palette", [])
            data.setdefault("coverage", [])
            return OperationResult.ok(
                operation="dominant_colors",
                message=f"Found up to {max_colors} dominant color(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="dominant_colors", error=str(e)).model_dump()

    @mcp.tool()
    async def analyze_color_histogram(
        channels: list[str] | None = None,
        start_range: float = 0.0,
        end_range: float = 1.0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Analyze channel histogram summary statistics for a layer.

        Args:
            channels: Channels to inspect: value, red, green, blue, alpha. Defaults to all common channels.
            start_range: Lower histogram range bound from 0.0 to 1.0.
            end_range: Upper histogram range bound from 0.0 to 1.0.
            layer_name: Target layer by name. Uses active layer if omitted.
            layer_index: Target layer by index. Uses active layer if omitted.

        Returns:
            Operation result with mean, standard deviation, median, pixel count, selected count, and percentile per channel.
        """
        selected_channels = channels or ["value", "red", "green", "blue", "alpha"]
        allowed = {"value", "red", "green", "blue", "alpha"}
        unknown = sorted(set(selected_channels) - allowed)
        if unknown:
            return OperationResult.fail(
                operation="analyze_color_histogram",
                error=f"Unknown channel(s): {', '.join(unknown)}",
            ).model_dump()
        if not (0.0 <= start_range <= end_range <= 1.0):
            return OperationResult.fail(
                operation="analyze_color_histogram",
                error="start_range and end_range must satisfy 0.0 <= start <= end <= 1.0",
            ).model_dump()
        channel_expr = {
            "value": "Gimp.HistogramChannel.VALUE",
            "red": "Gimp.HistogramChannel.RED",
            "green": "Gimp.HistogramChannel.GREEN",
            "blue": "Gimp.HistogramChannel.BLUE",
            "alpha": "Gimp.HistogramChannel.ALPHA",
        }
        lines = _color_preamble(layer_name, layer_index) + [
            "import json",
            "stats = {}",
        ]
        for channel in selected_channels:
            lines += [
                f"ok, mean, std_dev, median, pixels, count, percentile = drawable.histogram({channel_expr[channel]}, {start_range}, {end_range})",
                f"stats[{channel!r}] = {{'ok': bool(ok), 'mean': mean, 'std_dev': std_dev, 'median': median, 'pixels': pixels, 'count': count, 'percentile': percentile}}",
            ]
        lines += [
            "print(json.dumps({'channels': stats, 'range': {'start': "
            f"{start_range!r}, 'end': {end_range!r}"
            "}}))"
        ]
        try:
            result = await bridge.async_execute_python(lines)
            data = _json_from_bridge(result)
            data.setdefault("channels", {})
            return OperationResult.ok(
                operation="analyze_color_histogram",
                message=f"Analyzed histogram for {len(selected_channels)} channel(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="analyze_color_histogram", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def sample_pixels(
        points: list[dict[str, Any]] | None = None,
        grid: dict[str, Any] | None = None,
        sample_merged: bool = False,
        sample_average: bool = False,
        average_radius: float = 0.0,
        layer_name: str | None = None,
        layer_index: int | None = None,
    ) -> ToolResult:
        """Sample colors at multiple points or over a rectangular grid.

        Args:
            points: Explicit point dictionaries with x and y coordinates.
            grid: Optional grid spec with x, y, width, height, columns, and rows.
            sample_merged: If True, sample the visible composite image.
            sample_average: If True, average a radius around each point via GIMP pick_color.
            average_radius: Radius used when sample_average is enabled.
            layer_name: Target layer by name when not sampling merged output.
            layer_index: Target layer by index when not sampling merged output.

        Returns:
            Operation result with sampled RGBA/hex colors and request metadata.
        """
        if not points and grid is None:
            return OperationResult.fail(
                operation="sample_pixels",
                error="sample_pixels requires points or grid",
            ).model_dump()

        try:
            normalised_points, points_requested = _normalise_sample_points(points, grid)
        except (KeyError, TypeError, ValueError) as e:
            return OperationResult.fail(operation="sample_pixels", error=str(e)).model_dump()

        average_radius = max(0.0, float(average_radius))
        if average_radius > MAX_AVERAGE_RADIUS:
            return OperationResult.fail(
                operation="sample_pixels",
                error=f"average_radius must be <= {MAX_AVERAGE_RADIUS}",
            ).model_dump()
        code = _sample_pixels_code(
            normalised_points,
            grid,
            sample_merged=sample_merged,
            sample_average=sample_average,
            average_radius=average_radius,
            layer_name=layer_name,
            layer_index=layer_index,
        )
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            sample_data: dict[str, Any] = {}
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        decoded = _json.loads(str(out).strip())
                    except _json.JSONDecodeError:
                        continue
                    if isinstance(decoded, dict):
                        sample_data = decoded
                        break
            sample_data.setdefault("samples", [])
            sample_data.setdefault("color_space", "rgba")
            sample_data["points_requested"] = points_requested
            sample_data["sample_merged"] = sample_merged
            sample_data["sample_average"] = sample_average
            sample_data["average_radius"] = average_radius
            return OperationResult.ok(
                operation="sample_pixels",
                message=f"Sampled {points_requested} pixel point(s)",
                data=sample_data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="sample_pixels", error=str(e)).model_dump()

    @mcp.tool()
    async def sample_color(
        x: int,
        y: int,
        sample_merged: bool = False,
    ) -> ToolResult:
        """Pick/sample a color from a pixel in the image.

        Args:
            x: X coordinate to sample
            y: Y coordinate to sample
            sample_merged: If True, sample from all visible layers merged.
                          If False, sample from active layer only.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "import json",
            "from gi.repository import Gimp, Gegl",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "sel = image.get_selected_layers()",
            "if not sel: raise RuntimeError('No active layer')",
            "drawable = sel[0]",
            "result = {}",
            "try:\n"
            f"    color = drawable.get_pixel({x}, {y})\n"
            "    rgba = color.get_rgba()\n"
            "    result = {'r': round(rgba.red, 4), 'g': round(rgba.green, 4), 'b': round(rgba.blue, 4), 'a': round(rgba.alpha, 4)}\n"
            "except Exception as e:\n"
            "    result = {'error': str(e)}",
            "print(json.dumps(result))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            color_data = {}
            for out in result.get("results", []):
                if out and out.strip():
                    try:
                        color_data = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="sample_color",
                message=f"Color sampled at ({x}, {y})",
                data=color_data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="sample_color", error=str(e)).model_dump()

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
        return await execute_json_tool(
            bridge,
            operation="palette_create_or_update",
            marker="__gimp_mcp_palette_create_or_update__",
            payload=payload,
            message="Palette operation prepared",
        )
