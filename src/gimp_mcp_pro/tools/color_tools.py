"""Color adjustment tools for GIMP MCP Pro.

Covers brightness/contrast, levels, curves, hue-saturation, desaturation,
color inversion, threshold, posterize, and color-to-alpha.
"""

from __future__ import annotations

import logging

from gimp_mcp_pro.bridge import LONG_TIMEOUT
from gimp_mcp_pro.models.common import Color, OperationResult, py_literal
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.color")


def _color_preamble(layer_name: str | None, layer_index: int | None) -> list[str]:
    """Standard preamble for color adjustment tools."""
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

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.brightness_contrast(drawable, {brightness / 127.0}, {contrast / 127.0})",
            "Gimp.displays_flush()",
        ]
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

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.hue_saturation(drawable, Gimp.HueRange.ALL, "
            f"{hue}, {lightness}, {saturation}, 0.0)",
            "Gimp.displays_flush()",
        ]
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

        code = _color_preamble(layer_name, layer_index) + [
            "Gimp.Drawable.color_balance("
            f"drawable, {transfer_expr}, {preserve_luminosity}, "
            f"{cyan_red / 100.0}, {magenta_green / 100.0}, {yellow_blue / 100.0})",
            "Gimp.displays_flush()",
        ]
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

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.levels(drawable, {ch_expr}, "
            f"{input_low / 255.0}, {input_high / 255.0}, False, "
            f"{gamma}, "
            f"{output_low / 255.0}, {output_high / 255.0}, False)",
            "Gimp.displays_flush()",
        ]
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

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.curves_spline(drawable, {ch_expr}, {control_points})",
            "Gimp.displays_flush()",
        ]
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

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.desaturate(drawable, {m_expr})",
            "Gimp.displays_flush()",
        ]
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
        code = _color_preamble(layer_name, layer_index) + [
            "Gimp.Drawable.invert(drawable, False)",
            "Gimp.displays_flush()",
        ]
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
        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.threshold(drawable, Gimp.HistogramChannel.VALUE, "
            f"{low / 255.0}, {high / 255.0})",
            "Gimp.displays_flush()",
        ]
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

        code = _color_preamble(layer_name, layer_index) + [
            f"Gimp.Drawable.posterize(drawable, {levels})",
            "Gimp.displays_flush()",
        ]
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

        code = _color_preamble(layer_name, layer_index) + [
            "if not drawable.has_alpha(): drawable.add_alpha()",
            f"gegl_color = {c.to_gegl_code()}",
            "df = Gimp.DrawableFilter.new(drawable, 'gegl:color-to-alpha', '')",
            "cfg = df.get_config()",
            "cfg.set_property('color', gegl_color)",
            "drawable.append_filter(df)",
            "drawable.merge_filter(df)",
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
        code = _color_preamble(layer_name, layer_index) + [
            "Gimp.Drawable.levels_stretch(drawable)",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="auto_white_balance",
                message="Auto white balance applied",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="auto_white_balance", error=str(e)).model_dump()

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
