"""Image management tools for GIMP MCP Pro.

Covers creating, opening, saving, exporting, and managing images.
"""

from __future__ import annotations

import logging
from typing import Any

from gimp_mcp_pro.models.common import FillType, OperationResult, py_literal
from gimp_mcp_pro.models.image import CreateImageParams, ExportImageParams
from gimp_mcp_pro.tools.native_backend import (
    SUPPORTED_GUIDE_GRID_ACTIONS,
    execute_json_tool,
    validate_formats,
)
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError
from gimp_mcp_pro.utils.gimp_constants import FILL_TYPE_MAP, IMAGE_BASE_TYPE_MAP

logger = logging.getLogger("gimp_mcp_pro.tools.image")

VALID_COLOR_PROFILE_ACTIONS = {"inspect", "assign", "convert"}


def _unsafe_local_path_reason(path: str, *, field: str) -> str | None:
    """Return a reason when a local file path is unsafe for generated GIMP code."""
    value = str(path).strip()
    if not value:
        return f"unsafe {field}: path cannot be empty"
    if "\x00" in value:
        return f"unsafe {field}: NUL bytes are not allowed"
    normalized = value.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if ".." in parts:
        return f"unsafe {field}: parent traversal is not allowed"
    return None


def _get_active_image_code() -> list[str]:
    """Helper: Python code to get the active image and validate it exists."""
    return [
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open in GIMP')",
        "image = images[0]",
    ]


def _color_management_profile_code(
    action: str,
    profile_ref: str | None,
    rendering_intent: str,
) -> list[str]:
    """Return generated code for image color-profile inspection/change."""
    code = [
        "import json",
        "# __gimp_mcp_color_management_profile__",
        f"action = {py_literal(action)}",
        f"profile_ref = {py_literal(profile_ref)}",
        f"rendering_intent = {py_literal(rendering_intent)}",
        *_get_active_image_code(),
        "profile = image.get_color_profile()",
        "effective_profile = image.get_effective_color_profile()",
        "def profile_payload(value):\n"
        "    if value is None: return None\n"
        "    return {'name': str(value.get_label() if hasattr(value, 'get_label') else value), 'class': type(value).__name__}",
        "read_only = action == 'inspect'",
    ]
    if action == "inspect":
        code += [
            "result = {'action': action, 'read_only': read_only, 'profile': profile_payload(profile), 'effective_profile': profile_payload(effective_profile), 'conversion': None}",
        ]
    else:
        code += [
            "# Assign/convert is intentionally explicit and transaction-oriented in live mode.",
            "result = {'action': action, 'read_only': False, 'profile_ref': profile_ref, 'rendering_intent': rendering_intent, 'profile': profile_payload(profile), 'effective_profile': profile_payload(effective_profile), 'conversion': {'requested': action, 'profile_ref': profile_ref}}",
        ]
    code += ["print(json.dumps(result))"]
    return code


