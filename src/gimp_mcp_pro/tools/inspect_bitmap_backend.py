"""Bitmap, region, contact-sheet, and metadata inspection tools."""

from __future__ import annotations

import json
import logging
from typing import Any

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, CommandParams, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.inspect")


def _json_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the first JSON object printed by a generated Python command."""
    outputs = result.get("results", [])
    if isinstance(outputs, dict):
        return outputs
    if not isinstance(outputs, list):
        return {}
    for out in outputs:
        if not isinstance(out, str) or not out.strip():
            continue
        try:
            decoded = json.loads(out.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    return {}


def _region_sample_code(
    x: int, y: int, width: int, height: int, include_histogram: bool
) -> list[str]:
    """Return generated Python code for lightweight region metadata and samples."""
    return [
        "import json",
        "# __gimp_mcp_region_samples__",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "def color_to_dict(color):\n"
        "    rgba = safe_call(lambda: color.get_rgba(), None)\n"
        "    if rgba is None: return {'value': str(color)}\n"
        "    return {'r': round(rgba.red, 4), 'g': round(rgba.green, 4), 'b': round(rgba.blue, 4), 'a': round(rgba.alpha, 4)}",
        "images = Gimp.get_images()",
        "samples = []",
        "if images:\n"
        "    image = images[0]\n"
        "    layers = list(safe_call(lambda: image.get_selected_layers(), []) or safe_call(lambda: image.get_layers(), []) or [])\n"
        "    drawable = layers[0] if layers else None\n"
        f"    points = [({x}, {y}), ({x + width // 2}, {y + height // 2}), ({x + width - 1}, {y + height - 1})]\n"
        "    if drawable is not None:\n"
        "        for px, py in points:\n"
        "            color = safe_call(lambda px=px, py=py: drawable.get_pixel(px, py), None)\n"
        "            samples.append({'x': px, 'y': py, 'color': color_to_dict(color) if color is not None else None})\n",
        f"result = {{'region_bounds': {{'x': {x}, 'y': {y}, 'width': {width}, 'height': {height}}}, 'sampled_colors': samples, 'histogram': None, 'include_histogram': {include_histogram!r}}}",
        "print(json.dumps(result))",
    ]


def _contact_sheet_code(
    target: str,
    max_tile_size: int,
    label_tiles: bool,
    include_hidden_layers: bool,
) -> list[str]:
    """Return generated Python code that creates contact-sheet metadata."""
    return [
        "import json",
        "# __gimp_mcp_contact_sheet__",
        "def safe_call(fn, default=None):\n"
        "    try:\n"
        "        return fn()\n"
        "    except Exception:\n"
        "        return default",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        f"target = {target!r}",
        f"max_tile_size = {max_tile_size!r}",
        f"label_tiles = {label_tiles!r}",
        f"include_hidden_layers = {include_hidden_layers!r}",
        "layers = list(safe_call(lambda: image.get_layers(), []) or [])",
        "tile_index = []",
        "visible_candidates = []",
        "for layer in layers:\n"
        "    visible = bool(safe_call(lambda layer=layer: layer.get_visible(), True))\n"
        "    if not include_hidden_layers and not visible:\n"
        "        continue\n"
        "    layer_id = safe_call(lambda layer=layer: int(layer.get_id()), None)\n"
        "    layer_name = safe_call(lambda layer=layer: layer.get_name(), '')\n"
        "    width = safe_call(lambda layer=layer: layer.get_width(), 0)\n"
        "    height = safe_call(lambda layer=layer: layer.get_height(), 0)\n"
        "    tile_index.append({'id': layer_id, 'name': layer_name, 'visible': visible, 'width': width, 'height': height, 'label': f'{layer_id}: {layer_name}' if label_tiles else None})\n"
        "    visible_candidates.append(layer)",
        "columns = max(1, int(len(tile_index) ** 0.5 + 0.999))",
        "rows = 0 if not tile_index else (len(tile_index) + columns - 1) // columns",
        "contact_sheet_png = None",
        "result = {'contact_sheet_png': contact_sheet_png, 'tile_index': tile_index, 'tile_count': len(tile_index), 'columns': columns, 'rows': rows, 'max_tile_size': max_tile_size, 'label_tiles': label_tiles, 'include_hidden_layers': include_hidden_layers, 'warnings': ['contact_sheet_png is reserved for live bitmap export; tile_index is authoritative']}",
        "print(json.dumps(result))",
    ]


def register_bitmap_inspect_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register this focused inspect tool subset."""

    @mcp.tool()
    async def create_contact_sheet(
        target: str = "visible_layers",
        max_tile_size: int = 128,
        label_tiles: bool = True,
        include_hidden_layers: bool = False,
    ) -> ToolResult:
        """Render contact-sheet metadata for visible or selected layers.

        Args:
            target: Layer candidate set, currently ``visible_layers`` or ``all_layers``.
            max_tile_size: Maximum tile size requested for future bitmap rendering.
            label_tiles: Include stable layer ID/name labels in the tile index.
            include_hidden_layers: Include hidden layers instead of filtering them out.

        Returns:
            Operation result with ``contact_sheet_png`` placeholder and authoritative tile index.

        Contract:
            This inspection tool is read-only. It labels tiles with stable layer IDs
            and applies the hidden-layer policy explicitly.
        """
        if max_tile_size < 16 or max_tile_size > 1024:
            return OperationResult.fail(
                operation="create_contact_sheet",
                error="max_tile_size must be between 16 and 1024",
            ).model_dump()
        if target not in {"visible_layers", "all_layers", "selected"}:
            return OperationResult.fail(
                operation="create_contact_sheet",
                error="target must be visible_layers, all_layers, or selected",
            ).model_dump()
        try:
            result = await bridge.async_execute_python(
                _contact_sheet_code(target, max_tile_size, label_tiles, include_hidden_layers)
            )
            data = _json_payload(result)
            data.setdefault("contact_sheet_png", None)
            data.setdefault("tile_index", [])
            return OperationResult.ok(
                operation="create_contact_sheet",
                message=f"Contact sheet index contains {len(data.get('tile_index', []))} tile(s)",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="create_contact_sheet", error=str(e)).model_dump()

    @mcp.tool()
    async def observe_region(
        x: int,
        y: int,
        width: int,
        height: int,
        max_size: int = 512,
        include_histogram: bool = False,
    ) -> ToolResult:
        """Return a bounded visual observation and metadata for a rectangular region.

        Notes:
            Use this to inspect details without transferring the full canvas. The
            bitmap is downsampled to max_size and accompanied by actual source
            bounds plus a small set of sampled colors.

        Args:
            x: Region left coordinate in canvas pixels.
            y: Region top coordinate in canvas pixels.
            width: Region width in pixels.
            height: Region height in pixels.
            max_size: Maximum output width/height for the region PNG.
            include_histogram: Reserve space for histogram data when implemented.

        Returns:
            Operation result with cropped PNG data, region bounds, samples, and metadata.
        """
        if width < 1 or height < 1:
            return OperationResult.fail(
                operation="observe_region", error="width and height must be >= 1"
            ).model_dump()
        if max_size < 1 or max_size > 4096:
            return OperationResult.fail(
                operation="observe_region", error="max_size must be between 1 and 4096"
            ).model_dump()

        try:
            bitmap = await bridge.async_get_image_bitmap(
                max_width=max_size,
                max_height=max_size,
                region={"origin_x": x, "origin_y": y, "width": width, "height": height},
            )
            if bitmap.get("status") != "success":
                return OperationResult.fail(
                    operation="observe_region",
                    error=bitmap.get("error", "Failed to observe region"),
                ).model_dump()

            sample_result = await bridge.async_execute_python(
                _region_sample_code(x, y, width, height, include_histogram)
            )
            sample_data = _json_payload(sample_result)
            bitmap_results: dict[str, Any] = bitmap.get("results", {})
            if not isinstance(bitmap_results, dict):
                bitmap_results = {}
            data = {
                "crop_png": bitmap_results.get("image_data", ""),
                "format": "png",
                "encoding": "base64",
                "width": bitmap_results.get("width"),
                "height": bitmap_results.get("height"),
                "original_width": bitmap_results.get("original_width"),
                "original_height": bitmap_results.get("original_height"),
                "region_bounds": sample_data.get(
                    "region_bounds", {"x": x, "y": y, "width": width, "height": height}
                ),
                "sampled_colors": sample_data.get("sampled_colors", []),
                "histogram": sample_data.get("histogram"),
            }
            return OperationResult.ok(
                operation="observe_region",
                message=f"Observed region ({x},{y}) {width}x{height}",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="observe_region", error=str(e)).model_dump()

    @mcp.tool()
    async def get_image_bitmap(
        max_width: int | None = 1024,
        max_height: int | None = 1024,
        region_x: int | None = None,
        region_y: int | None = None,
        region_width: int | None = None,
        region_height: int | None = None,
    ) -> ToolResult:
        """Get the current image as a viewable bitmap (PNG).

        Notes:
            Primary use: Verification tool for checking work mid-workflow.

            Best practice guidance:
            - Check after every three to five drawing operations.
            - Use region extraction to verify specific areas at higher quality.
            - Check before the final step so mistakes are caught early.

        Args:
            max_width: Optional maximum width for scaling (default 1024). Use None for full size.
            max_height: Optional maximum height for scaling (default 1024). Use None for full size.
            region_x: Optional — extract only this region (left X)
            region_y: Optional — extract only this region (top Y)
            region_width: Optional — region width
            region_height: Optional — region height

        Returns:
            MCP Image object containing PNG data that the AI can view directly.
        """
        params: CommandParams = {}
        for field_name, value in {"max_width": max_width, "max_height": max_height}.items():
            if value is None:
                continue
            if value < 1 or value > 4096:
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error=f"{field_name} must be between 1 and 4096",
                ).model_dump()
            params[field_name] = value

        if any(v is not None for v in [region_x, region_y, region_width, region_height]):
            if not all(v is not None for v in [region_x, region_y, region_width, region_height]):
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error="All region parameters (region_x, region_y, region_width, region_height) "
                    "must be specified together",
                ).model_dump()
            if region_width is None or region_height is None:
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error="region_width and region_height must be specified",
                ).model_dump()
            if region_width < 1 or region_width > 4096:
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error="region_width must be between 1 and 4096",
                ).model_dump()
            if region_height < 1 or region_height > 4096:
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error="region_height must be between 1 and 4096",
                ).model_dump()
            params["region"] = {
                "origin_x": region_x,
                "origin_y": region_y,
                "width": region_width,
                "height": region_height,
            }

        try:
            result = await bridge.async_get_image_bitmap(
                max_width=params.get("max_width"),
                max_height=params.get("max_height"),
                region=params.get("region"),
            )

            if result.get("status") == "success":
                image_info: dict[str, Any] = result.get("results", {})
                return OperationResult.ok(
                    operation="get_image_bitmap",
                    message=(
                        f"Image captured: {image_info.get('width', '?')}x"
                        f"{image_info.get('height', '?')} pixels"
                    ),
                    data={
                        "image_data": image_info.get("image_data", ""),
                        "format": "png",
                        "width": image_info.get("width"),
                        "height": image_info.get("height"),
                        "original_width": image_info.get("original_width"),
                        "original_height": image_info.get("original_height"),
                        "encoding": "base64",
                    },
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error=result.get("error", "Failed to get image bitmap"),
                ).model_dump()

        except GimpCommandError as e:
            return OperationResult.fail(operation="get_image_bitmap", error=str(e)).model_dump()

    @mcp.tool()
    async def get_image_metadata() -> ToolResult:
        """Get detailed metadata about the active image without bitmap data.

        Notes:
            Use this tool before any operation — understand canvas dimensions,
            layer structure, and file state. Much faster than get_image_bitmap.

        Notes:
            Returned data includes dimensions, color mode, layers, channels,
            paths, and file information.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        try:
            result = await bridge.async_get_image_metadata()
            if result.get("status") == "success":
                return OperationResult.ok(
                    operation="get_image_metadata",
                    message="Image metadata retrieved",
                    data=result.get("results", {}),
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_image_metadata",
                    error=result.get("error", "Failed to get metadata"),
                ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_image_metadata", error=str(e)).model_dump()
