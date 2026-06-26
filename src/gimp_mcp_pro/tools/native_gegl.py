"""Native GEGL operation code generators."""

from __future__ import annotations

import textwrap
from typing import Any

from gimp_mcp_pro.tools.native_backend import (
    NativeOperation,
    generated_context_helpers,
    py_literal,
)


def _op_preview_gegl_operation(payload: dict[str, Any]) -> list[str]:
    return [
        *generated_context_helpers(["temporary_duplicate_image", "drawable_filter"]),
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "with temporary_duplicate_image(image) as preview_image:\n"
        "    layers = preview_image.get_layers()\n"
        "    drawable = layers[0] if layers else None\n"
        "    if drawable is None: raise RuntimeError('No drawable target available')\n"
        "    with managed_drawable_filter(drawable, result['operation']) as (df, cfg):\n"
        "        for key, value in result['properties'].items(): cfg.set_property(key, value)\n"
        "        drawable.append_filter(df); drawable.merge_filter(df)\n"
        "    result['metrics'] = {'document_mutated': False, 'preview_image_width': preview_image.get_width()}",
        "# get_image_bitmap compatible bounded preview export happens through the MCP bitmap path",
    ]


def _target_from_payload_lines() -> list[str]:
    return [
        "target_ref = result.get('target')",
        "images = Gimp.get_images()",
        "if not images: raise RuntimeError('No images are open')",
        "image = images[0]",
        "if isinstance(target_ref, dict) and target_ref.get('layer_name') is not None:\n"
        "    drawable = image.get_layer_by_name(target_ref.get('layer_name'))\n"
        "elif isinstance(target_ref, dict) and target_ref.get('layer_index') is not None:\n"
        "    layers = image.get_layers()\n"
        "    drawable = layers[int(target_ref.get('layer_index'))]\n"
        "elif isinstance(target_ref, str):\n"
        "    drawable = image.get_layer_by_name(target_ref)\n"
        "else:\n"
        "    selected = image.get_selected_layers()\n"
        "    drawable = selected[0] if selected else None",
        "if drawable is None: raise RuntimeError('No drawable target available')",
    ]


def _op_apply_gegl_operation(payload: dict[str, Any]) -> list[str]:
    property_lines = [
        f"        cfg.set_property({py_literal(key)}, {py_literal(value)})"
        for key, value in (payload.get("properties_applied") or {}).items()
    ]
    property_block = "\n".join(property_lines) or "        pass"
    return [
        *generated_context_helpers(["drawable_filter"]),
        "# __gimp_mcp_filter_lifecycle__",
        f"ALLOWED_GEGL_OPERATIONS = {py_literal(payload.get('allowed_operations') or [])}",
        f"operation_name = {py_literal(payload.get('operation_name'))}",
        f"properties = {py_literal(payload.get('properties_applied') or {})}",
        f"allowed_properties = {py_literal(payload.get('allowed_properties') or [])}",
        f"dry_run = {bool(payload.get('dry_run'))!r}",
        "if operation_name not in ALLOWED_GEGL_OPERATIONS: raise RuntimeError(f'operation is not allowlisted: {operation_name}')",
        *_target_from_payload_lines(),
        textwrap.dedent(f"""
            if dry_run:
                result['dry_run_native_backend'] = 'Gimp.DrawableFilter.new merge_filter validation path'
            else:
                with managed_drawable_filter(drawable, operation_name) as (df, cfg):
{property_block}
                    drawable.append_filter(df)
                    drawable.merge_filter(df)
                result['changed_bounds'] = {{'source': 'drawable'}}
            """).strip("\n"),
    ]


def operations() -> dict[str, NativeOperation]:
    """Return registered native backend operations for this concern."""
    return {
        "preview_gegl_operation": NativeOperation(
            name="preview_gegl_operation",
            generator=_op_preview_gegl_operation,
            required_payload_keys=("operation", "properties"),
        ),
        "apply_gegl_operation": NativeOperation(
            name="apply_gegl_operation",
            generator=_op_apply_gegl_operation,
            required_payload_keys=("operation_name", "allowed_operations"),
        ),
    }