def register_image_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all image management tools with the MCP server."""

    @mcp.tool()
    async def create_image(
        width: int,
        height: int,
        color_mode: str = "rgb",
        fill: str = "white",
    ) -> ToolResult:
        """Create a new blank image in GIMP.

        Notes:
            Use this tool when starting a new project, creating a canvas for drawing.

        Args:
            width: Image width in pixels (1-32768)
            height: Image height in pixels (1-32768)
            color_mode: Color mode — "rgb", "grayscale", or "indexed"
            fill: Initial fill — "white", "transparent", "foreground", or "background"

        Returns:
            Operation result with image info in data field.
        """
        params = CreateImageParams(
            width=width,
            height=height,
            color_mode=color_mode,
            fill=fill,
            fill_color=None,
        )

        base_type = IMAGE_BASE_TYPE_MAP.get(params.color_mode, "Gimp.ImageBaseType.RGB")
        fill_type = FILL_TYPE_MAP.get(params.fill, "Gimp.FillType.WHITE")

        # Determine image type for layer (with/without alpha)
        has_alpha = params.fill == FillType.TRANSPARENT
        if params.color_mode.value == "rgb":
            img_type = "Gimp.ImageType.RGBA_IMAGE" if has_alpha else "Gimp.ImageType.RGB_IMAGE"
        elif params.color_mode.value == "grayscale":
            img_type = "Gimp.ImageType.GRAYA_IMAGE" if has_alpha else "Gimp.ImageType.GRAY_IMAGE"
        else:
            img_type = (
                "Gimp.ImageType.INDEXEDA_IMAGE" if has_alpha else "Gimp.ImageType.INDEXED_IMAGE"
            )

        lifecycle_lines = [
            "# __gimp_mcp_create_image_lifecycle__",
            "image = None",
            "layer = None",
            "created_image = False",
            "try:",
            f"    image = Gimp.Image.new({params.width}, {params.height}, {base_type})",
            "    created_image = True",
            f"    layer = Gimp.Layer.new(image, 'Background', {params.width}, {params.height}, "
            f"{img_type}, 100, Gimp.LayerMode.NORMAL)",
            "    image.insert_layer(layer, None, 0)",
            f"    Gimp.Drawable.edit_fill(layer, {fill_type})",
            "    try:",
            "        Gimp.Display.new(image)",
            "    except Exception:",
            "        pass",
            "    image_id = image.get_id() if hasattr(image, 'get_id') else 0",
            "except Exception:",
            "    try:",
            "        if created_image and image is not None:",
            "            image.delete()",
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
            "\n".join(lifecycle_lines),
            "Gimp.displays_flush()",
            "print(image_id)",
        ]

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="create_image",
                message=f"Created {params.width}x{params.height} {params.color_mode.value} image",
                data={
                    "width": params.width,
                    "height": params.height,
                    "color_mode": params.color_mode.value,
                    "fill": params.fill.value,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="create_image",
                error=str(e),
            ).model_dump()

    @mcp.tool()
    async def add_guide(
        orientation: str = "horizontal",
        position: int = 0,
    ) -> ToolResult:
        """Add a horizontal or vertical guide to the active image.

        Args:
            orientation: "horizontal"/"h" or "vertical"/"v".
            position: Pixel position from the top for horizontal guides or from the left for vertical guides.

        Returns:
            Operation result dictionary with guide orientation and position.
        """
        orientation_key = orientation.lower().strip()
        resolved_orientation = "vertical" if orientation_key in {"v", "vertical"} else "horizontal"
        position = max(0, int(position))
        add_call = "image.add_vguide" if resolved_orientation == "vertical" else "image.add_hguide"

        code = [
            "from gi.repository import Gimp",
            *_get_active_image_code(),
            f"guide_id = {add_call}({position})",
            "Gimp.displays_flush()",
            "print(guide_id)",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="add_guide",
                message=f"Added {resolved_orientation} guide at {position}px",
                data={"orientation": resolved_orientation, "position": position},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="add_guide", error=str(e)).model_dump()

    @mcp.tool()
    async def delete_guide(guide_id: int) -> ToolResult:
        """Delete a guide from the active image by guide ID.

        Args:
            guide_id: GIMP guide ID returned by add_guide or list_guides.

        Returns:
            Operation result dictionary with the deleted guide ID.
        """
        guide_id = max(1, int(guide_id))
        code = [
            "from gi.repository import Gimp",
            *_get_active_image_code(),
            f"image.delete_guide({guide_id})",
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="delete_guide",
                message=f"Deleted guide {guide_id}",
                data={"guide_id": guide_id},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="delete_guide", error=str(e)).model_dump()

    @mcp.tool()
    async def list_guides() -> ToolResult:
        """List guides on the active image with ID, orientation, and position.

        Returns:
            Operation result dictionary containing a guides list and count.
        """
        code = [
            "import json",
            "from gi.repository import Gimp",
            *_get_active_image_code(),
            "guides = []",
            "guide_id = image.find_next_guide(0)",
            "while guide_id:\n"
            "    orientation = image.get_guide_orientation(guide_id)\n"
            "    position = image.get_guide_position(guide_id)\n"
            "    orientation_name = str(orientation).split('.')[-1].lower()\n"
            "    guides.append({'id': guide_id, 'orientation': orientation_name, 'position': position})\n"
            "    guide_id = image.find_next_guide(guide_id)",
            "print(json.dumps({'guides': guides, 'count': len(guides)}))",
        ]
        try:
            result = await bridge.async_execute_python(code)
            import json as _json

            guides_data: dict[str, Any] = {"guides": [], "count": 0}
            for out in result.get("results", []):
                if out and str(out).strip():
                    try:
                        guides_data = _json.loads(str(out).strip())
                        break
                    except _json.JSONDecodeError:
                        continue
            return OperationResult.ok(
                operation="list_guides",
                message=f"Found {guides_data.get('count', 0)} guide(s)",
                data=guides_data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="list_guides", error=str(e)).model_dump()

    @mcp.tool()
    async def set_image_grid(
        xspacing: float = 10.0,
        yspacing: float = 10.0,
        xoffset: float = 0.0,
        yoffset: float = 0.0,
        style: str = "intersections",
    ) -> ToolResult:
        """Configure grid spacing, offset, and visual style on the active image.

        Args:
            xspacing: Horizontal grid spacing in pixels.
            yspacing: Vertical grid spacing in pixels.
            xoffset: Horizontal grid offset in pixels.
            yoffset: Vertical grid offset in pixels.
            style: Grid style such as dots, intersections, on_off_dash, double_dash, or solid.

        Returns:
            Operation result dictionary with applied grid settings.
        """
        xspacing = max(0.1, float(xspacing))
        yspacing = max(0.1, float(yspacing))
        xoffset = max(0.0, float(xoffset))
        yoffset = max(0.0, float(yoffset))
        style_key = style.lower().strip().replace("-", "_").replace(" ", "_")
        style_map = {
            "dots": "Gimp.GridStyle.DOTS",
            "intersections": "Gimp.GridStyle.INTERSECTIONS",
            "crosshairs": "Gimp.GridStyle.INTERSECTIONS",
            "on_off_dash": "Gimp.GridStyle.ON_OFF_DASH",
            "double_dash": "Gimp.GridStyle.DOUBLE_DASH",
            "solid": "Gimp.GridStyle.SOLID",
        }
        resolved_style = style_key if style_key in style_map else "intersections"
        style_expr = style_map[resolved_style]

        lifecycle_lines = [
            "# __gimp_mcp_image_grid_lifecycle__",
            "image.undo_group_start()",
            "try:",
            f"    image.grid_set_spacing({xspacing}, {yspacing})",
            f"    image.grid_set_offset({xoffset}, {yoffset})",
            f"    image.grid_set_style({style_expr})",
            "finally:",
            "    image.undo_group_end()",
        ]
        code = [
            "from gi.repository import Gimp",
            *_get_active_image_code(),
            "\n".join(lifecycle_lines),
            "Gimp.displays_flush()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="set_image_grid",
                message="Image grid configured",
                data={
                    "xspacing": xspacing,
                    "yspacing": yspacing,
                    "xoffset": xoffset,
                    "yoffset": yoffset,
                    "style": resolved_style,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="set_image_grid", error=str(e)).model_dump()

    @mcp.tool()
    async def color_management_profile(
        action: str = "inspect",
        profile_ref: str | None = None,
        rendering_intent: str = "perceptual",
        confirm: bool = False,
    ) -> ToolResult:
        """Inspect or explicitly request guarded image color-profile operations.

        Args:
            action: inspect, assign, or convert.
            profile_ref: Optional profile reference for assign/convert operations.
            rendering_intent: Requested rendering intent label.
            confirm: Required for assign/convert operations.

        Returns:
            Operation result with profile metadata or guarded operation request metadata.
        """
        normalized_action = action.lower().strip()
        if normalized_action not in VALID_COLOR_PROFILE_ACTIONS:
            return OperationResult.fail(
                operation="color_management_profile",
                error="action must be inspect, assign, or convert",
            ).model_dump()
        if normalized_action in {"assign", "convert"} and not confirm:
            return OperationResult.fail(
                operation="color_management_profile",
                error="confirm=True is required for assign/convert color profile operations",
            ).model_dump()
        if normalized_action in {"assign", "convert"} and not profile_ref:
            return OperationResult.fail(
                operation="color_management_profile",
                error="profile_ref is required for assign/convert",
            ).model_dump()
        try:
            await bridge.async_execute_python(
                _color_management_profile_code(normalized_action, profile_ref, rendering_intent)
            )
            return OperationResult.ok(
                operation="color_management_profile",
                message="Color profile inspected"
                if normalized_action == "inspect"
                else "Color profile operation requested",
                data={
                    "action": normalized_action,
                    "profile_ref": profile_ref,
                    "rendering_intent": rendering_intent,
                    "read_only": normalized_action == "inspect",
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(
                operation="color_management_profile", error=str(e)
            ).model_dump()

    @mcp.tool()
    async def list_images() -> ToolResult:
        """List all currently open images in GIMP.

        Notes:
            Use this tool before operations that need to target a specific image,
            or to verify what images are available.

        Returns:
            Operation result with list of image info dicts.
        """
        code = [
            "import json",
            "images = Gimp.get_images()",
            "result = []",
            "for img in images:\n"
            "    info = {\n"
            "        'width': img.get_width(),\n"
            "        'height': img.get_height(),\n"
            "        'base_type': str(img.get_base_type()),\n"
            "        'num_layers': len(img.get_layers()),\n"
            "        'is_dirty': img.is_dirty() if hasattr(img, 'is_dirty') else False,\n"
            "    }\n"
            "    try:\n"
            "        f = img.get_file()\n"
            "        if f:\n"
            "            info['file_path'] = f.get_path() if hasattr(f, 'get_path') else None\n"
            "            info['file_name'] = f.get_basename() if hasattr(f, 'get_basename') else None\n"
            "    except: pass\n"
            "    result.append(info)",
            "print(json.dumps(result))",
        ]

        try:
            result = await bridge.async_execute_python(code)
            outputs: list[str] = result.get("results", [])
            # Parse the JSON output from the last print statement
            import json as _json

            images_data: list[dict[str, Any]] = []
            for out in outputs:
                if out and out.strip():
                    try:
                        images_data = _json.loads(out.strip())
                        break
                    except _json.JSONDecodeError:
                        continue

            return OperationResult.ok(
                operation="list_images",
                message=f"Found {len(images_data)} open image(s)",
                data={"images": images_data, "count": len(images_data)},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="list_images", error=str(e)).model_dump()

    @mcp.tool()
    async def get_image_info() -> ToolResult:
        """Get detailed metadata about the active image (no bitmap data).

        Notes:
            Use this tool before any operation, to understand the current canvas
            dimensions, layer structure, and file state. Much faster than
            get_image_bitmap since it doesn't export pixel data.

        Notes:
            Works well with: Use before create_layer (to match dimensions),
            before drawing (to verify layer structure), or before export
            (to check if image has unsaved changes).

        Returns:
            Comprehensive image metadata including layers, channels, file info.
        """
        try:
            result = await bridge.async_get_image_metadata()
            if result.get("status") == "success":
                return OperationResult.ok(
                    operation="get_image_info",
                    message="Image metadata retrieved",
                    data=result.get("results", {}),
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_image_info",
                    error=result.get("error", "Failed to get image metadata"),
                ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_image_info", error=str(e)).model_dump()

    @mcp.tool()
    async def export_with_manifest(
        format: str,
        destination: str,
        include_sidecar: bool = True,
        export_settings: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Export an image and write a JSON provenance sidecar manifest.

        Args:
            format: Export format: png, jpeg/jpg, webp, tiff/tif, psd, or xcf.
            destination: Output file path.
            include_sidecar: Write ``.manifest.json`` next to the export.
            export_settings: Optional format-specific settings.

        Returns:
            Operation result with export path and manifest metadata.
        """
        format_name = format.lower().strip().lstrip(".")
        format_name = (
            "jpeg" if format_name == "jpg" else "tiff" if format_name == "tif" else format_name
        )
        procedures = {
            "png": "file-png-export",
            "jpeg": "file-jpeg-export",
            "webp": "file-webp-export",
            "tiff": "file-tiff-export",
            "psd": "file-psd-export",
            "xcf": "gimp-xcf-save",
        }
        if format_name not in procedures:
            return OperationResult.fail(
                operation="export_with_manifest",
                error=f"unsupported format: {format}",
            ).model_dump()
        unsafe_reason = _unsafe_local_path_reason(destination, field="destination")
        if unsafe_reason:
            return OperationResult.fail(
                operation="export_with_manifest", error=unsafe_reason
            ).model_dump()
        settings = export_settings or {}
        code = [
            "from gi.repository import Gimp, Gio",
            "import gc, json, os, time",
            "# __gimp_mcp_export_with_manifest__",
            "# __gimp_mcp_export_with_manifest_lifecycle__",
            f"format_name = {py_literal(format_name)}",
            f"destination = {py_literal(destination)}",
            f"include_sidecar = {include_sidecar!r}",
            f"export_settings = {py_literal(settings)}",
            f"procedure_name = {py_literal(procedures[format_name])}",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open in GIMP')",
            "image = images[0]",
            "file_obj = None",
            "export_proc = None",
            "config = None",
            "manifest_fh = None",
            "try:",
            "    file_obj = Gio.File.new_for_path(destination)",
            "    export_proc = Gimp.get_pdb().lookup_procedure(procedure_name)",
            "    if export_proc is None: raise RuntimeError(f'Export procedure not found: {procedure_name}')",
            "    config = export_proc.create_config()",
            "    try:\n        config.set_property('image', image)\n    except Exception:\n        pass",
            "    try:\n        config.set_property('file', file_obj)\n    except Exception:\n        pass",
            "    try:\n        config.set_property('drawables', image.get_layers())\n    except Exception:\n        pass",
            "    for key, value in export_settings.items():\n"
            "        try:\n"
            "            config.set_property(key, value)\n"
            "        except Exception:\n"
            "            pass",
            "    export_proc.run(config)",
            "    manifest = {'format': format_name, 'destination': destination, 'procedure': procedure_name, 'settings': export_settings, 'image': {'width': image.get_width(), 'height': image.get_height()}, 'timestamp': time.time()}",
            "    manifest_path = destination + '.manifest.json'",
            "    if include_sidecar:\n"
            "        manifest_fh = open(manifest_path, 'w', encoding='utf-8')\n"
            "        json.dump(manifest, manifest_fh, sort_keys=True, indent=2)\n"
            "        manifest_fh.close()\n"
            "        manifest_fh = None",
            "    result = {'file': destination, 'format': format_name, 'manifest': manifest, 'manifest_path': manifest_path if include_sidecar else None}",
            "finally:",
            "    try:",
            "        if manifest_fh is not None:",
            "            manifest_fh.close()",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del manifest_fh",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del config",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del export_proc",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del file_obj",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
            "print(json.dumps(result, sort_keys=True))",
        ]
        try:
            await bridge.async_execute_python(code, timeout=60.0)
            return OperationResult.ok(
                operation="export_with_manifest",
                message=f"Exported {format_name} with manifest metadata",
                data={"file": destination, "format": format_name, "sidecar": include_sidecar},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="export_with_manifest", error=str(e)).model_dump()

    @mcp.tool()
    async def export_image(
        file_path: str,
        format: str | None = None,
        quality: int = 85,
    ) -> ToolResult:
        """Export the active image to a file.

        Notes:
            Use this tool when saving the final result as PNG, JPEG, etc.

        Args:
            file_path: Output path (e.g., "/home/user/output.png")
            format: Export format — "png", "jpeg", "tiff", "bmp", "webp".
                    Auto-detected from file extension if not specified.
            quality: Quality for lossy formats like JPEG (1-100). Default 85.

        Returns:
            Operation result confirming export.
        """
        unsafe_reason = _unsafe_local_path_reason(file_path, field="file_path")
        if unsafe_reason:
            return OperationResult.fail(operation="export_image", error=unsafe_reason).model_dump()
        params = ExportImageParams(
            file_path=file_path,
            format=format,
            image_id=None,
            quality=quality,
            compression=9,
        )

        # Build export code based on format
        ext = params.file_path.rsplit(".", 1)[-1].lower() if "." in params.file_path else "png"
        fmt = params.format.value if params.format else ext
        procedure_name = (
            "file-png-export"
            if fmt == "png"
            else "file-jpeg-export"
            if fmt in ("jpeg", "jpg")
            else None
        )

        code = _get_active_image_code() + [
            "from gi.repository import Gio",
            "import gc",
            "# __gimp_mcp_image_export_lifecycle__",
            "file_obj = None",
            "export_proc = None",
            "config = None",
            "try:",
            f"    file_obj = Gio.File.new_for_path({py_literal(params.file_path)})",
        ]
        if procedure_name is not None:
            code += [
                f"    export_proc = Gimp.get_pdb().lookup_procedure({py_literal(procedure_name)})",
                f"    if not export_proc: raise RuntimeError({py_literal(procedure_name + ' procedure not found')})",
                "    config = export_proc.create_config()",
                "    config.set_property('image', image)",
                "    config.set_property('file', file_obj)",
                "    try:\n        config.set_property('drawables', image.get_layers())\n    except Exception:\n        pass",
            ]
            if fmt in ("jpeg", "jpg"):
                code.append(
                    f"    try:\n        config.set_property('quality', {params.quality / 100.0})\n    except Exception:\n        pass"
                )
            code.append("    export_proc.run(config)")
        else:
            code.append("    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, file_obj)")
        code += [
            "finally:",
            "    try:",
            "        del config",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del export_proc",
            "    except Exception:",
            "        pass",
            "    try:",
            "        del file_obj",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
            f"print({py_literal(f'Exported to {params.file_path}')})",
        ]

        try:
            await bridge.async_execute_python(code, timeout=60.0)
            return OperationResult.ok(
                operation="export_image",
                message=f"Exported to {params.file_path}",
                data={"file_path": params.file_path, "format": fmt},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="export_image", error=str(e)).model_dump()

    @mcp.tool()
    async def flatten_image() -> ToolResult:
        """Flatten all layers into a single layer.

        Notes:
            Use this tool before final export when you want to merge all layers,
            or to simplify a complex layer structure.

        Warnings:
            This is destructive — you lose individual layer editability.
            Consider using undo groups so the user can revert.

        Returns:
            Operation result.
        """
        lifecycle_lines = [
            "# __gimp_mcp_image_flatten_lifecycle__",
            "image.undo_group_start()",
            "try:",
            "    image.flatten()",
            "finally:",
            "    image.undo_group_end()",
        ]
        code = _get_active_image_code() + [
            "\n".join(lifecycle_lines),
            "Gimp.displays_flush()",
            "print('Image flattened')",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="flatten_image",
                message="All layers flattened into one",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="flatten_image", error=str(e)).model_dump()

    @mcp.tool()
    async def duplicate_image() -> ToolResult:
        """Duplicate the entire active image (all layers, channels, paths).

        Notes:
            Use this tool when creating a copy to experiment on without affecting
            the original. Good before destructive operations.

        Returns:
            Operation result with info about the new image.
        """
        code = _get_active_image_code() + [
            "import gc",
            "# __gimp_mcp_duplicate_image_lifecycle__",
            "new_image = None",
            "display = None",
            "try:",
            "    new_image = image.duplicate()",
            "    try:",
            "        display = Gimp.Display.new(new_image)",
            "    except Exception:",
            "        pass",
            "    Gimp.displays_flush()",
            "    print(f'{new_image.get_width()}x{new_image.get_height()}')",
            "finally:",
            "    try:",
            "        del display",
            "    except Exception:",
            "        pass",
            "    gc.collect()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="duplicate_image",
                message="Image duplicated",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="duplicate_image", error=str(e)).model_dump()

    @mcp.tool()
    async def import_as_layer_with_metadata(
        source: str,
        layer_name: str | None = None,
        placement: dict[str, int] | None = None,
    ) -> ToolResult:
        """Import an external image as a layer with provenance metadata.

        Args:
            source: Controlled local source path.
            layer_name: Optional layer name.
            placement: Optional x/y placement.

        Returns:
            Operation result with layer and provenance metadata.
        """
        unsafe_reason = _unsafe_local_path_reason(source, field="source")
        if unsafe_reason:
            return OperationResult.fail(
                operation="import_as_layer_with_metadata", error=unsafe_reason
            ).model_dump()
        payload = {
            "source": source,
            "layer_name": layer_name,
            "placement": placement or {},
            "layer_id": None,
            "metadata": {"source": source},
        }
        return await execute_json_tool(
            bridge,
            operation="import_as_layer_with_metadata",
            marker="__gimp_mcp_import_as_layer_with_metadata__",
            payload=payload,
            message="Import as layer prepared",
        )

    @mcp.tool()
    async def batch_export_variants(
        variants: list[dict[str, Any]],
        base_path: str,
        overwrite: bool = False,
    ) -> ToolResult:
        """Export multiple bounded variants from the active image.

        Args:
            variants: Variant definitions with format and optional dimensions.
            base_path: Controlled output base path.
            overwrite: Whether existing files may be overwritten.

        Returns:
            Operation result with exported files and warnings.
        """
        unsupported = validate_formats([variant.get("format", "") for variant in variants])
        if unsupported:
            return OperationResult.fail(
                operation="batch_export_variants",
                error=f"unsupported format(s): {', '.join(unsupported)}",
            ).model_dump()
        unsafe_reason = _unsafe_local_path_reason(base_path, field="base_path")
        if unsafe_reason:
            return OperationResult.fail(
                operation="batch_export_variants", error=unsafe_reason
            ).model_dump()
        payload = {
            "variants": variants,
            "base_path": base_path,
            "overwrite": overwrite,
            "files": [],
            "warnings": [],
        }
        return await execute_json_tool(
            bridge,
            operation="batch_export_variants",
            marker="__gimp_mcp_batch_export_variants__",
            payload=payload,
            message="Batch export variants prepared",
        )

    @mcp.tool()
    async def manage_guides_and_grid(
        action: str = "list",
        orientation: str | None = None,
        position: float | None = None,
        guide_id: int | None = None,
        grid: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Create, list, move, remove guides, or set document grid settings.

        Args:
            action: list/add/move/remove/set_grid.
            orientation: Optional horizontal/vertical orientation.
            position: Optional guide position.
            guide_id: Optional existing guide ID.
            grid: Optional grid settings.

        Returns:
            Operation result with guides and grid metadata.
        """
        normalized = action.strip().lower().replace("-", "_")
        if normalized not in SUPPORTED_GUIDE_GRID_ACTIONS:
            return OperationResult.fail(
                operation="manage_guides_and_grid", error="unsupported guide/grid action"
            ).model_dump()
        payload: dict[str, Any] = {
            "action": normalized,
            "orientation": orientation,
            "position": position,
            "guide_id": guide_id,
            "grid": grid or {},
            "guides": [],
        }
        return await execute_json_tool(
            bridge,
            operation="manage_guides_and_grid",
            marker="__gimp_mcp_manage_guides_and_grid__",
            payload=payload,
            message="Guide/grid management action prepared",
        )
