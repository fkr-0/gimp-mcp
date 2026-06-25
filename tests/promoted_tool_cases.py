"""Shared offline invocation cases for promoted native feature tools."""

from __future__ import annotations

from typing import Any

PROMOTED_TOOL_CASES: dict[str, dict[str, Any]] = {
    "edit_channels": {"kwargs": {"action": "list"}, "marker": "__gimp_mcp_edit_channels__"},
    "manage_channels": {"kwargs": {"action": "list"}, "marker": "__gimp_mcp_manage_channels__"},
    "edit_paths": {"kwargs": {"action": "list"}, "marker": "__gimp_mcp_edit_paths__"},
    "create_and_edit_paths": {
        "kwargs": {
            "action": "create",
            "points": [{"x": 0, "y": 0}, {"x": 20, "y": 0}],
            "closed": False,
        },
        "marker": "__gimp_mcp_create_and_edit_paths__",
    },
    "stroke_or_fill_path": {
        "kwargs": {
            "path_ref": "Path 1",
            "mode": "stroke",
            "paint": {"color": "#000000", "width": 2},
        },
        "marker": "__gimp_mcp_stroke_or_fill_path__",
    },
    "palette_create_or_update": {
        "kwargs": {
            "action": "create",
            "palette_name": "Agent Palette",
            "colors": [{"name": "red", "hex": "#ff0000"}],
            "overwrite": False,
        },
        "marker": "__gimp_mcp_palette_create_or_update__",
    },
    "import_as_layer_with_metadata": {
        "kwargs": {
            "source": "/tmp/gimp-mcp-asset.png",
            "layer_name": "Imported",
            "placement": {"x": 1, "y": 2},
        },
        "marker": "__gimp_mcp_import_as_layer_with_metadata__",
    },
    "batch_export_variants": {
        "kwargs": {
            "variants": [{"format": "png", "width": 64, "height": 64}],
            "base_path": "/tmp/gimp-mcp-variant",
            "overwrite": False,
        },
        "marker": "__gimp_mcp_batch_export_variants__",
    },
    "pdb_introspect_typed": {
        "kwargs": {"query": "png", "include_deprecated": False},
        "marker": "__gimp_mcp_pdb_introspect_typed__",
    },
    "safe_python_eval": {
        "kwargs": {"code": "1 + 1", "mode": "expression", "require_debug_enabled": True},
        "marker": "__gimp_mcp_safe_python_eval__",
    },
    "manage_guides_and_grid": {
        "kwargs": {"action": "list"},
        "marker": "__gimp_mcp_manage_guides_and_grid__",
    },
    "preview_gegl_operation": {
        "kwargs": {
            "target": {"layer_name": "Layer 1"},
            "operation": "gegl:gaussian-blur",
            "properties": {"std-dev-x": 2.0},
            "preview_region": {"x": 0, "y": 0, "width": 32, "height": 32},
        },
        "marker": "__gimp_mcp_preview_gegl_operation__",
    },
    "execute_pdb_call": {
        "kwargs": {
            "procedure": "file-png-export",
            "arguments": {"run-mode": "noninteractive"},
            "dry_run": True,
        },
        "marker": "__gimp_mcp_execute_pdb_call__",
    },
    "apply_gegl_operation": {
        "kwargs": {
            "target": {"layer_name": "Layer 1"},
            "operation": "gegl:gaussian-blur",
            "properties": {"std-dev-x": 2.0},
            "dry_run": True,
        },
        "marker": "__gimp_mcp_apply_gegl_operation__",
    },
}
