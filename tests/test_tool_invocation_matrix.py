"""Behavioral invocation matrix for the async MCP tool surface.

These tests do not require GIMP. They exercise each public async tool handler
against a scripted bridge so the tool-level validation, generated-code dispatch,
and OperationResult shaping remain covered while live 3.2.4 smoke tests stay
separate.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

from gimp_mcp_pro.flows.models import FlowDefinition
from gimp_mcp_pro.flows.operations import OperationRegistry
from gimp_mcp_pro.flows.store import FlowStore
from gimp_mcp_pro.protocol import BitmapRegion, CommandParams, PluginResponse, ToolResult
from gimp_mcp_pro.tools.agent_tools import register_agent_tools
from gimp_mcp_pro.tools.color_tools import register_color_tools
from gimp_mcp_pro.tools.drawing_tools import register_drawing_tools
from gimp_mcp_pro.tools.filter_tools import register_filter_tools
from gimp_mcp_pro.tools.flow_tools import register_flow_tools
from gimp_mcp_pro.tools.gimp_dev_tools import register_gimp_dev_tools
from gimp_mcp_pro.tools.history_tools import register_history_tools
from gimp_mcp_pro.tools.image_tools import register_image_tools
from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools
from gimp_mcp_pro.tools.layer_tools import register_layer_tools
from gimp_mcp_pro.tools.path_tools import register_path_tools
from gimp_mcp_pro.tools.pdb_tools import register_pdb_tools
from gimp_mcp_pro.tools.selection_tools import register_selection_tools
from gimp_mcp_pro.tools.target_tools import register_target_tools
from gimp_mcp_pro.tools.transform_tools import register_transform_tools
from gimp_mcp_pro.tools.types import AsyncToolBridge
from gimp_mcp_pro.utils.errors import GimpCommandError
from tests.promoted_tool_cases import PROMOTED_TOOL_CASES
from tests.test_flow_models import flow_payload

AsyncRegisteredTool = Callable[..., Awaitable[ToolResult]]


class CaptureMCP:
    """Small FastMCP-compatible registrar used for direct tool invocation."""

    def __init__(self) -> None:
        self.tools: dict[str, AsyncRegisteredTool] = {}

    def tool(
        self, *args: Any, **kwargs: Any
    ) -> Callable[[AsyncRegisteredTool], AsyncRegisteredTool]:
        """Return a decorator that records a tool coroutine by function name."""

        def decorator(fn: AsyncRegisteredTool) -> AsyncRegisteredTool:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class ScriptedToolBridge:
    """Async bridge fake with result payloads tailored to parser branches."""

    def __init__(self) -> None:
        self.execute_calls: list[list[str]] = []
        self.command_calls: list[tuple[str, CommandParams | None, float | None]] = []
        self.bitmap_calls: list[dict[str, object]] = []

    async def async_send_command(
        self,
        command_type: str,
        params: CommandParams | None = None,
        timeout: float | None = None,
    ) -> PluginResponse:
        self.command_calls.append((command_type, params, timeout))
        return {
            "status": "success",
            "results": {"command_type": command_type, "params": params or {}},
        }

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        del timeout
        self.execute_calls.append(code_lines)
        source = "\n".join(code_lines)

        if "gimp-mcp-pro:agent:begin_edit_transaction" in source:
            return {
                "status": "success",
                "results": [json.dumps({"image_id": 101, "undo_group_started": True})],
            }
        if "gimp-mcp-pro:agent:end_edit_transaction" in source:
            return {"status": "success", "results": [json.dumps({"undo_group_ended": True})]}
        if "gimp-mcp-pro:agent:rollback_transaction" in source:
            return {
                "status": "success",
                "results": [json.dumps({"undo_group_ended": True, "rolled_back": True})],
            }
        if "__gimp_mcp_session_capabilities__" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        {
                            "gimp_version": "3.2.4",
                            "api_namespace": "3.0",
                            "capabilities": {
                                "pdb_available": True,
                                "procedures": {"file-png-export": True},
                                "export": {"file-png-export": True},
                                "safety_mode": "localhost-only",
                            },
                            "unavailable": [],
                        }
                    )
                ],
            }
        if "__gimp_mcp_document_state__" in source and "__gimp_mcp_layer_tree__" not in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        {
                            "has_image": True,
                            "image_id": 101,
                            "dimensions": {"width": 320, "height": 200},
                            "color_mode": "RGB",
                            "active_layer": {"id": 201, "name": "Layer 1", "kind": "layer"},
                            "selected_layer_ids": [201],
                            "layer_tree": [{"id": 201, "name": "Layer 1", "visible": True}],
                            "layers_flat": [{"id": 201, "name": "Layer 1", "visible": True}],
                            "selections": {"non_empty": False},
                            "guides": [],
                            "paths": [],
                            "channels": [],
                            "warnings": [],
                        }
                    )
                ],
            }
        if "__gimp_mcp_layer_tree__" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        {
                            "image_id": 101,
                            "layers": [
                                {
                                    "id": 201,
                                    "name": "Layer 1",
                                    "visible": True,
                                    "editable": True,
                                    "bounds": {"x": 0, "y": 0, "width": 320, "height": 200},
                                }
                            ],
                            "groups": [],
                            "warnings": [],
                        }
                    )
                ],
            }
        if "__gimp_mcp_region_samples__" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        {
                            "region_bounds": {"x": 1, "y": 2, "width": 30, "height": 40},
                            "sampled_colors": [
                                {"x": 1, "y": 2, "color": {"r": 0.1, "g": 0.2, "b": 0.3, "a": 1.0}}
                            ],
                            "histogram": None,
                        }
                    )
                ],
            }
        if "__gimp_mcp_resolve_target__" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        {
                            "query": "layer 1",
                            "target_types": ["layer"],
                            "matches": [
                                {"kind": "layer", "id": 201, "name": "Layer 1", "score": 90}
                            ],
                            "count": 1,
                            "selected": {"kind": "layer", "id": 201, "name": "Layer 1"},
                            "ambiguity": {"ambiguous": False, "reason": "none"},
                        }
                    )
                ],
            }
        if "__gimp_mcp_validate_targets__" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        {
                            "valid": True,
                            "targets": [{"kind": "layer", "id": 201, "name": "Layer 1"}],
                            "failures": [],
                            "warnings": [],
                            "required_capabilities": ["editable", "visible"],
                        }
                    )
                ],
            }

        if "for img in images" in source and "json.dumps(result)" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        [
                            {
                                "width": 320,
                                "height": 200,
                                "base_type": "RGB",
                                "num_layers": 2,
                                "is_dirty": False,
                            }
                        ]
                    )
                ],
            }
        if "for i, layer in enumerate(layers)" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        [
                            {
                                "index": 0,
                                "name": "Layer 1",
                                "visible": True,
                                "opacity": 100.0,
                                "width": 320,
                                "height": 200,
                                "has_alpha": True,
                            }
                        ]
                    )
                ],
            }
        if "result['foreground']" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        {
                            "foreground": {"r": 0.1, "g": 0.2, "b": 0.3, "a": 1.0},
                            "background": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
                        }
                    )
                ],
            }
        if "drawable.get_pixel" in source:
            return {
                "status": "success",
                "results": [json.dumps({"r": 0.25, "g": 0.5, "b": 0.75, "a": 1.0})],
            }
        if "json.dumps(results)" in source and "lookup_procedure" in source:
            return {"status": "success", "results": [json.dumps(["gimp-blur", "plug-in-blur"])]}
        if "print(target.get_name())" in source or "print(dup.get_name())" in source:
            return {"status": "success", "results": ["Layer 1"]}
        if "print(json.dumps(result))" in source:
            return {"status": "success", "results": [json.dumps({"ok": True})]}
        return {"status": "success", "results": ["ok"]}

    async def async_evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        del timeout
        return {"status": "success", "results": [f"value:{expr}" for expr in expressions]}

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: BitmapRegion | None = None,
    ) -> PluginResponse:
        self.bitmap_calls.append(
            {"max_width": max_width, "max_height": max_height, "region": region}
        )
        return {
            "status": "success",
            "results": {
                "image_data": "iVBORw0KGgo=",
                "width": max_width or 320,
                "height": max_height or 200,
                "original_width": 320,
                "original_height": 200,
            },
        }

    async def async_get_image_metadata(self) -> PluginResponse:
        return {
            "status": "success",
            "results": {
                "basic": {"width": 320, "height": 200, "base_type": "RGB"},
                "layers": [{"name": "Layer 1", "visible": True}],
            },
        }

    async def async_get_context_state(self) -> PluginResponse:
        return {
            "status": "success",
            "results": {
                "foreground": "#000000",
                "background": "#ffffff",
                "brush": "2. Hardness 050",
            },
        }

    async def async_get_gimp_info(self) -> PluginResponse:
        return {
            "status": "success",
            "results": {
                "gimp": {"version": "3.2.4", "api_namespace": "3.0"},
                "pdb": {"file-png-export": True, "file-jpeg-export": True},
            },
        }


class FailingExecuteBridge(ScriptedToolBridge):
    """Bridge fake that raises for generated Python execution."""

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        del code_lines, timeout
        raise GimpCommandError("script failed", command="exec", traceback="Traceback")


class FailingInspectBridge(ScriptedToolBridge):
    """Bridge fake that returns transport-level failures for inspection methods."""

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: BitmapRegion | None = None,
    ) -> PluginResponse:
        del max_width, max_height, region
        return {"status": "error", "error": "bitmap unavailable"}

    async def async_get_image_metadata(self) -> PluginResponse:
        return {"status": "error", "error": "metadata unavailable"}

    async def async_get_context_state(self) -> PluginResponse:
        return {"status": "error", "error": "context unavailable"}

    async def async_get_gimp_info(self) -> PluginResponse:
        return {"status": "error", "error": "info unavailable"}


class FakeGimpDevAdapter:
    """Small gimp.dev adapter fake used by registration/invocation tests."""

    def status(self) -> dict[str, object]:
        """Return deterministic fake status data."""
        return {"enabled": True, "available": True, "root": "/fake/gimp.dev"}

    def load_catalog(self, *, validate: bool = True) -> dict[str, object]:
        """Return deterministic fake catalog data."""
        return {
            "plugins": [
                {
                    "name": "sprite-tools",
                    "validation_errors": [],
                    "procedures": [
                        {
                            "name": "python-fu-gimp-dev-sprite-sheet-plan",
                            "handler": "run_sheet_plan",
                            "commands": ["sprite.sheet.detect"],
                            "arguments": [{"name": "columns"}],
                        }
                    ],
                }
            ],
            "validation_errors": [],
        }

    def summarize_catalog(self, catalog: dict[str, object]):
        """Summarize fake catalog with the real adapter logic."""
        from gimp_mcp_pro.gimp_dev_integration import GimpDevAdapter

        return GimpDevAdapter().summarize_catalog(catalog)


def matrix_flow_registry_factory(_bridge: AsyncToolBridge) -> OperationRegistry:
    """Return a small operation registry for offline flow execution tests."""
    registry = OperationRegistry()

    @registry.tool()
    async def scale_image(width: int, height: int) -> dict[str, object]:
        return {"status": "success", "data": {"width": width, "height": height}}

    @registry.tool()
    async def apply_unsharp_mask() -> dict[str, object]:
        return {"status": "success"}

    return registry


def matrix_flow_store() -> FlowStore:
    """Create an isolated active flow store for independent matrix tool calls."""
    root = Path(tempfile.mkdtemp(prefix="gimp-mcp-flow-matrix-"))
    store = FlowStore(root)
    flow = FlowDefinition.model_validate(flow_payload())
    flow.state = "active"
    store.save(flow)
    return store


def registered_tools(bridge: AsyncToolBridge) -> dict[str, AsyncRegisteredTool]:
    """Register all tool groups against a bridge fake."""
    mcp = CaptureMCP()
    for register in [
        register_agent_tools,
        register_image_tools,
        register_layer_tools,
        register_selection_tools,
        register_path_tools,
        register_drawing_tools,
        register_inspect_tools,
        register_history_tools,
        register_pdb_tools,
        register_target_tools,
        register_transform_tools,
        register_filter_tools,
        register_color_tools,
        lambda mcp, bridge: register_gimp_dev_tools(mcp, bridge, FakeGimpDevAdapter()),
        lambda mcp, bridge: register_flow_tools(
            mcp, bridge, store=matrix_flow_store(), registry_factory=matrix_flow_registry_factory
        ),
    ]:
        register(mcp, bridge)
    return mcp.tools


TOOL_SUCCESS_CASES: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {
    "activate_flow": (("prepare-product-image",), {}),
    "add_alpha_channel": ((), {"layer_index": 0}),
    "add_layer_mask": ((), {"mask_type": "white", "layer_index": 0}),
    "add_guide": ((), {"orientation": "vertical", "position": 42}),
    "border_selection": ((2,), {}),
    "add_text": (("hello",), {"x": 1, "y": 2, "color": "#ff0000"}),
    "adjust_brightness_contrast": ((), {"brightness": 12, "contrast": -6}),
    "adjust_color_balance": ((), {"range": "shadows", "cyan_red": 10.0, "magenta_green": -5.0}),
    "analyze_color_palette": (
        (),
        {
            "max_colors": 5,
            "ignore_transparent": True,
            "region": {"x": 1, "y": 2, "width": 8, "height": 6},
            "layer_index": 0,
        },
    ),
    "assert_image_state": ((), {"assertions": []}),
    "adjust_curves": (([0.0, 0.0, 1.0, 1.0],), {}),
    "adjust_hue_saturation": ((), {"hue": 10, "saturation": 5, "lightness": -3}),
    "adjust_levels": ((), {"input_low": 10, "input_high": 240, "gamma": 1.1}),
    "apply_drop_shadow": ((), {"offset_x": 2, "offset_y": 3}),
    "apply_edge_detect": ((), {"method": "sobel", "amount": 1.2}),
    "apply_emboss": ((), {"azimuth": 300, "elevation": 40, "depth": 3}),
    "apply_gaussian_blur": ((), {"radius_x": 2.5, "radius_y": 1.5}),
    "apply_median": ((), {"radius": 2}),
    "apply_motion_blur": (
        (),
        {"blur_type": "linear", "length": 24.0, "angle": 37.5, "layer_name": "Speed"},
    ),
    "apply_noise": ((), {"amount": 0.1}),
    "apply_pixelize": ((), {"block_width": 8, "block_height": 6}),
    "apply_threshold": ((), {"low": 64, "high": 192}),
    "apply_unsharp_mask": ((), {"amount": 0.4, "radius": 2.0}),
    "auto_white_balance": ((), {}),
    "brush_inventory": (
        (),
        {"asset_types": ["brushes", "patterns", "palettes"], "filter": "Hardness", "limit": 12},
    ),
    "autocrop_image": ((), {}),
    "begin_edit_transaction": ((), {"label": "matrix", "capture_before_state": True}),
    "begin_undo_group": ((), {"name": "matrix"}),
    "bucket_fill": ((10, 12), {"color": "red", "threshold": 51.0, "sample_merged": True}),
    "color_to_alpha": ((), {"color": "white"}),
    "create_image": ((320, 200), {"color_mode": "rgb", "fill": "white"}),
    "compare_snapshots": (
        (),
        {"before": {"dimensions": {"width": 1}}, "after": {"dimensions": {"width": 2}}},
    ),
    "create_layer": ((), {"name": "Paint", "opacity": 80, "fill": "transparent"}),
    "create_layer_group": ((), {"name": "Group A", "position": 0}),
    "create_contact_sheet": (
        (),
        {"target": "visible_layers", "max_tile_size": 96, "label_tiles": True},
    ),
    "content_bounds": ((), {"target": "active_layer", "threshold": 0.05}),
    "create_checkpoint": ((), {"label": "matrix checkpoint", "include_xcf_copy": False}),
    "crop_image": ((1, 2, 100, 80), {}),
    "commit_filter_preview": (
        ("Preview: gegl:gaussian-blur", "commit"),
        {"committed_name": "Committed blur"},
    ),
    "crop_to_selection": ((), {}),
    "deactivate_flow": (("prepare-product-image",), {}),
    "delete_layer": ((), {"layer_index": 0}),
    "delete_guide": ((7,), {}),
    "desaturate": ((), {"method": "luminosity"}),
    "draw_brush_stroke": (([0, 0, 10, 10, 20, 5],), {"tool": "pencil"}),
    "dry_run_macro": (
        ([{"tool": "scale_image", "arguments": {"width": 320, "height": 200}}],),
        {},
    ),
    "draw_ellipse": ((2, 3, 40, 20), {"filled": False, "color": "blue"}),
    "draw_line": ((0, 0, 20, 10), {"color": "black", "brush_size": 3}),
    "draw_polygon": (([0, 0, 10, 0, 5, 8],), {"filled": True}),
    "draw_rectangle": ((1, 2, 30, 40), {"filled": True, "color": "#00ff00"}),
    "duplicate_image": ((), {}),
    "duplicate_layer": ((), {"layer_index": 0, "new_name": "Copy"}),
    "edit_clear": ((), {}),
    "edit_text_layer": ((), {"text": "updated", "layer_name": "Text", "font_size": 18.0}),
    "text_layer_introspection": ((), {"layer_name": "Headline"}),
    "end_edit_transaction": ((), {}),
    "end_undo_group": ((), {}),
    "execute_python": (
        (["print('ok')"],),
        {"timeout_seconds": 1.0, "require_debug_enabled": True, "allow_dangerous_code": True},
    ),
    "explain_current_context": ((), {"detail_level": "high", "include_recommendations": True}),
    "export_image": (("/tmp/gimp-mcp-test.png",), {"format": "png", "quality": 90}),
    "fill_selection": ((), {"fill_type": "foreground", "color": "red"}),
    "flatten_image": ((), {}),
    "flip_image": ((), {"direction": "vertical"}),
    "flip_layer": ((), {"direction": "horizontal", "layer_index": 0}),
    "get_flow": (("prepare-product-image",), {}),
    "get_colors": ((), {}),
    "get_context_state": ((), {}),
    "get_gimp_info": ((), {}),
    "get_image_bitmap": ((), {"max_width": 64, "max_height": 48}),
    "gimp_dev_plugin_catalog": ((), {"include_raw_catalog": True}),
    "gimp_dev_status": ((), {}),
    "get_image_info": ((), {}),
    "get_image_metadata": ((), {}),
    "get_layer_mask_info": ((), {"layer_index": 0}),
    "generate_layer_report": ((), {"include_previews": False, "include_warnings": True}),
    "get_operation_log": ((), {"limit": 5}),
    "get_selection_info": ((), {}),
    "gradient_fill": (
        (0, 0, 64, 32),
        {"gradient_type": "linear", "foreground_color": "black", "background_color": "white"},
    ),
    "invert_colors": ((), {}),
    "list_flows": ((), {}),
    "list_gimp_resources": ((), {"resource_type": "all", "limit": 5}),
    "list_guides": ((), {}),
    "list_images": ((), {}),
    "list_layers": ((), {}),
    "list_channels": ((), {}),
    "list_paths": ((), {}),
    "merge_visible_layers": ((), {}),
    "new_layer_from_visible": ((), {"name": "Visible Snapshot", "position": 0}),
    "merge_down": ((), {"layer_index": 0, "merge_type": "clip_to_image"}),
    "copy_layer_alpha_to_mask": (
        (),
        {"source_layer_index": 0, "target_layer_index": 1, "replace_existing": True},
    ),
    "move_layer_to_group": ((), {"layer_index": 0, "group_name": "Group A", "position": 0}),
    "measure_geometry": (
        (),
        {
            "targets": [{"layer_name": "A"}, {"layer_name": "B"}],
            "measurements": ["bounds", "distance", "overlap", "alignment", "spacing"],
        },
    ),
    "offset_layer": ((5, -3), {"layer_index": 0}),
    "pin_flow": (("prepare-product-image",), {}),
    "path_to_selection": ((), {"path_name": "Path 1"}),
    "perspective_layer": (
        (0, 4, 80, 0, 8, 60, 72, 64),
        {"interpolation": "cubic", "resize": "adjust", "layer_name": "Photo"},
    ),
    "propose_flow": ((flow_payload(),), {}),
    "preview_filter": (
        (),
        {
            "filter": "gaussian_blur",
            "parameters": {"radius_x": 3.0, "radius_y": 4.0},
            "layer_index": 0,
        },
    ),
    "prepare_export_checklist": (
        (),
        {
            "formats": ["png", "jpeg", "xcf"],
            "require_alpha": True,
            "require_layers_preserved": True,
        },
    ),
    "posterize": ((), {"levels": 5}),
    "redo": ((), {"steps": 1}),
    "remove_layer_mask": ((), {"apply": False, "layer_index": 0}),
    "remove_path": ((), {"path_name": "Path 1"}),
    "rollback_transaction": ((), {}),
    "resize_canvas": ((400, 250), {"offset_x": 2, "offset_y": 3}),
    "smart_crop_or_resize": (
        (),
        {
            "mode": "crop",
            "target_size": {"width": 320, "height": 200},
            "anchor": "center",
            "dry_run": True,
        },
    ),
    "create_path": (([0, 0, 20, 0, 20, 20],), {"name": "Path 1", "closed": True}),
    "run_flow": (("prepare-product-image", {"width": 800, "image": 1, "sharpen": False}), {}),
    "run_macro_transaction": (
        ([{"tool": "scale_image", "arguments": {"width": 320, "height": 200}}],),
        {"transaction_label": "matrix macro"},
    ),
    "rotate_image": ((90,), {}),
    "rotate_layer": ((15.0,), {"layer_index": 0}),
    "sample_color": ((4, 5), {"sample_merged": False}),
    "sample_pixels": (([{"x": 1, "y": 2}, {"x": 3, "y": 4}],), {"sample_merged": True}),
    "scale_image": ((640, 480), {"interpolation": "cubic"}),
    "scale_layer": ((128, 96), {"interpolation": "linear", "layer_index": 0}),
    "save_selection_to_channel": ((), {"name": "Saved alpha"}),
    "search_pdb": (("blur",), {"max_results": 5}),
    "select_by_color": ((4, 5), {"threshold": 20.0}),
    "select_layer_alpha": ((), {"layer_index": 0, "operation": "replace"}),
    "select_all": ((), {}),
    "select_ellipse": ((1, 2, 30, 40), {"operation": "replace"}),
    "feather_selection": ((2.5,), {}),
    "select_grow": ((3,), {}),
    "select_invert": ((), {}),
    "select_none": ((), {}),
    "select_polygon": (([0, 0, 20, 0, 10, 12],), {}),
    "select_rectangle": ((1, 2, 30, 40), {"feather_radius": 1.0}),
    "select_shrink": ((2,), {}),
    "observe_document_state": ((), {"include_thumbnail": True, "max_preview_size": 64}),
    "observe_region": ((1, 2, 30, 40), {"max_size": 64}),
    "get_layer_tree_detailed": ((), {}),
    "resolve_target": (("Layer 1",), {"target_types": ["layer"], "require_unique": True}),
    "session_capabilities": ((), {}),
    "set_active_layer": ((), {"layer_index": 0}),
    "set_image_grid": (
        (),
        {
            "xspacing": 16.0,
            "yspacing": 24.0,
            "xoffset": 2.0,
            "yoffset": 3.0,
            "style": "intersections",
        },
    ),
    "shear_layer": (
        (),
        {
            "direction": "vertical",
            "magnitude": -12.5,
            "interpolation": "linear",
            "resize": "clip",
            "layer_index": 0,
        },
    ),
    "set_background_color": (("#ffffff",), {}),
    "set_paint_context": (
        (),
        {
            "brush": "2. Hardness 050",
            "size": 12.5,
            "opacity": 80.0,
            "pattern": "Pine",
            "gradient": "FG to BG (RGB)",
            "foreground": "#112233",
            "background": "#ffffff",
        },
    ),
    "set_paint_resource": (("brush", "2. Hardness 050"), {}),
    "set_foreground_color": (("#000000",), {}),
    "set_layer_mask_state": (
        (),
        {"edit_mask": True, "show_mask": False, "apply_mask": True, "layer_index": 0},
    ),
    "set_layer_mode": (("multiply",), {"layer_index": 0}),
    "set_layer_blend_mode": (("multiply",), {"layer_index": 0}),
    "set_layer_opacity": ((75.0,), {"layer_index": 0}),
    "set_layer_visibility": ((False,), {"layer_index": 0}),
    "stroke_path": ((), {"path_name": "Path 1", "color": "black", "brush_size": 2.0}),
    "channel_to_selection": ((), {"channel_name": "Saved alpha", "operation": "add"}),
    "stroke_selection": ((), {"color": "black", "brush_size": 2.0}),
    "swap_colors": ((), {}),
    "validate_flow": (("prepare-product-image",), {}),
    "validate_targets": (
        ([{"kind": "layer", "id": 201}],),
        {"required_capabilities": ["visible", "editable"]},
    ),
    "unpin_flow": (("prepare-product-image",), {}),
    "undo": ((), {"steps": 1}),
}

TOOL_SUCCESS_CASES.update(
    {name: ((), case["kwargs"]) for name, case in PROMOTED_TOOL_CASES.items()}
)
TOOL_SUCCESS_CASES.update(
    {
        "align_and_distribute_layers": (
            (),
            {
                "layers": [{"layer_name": "A"}, {"layer_name": "B"}],
                "align": "center_x",
                "distribute": "horizontal",
                "reference": "canvas",
                "dry_run": True,
            },
        ),
        "color_management_profile": ((), {"action": "inspect"}),
        "create_text_box": (
            (),
            {
                "text": "Hello",
                "rectangle": {"x": 12, "y": 24, "width": 320, "height": 80},
                "style": {"font": "Sans", "font_size": 24, "color": "#445566", "justify": "center"},
                "name": "Title text",
            },
        ),
        "create_visual_annotation_layer": (
            (),
            {
                "annotations": [
                    {"type": "box", "x": 1, "y": 2, "width": 10, "height": 12, "color": "#ff0000"}
                ],
                "temporary": True,
            },
        ),
        "export_with_manifest": (
            (),
            {"format": "png", "destination": "/tmp/gimp-mcp-export.png", "include_sidecar": False},
        ),
        "find_similar_regions": (
            (),
            {
                "color": "#112233",
                "alpha_range": {"min": 0.25, "max": 1.0},
                "region": {"x": 10, "y": 20, "width": 100, "height": 80},
                "tolerance": 0.12,
                "max_regions": 8,
            },
        ),
        "layer_version_stamp": (
            (),
            {"target": {"layer_name": "Layer 1"}, "metadata": {"operation": "test"}, "merge": True},
        ),
        "remove_visual_annotations": ((), {"remove_all_mcp_annotations": True}),
        "resource_catalog": (
            (),
            {"resource_type": "brush", "query": "Hardness", "limit": 10, "include_optional": True},
        ),
    }
)


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(TOOL_SUCCESS_CASES))
async def test_all_async_tools_have_offline_success_path(tool_name: str) -> None:
    """Exercise every async tool through its public MCP-facing coroutine."""
    bridge = ScriptedToolBridge()
    tools = registered_tools(bridge)
    args, kwargs = TOOL_SUCCESS_CASES[tool_name]

    result = await tools[tool_name](*args, **kwargs)

    assert result["success"] is True
    assert result["operation"] == tool_name
    assert "message" in result


def test_success_matrix_tracks_complete_tool_registry() -> None:
    """Fail when a new tool is registered without an offline invocation case."""
    tools = registered_tools(ScriptedToolBridge())

    assert set(TOOL_SUCCESS_CASES) == set(tools)
    assert len(TOOL_SUCCESS_CASES) == 176


@pytest.mark.asyncio
async def test_region_bitmap_invocation_passes_structured_region() -> None:
    """Partial bitmap requests pass a complete structured region to the bridge."""
    bridge = ScriptedToolBridge()
    tools = registered_tools(bridge)

    result = await tools["get_image_bitmap"](
        region_x=1,
        region_y=2,
        region_width=30,
        region_height=40,
    )

    assert result["success"] is True
    assert bridge.bitmap_calls[-1]["region"] == {
        "origin_x": 1,
        "origin_y": 2,
        "width": 30,
        "height": 40,
    }


@pytest.mark.asyncio
async def test_inspection_transport_errors_return_structured_failures() -> None:
    """Inspection tools map error envelopes into OperationResult failures."""
    tools = registered_tools(FailingInspectBridge())

    for tool_name in [
        "get_image_bitmap",
        "get_image_metadata",
        "get_context_state",
        "get_gimp_info",
    ]:
        result = await tools[tool_name]()
        assert result["success"] is False
        assert result["operation"] == tool_name
        assert result["error"]


@pytest.mark.asyncio
async def test_execute_python_failure_preserves_gimp_traceback() -> None:
    """Raw Python escape-hatch failures retain GIMP traceback metadata."""
    tools = registered_tools(FailingExecuteBridge())

    result = await tools["execute_python"](
        ["raise RuntimeError('boom')"], require_debug_enabled=True, allow_dangerous_code=True
    )

    assert result["success"] is False
    assert result["operation"] == "execute_python"
    assert result["data"] == {"gimp_traceback": "Traceback"}


@pytest.mark.asyncio
async def test_validation_failures_do_not_call_bridge() -> None:
    """Fast validation failures return before crossing the bridge boundary."""
    bridge = ScriptedToolBridge()
    tools = registered_tools(bridge)

    invalid_results = [
        await tools["draw_polygon"]([0, 0, 1, 1]),
        await tools["select_polygon"]([0, 0, 1, 1]),
        await tools["get_image_bitmap"](region_x=1, region_y=2),
        await tools["execute_python"]([]),
        await tools["rotate_image"](45),
        await tools["set_active_layer"](),
        await tools["observe_region"](1, 2, 0, 5),
        await tools["observe_document_state"](max_preview_size=0),
        await tools["resolve_target"](""),
        await tools["validate_targets"]([]),
        await tools["create_path"]([0, 0, 1, 1]),
        await tools["set_layer_mask_state"](),
    ]

    assert all(result["success"] is False for result in invalid_results)
    assert bridge.execute_calls == []
    assert bridge.bitmap_calls == []


@pytest.mark.asyncio
async def test_mask_path_selection_tools_generate_valid_gimp_324_api_calls() -> None:
    """New mask/path/selection helpers use GIMP 3.0 introspected APIs."""
    bridge = ScriptedToolBridge()
    tools = registered_tools(bridge)

    calls = [
        ("add_layer_mask", (), {"mask_type": "selection", "layer_name": "Layer 1"}),
        (
            "set_layer_mask_state",
            (),
            {"edit_mask": True, "show_mask": True, "apply_mask": False, "layer_name": "Layer 1"},
        ),
        ("remove_layer_mask", (), {"apply": True, "layer_name": "Layer 1"}),
        ("feather_selection", (3.5,), {}),
        ("border_selection", (2,), {}),
        ("stroke_selection", (), {"color": "#000000", "brush_size": 2.0}),
        ("create_path", ([0, 0, 20, 0, 20, 20],), {"name": "Triangle", "closed": True}),
        ("path_to_selection", (), {"path_name": "Triangle", "operation": "replace"}),
        ("stroke_path", (), {"path_name": "Triangle", "color": "black", "brush_size": 2.0}),
        ("remove_path", (), {"path_name": "Triangle"}),
    ]
    for name, args, kwargs in calls:
        result = await tools[name](*args, **kwargs)
        assert result["success"] is True, (name, result)

    generated = "\n".join("\n".join(call) for call in bridge.execute_calls)
    assert "target.create_mask(Gimp.AddMaskType.SELECTION)" in generated
    assert "target.add_mask(mask)" in generated
    assert "target.set_edit_mask(True)" in generated
    assert "target.remove_mask(Gimp.MaskApplyMode.APPLY)" in generated
    assert "Gimp.Selection.feather(images[0], 3.5)" in generated
    assert "Gimp.Selection.border(images[0], 2)" in generated
    assert "Gimp.Drawable.edit_stroke_selection(drawable)" in generated
    assert "path = Gimp.Path.new(image, 'Triangle')" in generated
    assert "path.stroke_new_from_points(Gimp.PathStrokeType.BEZIER" in generated
    assert "image.select_item(Gimp.ChannelOps.REPLACE, target)" in generated
    assert "drawable.edit_stroke_item(target)" in generated
    assert "image.remove_path(target)" in generated


@pytest.mark.asyncio
async def test_execute_python_joins_lines_into_single_script_for_blocks() -> None:
    bridge = ScriptedToolBridge()
    tools = registered_tools(bridge)

    result = await tools["execute_python"](
        ["for i in range(2):", "    print(i)"],
        require_debug_enabled=True,
        allow_dangerous_code=True,
    )

    assert result["success"] is True
    assert bridge.execute_calls[-1] == ["for i in range(2):\n    print(i)"]
    assert result["data"]["script_executed"] is True
