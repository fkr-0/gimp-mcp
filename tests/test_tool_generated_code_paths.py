"""Generated-code coverage for the async MCP tool surface.

These tests deliberately avoid a live GIMP process. They exercise the public MCP
handlers against a scripted async bridge so the Python code-generation, parameter
normalisation, and structured OperationResult paths stay covered by fast unit
runs. Live symbol/API coverage remains in tests/live_gimp_324_smoke.py.
"""

from __future__ import annotations

import inspect
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

from gimp_mcp_pro.flows.models import FlowDefinition
from gimp_mcp_pro.flows.operations import OperationRegistry
from gimp_mcp_pro.flows.store import FlowStore
from gimp_mcp_pro.protocol import BitmapRegion, CommandParams, PluginResponse
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
from gimp_mcp_pro.utils.errors import GimpCommandError
from tests.promoted_tool_cases import PROMOTED_TOOL_CASES
from tests.test_flow_models import flow_payload

Tool = Callable[..., Awaitable[dict[str, Any]]]


class CaptureMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[Tool], Tool]:
        def decorator(fn: Tool) -> Tool:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class ScriptedBridge:
    """Async bridge that records all generated calls and returns useful fixtures."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def async_send_command(
        self,
        command_type: str,
        params: CommandParams | None = None,
        timeout: float | None = None,
    ) -> PluginResponse:
        self.calls.append(
            ("send_command", {"type": command_type, "params": params, "timeout": timeout})
        )
        return {"status": "success", "results": {"command": command_type}}

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        self.calls.append(("execute_python", code_lines))
        joined = "\n".join(code_lines)
        if "json.dumps" in joined or "print(json" in joined:
            return {"status": "success", "results": ["{}"]}
        return {"status": "success", "results": ["ok"]}

    async def async_evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        self.calls.append(("evaluate_python", expressions))
        values: list[Any] = []
        for expression in expressions:
            if "query_procedures" in expression:
                values.append(["file-png-export", "file-jpeg-export"])
            elif "procedure_exists" in expression:
                values.append(True)
            elif "get_name" in expression:
                values.append("Mock image")
            elif "get_width" in expression:
                values.append(320)
            elif "get_height" in expression:
                values.append(240)
            elif "get_layers" in expression:
                values.append([])
            else:
                values.append("ok")
        return {"status": "success", "results": values}

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: BitmapRegion | None = None,
    ) -> PluginResponse:
        self.calls.append(
            (
                "get_image_bitmap",
                {"max_width": max_width, "max_height": max_height, "region": region},
            )
        )
        return {
            "status": "success",
            "results": {
                "image_data": "iVBORw0KGgo=",
                "format": "png",
                "width": max_width or 64,
                "height": max_height or 64,
                "original_width": 320,
                "original_height": 240,
                "encoding": "base64",
            },
        }

    async def async_get_image_metadata(self) -> PluginResponse:
        self.calls.append(("get_image_metadata", None))
        return {
            "status": "success",
            "results": {
                "basic": {"width": 320, "height": 240, "base_type": "rgb"},
                "layers": [],
            },
        }

    async def async_get_context_state(self) -> PluginResponse:
        self.calls.append(("get_context_state", None))
        return {
            "status": "success",
            "results": {
                "foreground": "#000000",
                "background": "#ffffff",
                "brush": "2. Hardness 050",
            },
        }

    async def async_get_gimp_info(self) -> PluginResponse:
        self.calls.append(("get_gimp_info", None))
        return {
            "status": "success",
            "results": {
                "gimp": {"version": "3.2.4"},
                "python": {"version": "3.13"},
            },
        }


class FailingBridge(ScriptedBridge):
    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        self.calls.append(("execute_python", code_lines))
        raise GimpCommandError("boom", command="execute_python")

    async def async_evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        self.calls.append(("evaluate_python", expressions))
        raise GimpCommandError("boom", command="evaluate_python")

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: BitmapRegion | None = None,
    ) -> PluginResponse:
        self.calls.append(("get_image_bitmap", None))
        raise GimpCommandError("boom", command="get_image_bitmap")

    async def async_get_image_metadata(self) -> PluginResponse:
        self.calls.append(("get_image_metadata", None))
        raise GimpCommandError("boom", command="get_image_metadata")

    async def async_get_context_state(self) -> PluginResponse:
        self.calls.append(("get_context_state", None))
        raise GimpCommandError("boom", command="get_context_state")

    async def async_get_gimp_info(self) -> PluginResponse:
        self.calls.append(("get_gimp_info", None))
        raise GimpCommandError("boom", command="get_gimp_info")


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


LOCAL_TOOL_NAMES = {"compare_snapshots", "get_operation_log"}

FLOW_TOOL_NAMES = {
    "propose_flow",
    "list_flows",
    "get_flow",
    "validate_flow",
    "activate_flow",
    "deactivate_flow",
    "pin_flow",
    "unpin_flow",
    "run_flow",
    "dry_run_macro",
    "run_macro_transaction",
}


def generated_flow_registry_factory(_bridge: ScriptedBridge) -> OperationRegistry:
    """Return a small operation registry for generated-code flow tests."""
    registry = OperationRegistry()

    @registry.tool()
    async def scale_image(width: int, height: int) -> dict[str, object]:
        return {"status": "success", "data": {"width": width, "height": height}}

    @registry.tool()
    async def apply_unsharp_mask() -> dict[str, object]:
        return {"status": "success"}

    return registry


def generated_flow_store() -> FlowStore:
    """Create an isolated active flow store for generated-code tests."""
    root = Path(tempfile.mkdtemp(prefix="gimp-mcp-generated-flow-"))
    store = FlowStore(root)
    flow = FlowDefinition.model_validate(flow_payload())
    flow.state = "active"
    store.save(flow)
    return store


def registered_tools(bridge: ScriptedBridge) -> dict[str, Tool]:
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
            mcp,
            bridge,
            store=generated_flow_store(),
            registry_factory=generated_flow_registry_factory,
        ),
    ]:
        register(mcp, bridge)
    return mcp.tools


SUCCESS_TOOL_ARGS: dict[str, dict[str, Any]] = {
    "activate_flow": {"flow_id": "prepare-product-image"},
    "add_text": {"text": "hello 'quoted' world", "layer_name": "text-layer"},
    "add_layer_mask": {"mask_type": "white", "layer_index": 0},
    "add_guide": {"orientation": "vertical", "position": 42},
    "border_selection": {"radius": 2},
    "adjust_color_balance": {"range": "midtones", "cyan_red": 8.0},
    "brush_inventory": {
        "asset_types": ["brushes", "patterns", "palettes"],
        "filter": "Hardness",
        "limit": 12,
    },
    "analyze_color_palette": {
        "max_colors": 5,
        "ignore_transparent": True,
        "region": {"x": 1, "y": 2, "width": 8, "height": 6},
        "layer_index": 0,
    },
    "assert_image_state": {"assertions": []},
    "adjust_curves": {"control_points": [0.0, 0.0, 1.0, 1.0]},
    "begin_edit_transaction": {"label": "generated", "capture_before_state": True},
    "bucket_fill": {"x": 10, "y": 12, "color": "red", "threshold": 51.0, "sample_merged": True},
    "create_image": {"width": 64, "height": 48},
    "compare_snapshots": {
        "before": {"dimensions": {"width": 1}},
        "after": {"dimensions": {"width": 2}},
    },
    "create_layer_group": {"name": "Group A", "position": 0},
    "copy_layer_alpha_to_mask": {
        "source_layer_index": 0,
        "target_layer_index": 1,
        "replace_existing": True,
    },
    "create_mask_from_color": {
        "color": "#ffffff",
        "target_layer_index": 0,
        "replace_existing": True,
    },
    "create_contact_sheet": {"target": "visible_layers", "max_tile_size": 96, "label_tiles": True},
    "content_bounds": {"target": "active_layer", "threshold": 0.05, "include_sample_points": True},
    "create_checkpoint": {"label": "matrix checkpoint", "include_xcf_copy": False},
    "crop_image": {"x": 1, "y": 2, "width": 32, "height": 24},
    "commit_filter_preview": {
        "preview_id": "Preview: gegl:gaussian-blur",
        "action": "commit",
        "committed_name": "Committed blur",
    },
    "delete_layer": {"layer_index": 0},
    "delete_guide": {"guide_id": 7},
    "deactivate_flow": {"flow_id": "prepare-product-image"},
    "draw_brush_stroke": {"points": [0, 0, 10, 10, 20, 0, 30, 10]},
    "dry_run_macro": {
        "steps": [
            {"tool": "scale_image", "arguments": {"width": 320, "height": 200}},
        ]
    },
    "draw_ellipse": {"x": 2, "y": 3, "width": 12, "height": 8},
    "draw_line": {"x1": 0, "y1": 0, "x2": 16, "y2": 16},
    "draw_polygon": {"points": [0, 0, 20, 0, 20, 20]},
    "draw_rectangle": {"x": 1, "y": 1, "width": 12, "height": 8},
    "edit_text_layer": {"text": "updated", "layer_index": 0},
    "text_layer_introspection": {"layer_name": "Headline", "include_font_details": True},
    "end_edit_transaction": {},
    "execute_python": {
        "code": ["x = 1", "print(x)"],
        "require_debug_enabled": True,
        "allow_dangerous_code": True,
    },
    "explain_current_context": {"detail_level": "high", "include_recommendations": True},
    "export_image": {"file_path": "/tmp/gimp-mcp-test.png"},
    "gimp_dev_status": {},
    "gimp_dev_plugin_catalog": {"include_raw_catalog": True, "validate": False},
    "get_image_bitmap": {"max_width": 32, "max_height": 24},
    "get_flow": {"flow_id": "prepare-product-image"},
    "gradient_fill": {
        "x1": 0,
        "y1": 0,
        "x2": 64,
        "y2": 32,
        "gradient_type": "linear",
        "foreground_color": "black",
        "background_color": "white",
    },
    "get_layer_mask_info": {"layer_index": 0},
    "generate_layer_report": {
        "include_previews": False,
        "include_warnings": True,
        "include_markdown": True,
    },
    "list_channels": {},
    "list_gimp_resources": {"resource_type": "all", "limit": 5},
    "list_guides": {},
    "get_selection_info": {},
    "fuzzy_select": {"x": 4, "y": 5, "threshold": 20.0},
    "list_paths": {},
    "offset_layer": {"offset_x": 4, "offset_y": 5},
    "move_layer_to_group": {"layer_index": 0, "group_name": "Group A", "position": 0},
    "measure_geometry": {
        "targets": [{"layer_name": "A"}, {"layer_name": "B"}],
        "measurements": ["bounds", "distance", "overlap", "alignment", "spacing"],
    },
    "observe_region": {"x": 0, "y": 0, "width": 16, "height": 16},
    "resize_canvas": {"new_width": 128, "new_height": 96},
    "path_to_selection": {"path_name": "Path 1"},
    "perspective_layer": {
        "x0": 0,
        "y0": 4,
        "x1": 80,
        "y1": 0,
        "x2": 8,
        "y2": 60,
        "x3": 72,
        "y3": 64,
        "interpolation": "cubic",
        "resize": "adjust",
        "layer_name": "Photo",
    },
    "pin_flow": {"flow_id": "prepare-product-image"},
    "propose_flow": {"definition": flow_payload()},
    "preview_filter": {
        "filter": "gaussian_blur",
        "parameters": {"radius_x": 3.0, "radius_y": 4.0},
        "layer_index": 0,
    },
    "prepare_export_checklist": {
        "formats": ["png", "jpeg", "xcf"],
        "require_alpha": True,
        "require_layers_preserved": True,
    },
    "replace_color": {"source_color": "white", "replacement_color": "black"},
    "remove_layer_mask": {"apply": False, "layer_index": 0},
    "remove_path": {"path_name": "Path 1"},
    "rollback_transaction": {},
    "run_flow": {
        "flow_id": "prepare-product-image",
        "parameters": {"width": 640, "image": 1, "sharpen": False},
    },
    "run_macro_transaction": {
        "steps": [
            {"tool": "scale_image", "arguments": {"width": 320, "height": 200}},
        ],
        "transaction_label": "generated macro",
    },
    "rotate_image": {"angle": 90},
    "rotate_layer": {"angle_degrees": 15.0},
    "sample_color": {"x": 2, "y": 3},
    "sample_pixels": {"points": [{"x": 1, "y": 2}, {"x": 3, "y": 4}], "sample_merged": True},
    "create_path": {"points": [0, 0, 20, 0, 20, 20], "name": "Path 1", "closed": True},
    "scale_image": {"new_width": 128, "new_height": 96},
    "scale_layer": {"new_width": 32, "new_height": 24},
    "save_selection_to_channel": {"name": "Saved alpha"},
    "search_pdb": {"query": "png"},
    "select_color": {"color": "#ffffff", "threshold": 20.0},
    "select_by_color": {"x": 4, "y": 5, "threshold": 20.0},
    "select_ellipse": {"x": 2, "y": 3, "width": 12, "height": 8},
    "feather_selection": {"radius": 2.5},
    "select_grow": {"radius": 2},
    "select_polygon": {"points": [0, 0, 20, 0, 20, 20]},
    "select_rectangle": {"x": 2, "y": 3, "width": 12, "height": 8},
    "select_shrink": {"radius": 1},
    "set_active_layer": {"layer_index": 0},
    "set_image_grid": {
        "xspacing": 16.0,
        "yspacing": 24.0,
        "xoffset": 2.0,
        "yoffset": 3.0,
        "style": "intersections",
    },
    "set_background_color": {"color": "#ffffff"},
    "set_paint_context": {
        "brush": "2. Hardness 050",
        "size": 12.5,
        "opacity": 80.0,
        "pattern": "Pine",
        "gradient": "FG to BG (RGB)",
        "foreground": "#112233",
        "background": "#ffffff",
    },
    "set_paint_resource": {"resource_type": "brush", "name": "2. Hardness 050"},
    "smart_crop_or_resize": {
        "mode": "crop",
        "target_size": {"width": 320, "height": 200},
        "anchor": "center",
        "dry_run": True,
    },
    "set_foreground_color": {"color": "#000000"},
    "set_layer_mask_state": {
        "edit_mask": True,
        "show_mask": False,
        "apply_mask": True,
        "layer_index": 0,
    },
    "set_layer_mode": {"blend_mode": "multiply", "layer_index": 0},
    "set_layer_blend_mode": {"blend_mode": "multiply", "layer_index": 0},
    "set_layer_opacity": {"opacity": 42},
    "resolve_target": {"query": "Background", "target_types": ["layer"]},
    "validate_targets": {"targets": [{"type": "layer", "name": "Background"}]},
    "set_layer_visibility": {"visible": False},
    "shear_layer": {
        "direction": "vertical",
        "magnitude": -12.5,
        "interpolation": "nohalo",
        "resize": "crop",
        "layer_index": 0,
    },
    "stroke_path": {"path_name": "Path 1", "color": "black", "brush_size": 2.0},
    "channel_to_selection": {"channel_name": "Saved alpha", "operation": "add"},
    "stroke_selection": {"color": "black", "brush_size": 2.0},
    "unpin_flow": {"flow_id": "prepare-product-image"},
    "validate_flow": {"flow_id": "prepare-product-image"},
}

SUCCESS_TOOL_ARGS.update({name: case["kwargs"] for name, case in PROMOTED_TOOL_CASES.items()})
SUCCESS_TOOL_ARGS.update(
    {
        "align_and_distribute_layers": {
            "layers": [{"layer_name": "A"}, {"layer_name": "B"}],
            "align": "center_x",
            "distribute": "horizontal",
            "reference": "canvas",
            "dry_run": True,
        },
        "color_management_profile": {"action": "inspect"},
        "create_text_box": {
            "text": "Hello",
            "rectangle": {"x": 12, "y": 24, "width": 320, "height": 80},
            "style": {"font": "Sans", "font_size": 24, "color": "#445566", "justify": "center"},
            "name": "Title text",
        },
        "create_visual_annotation_layer": {
            "annotations": [
                {"type": "box", "x": 1, "y": 2, "width": 10, "height": 12, "color": "#ff0000"}
            ],
            "temporary": True,
        },
        "export_with_manifest": {
            "format": "png",
            "destination": "/tmp/gimp-mcp-export.png",
            "include_sidecar": False,
        },
        "find_similar_regions": {
            "color": "#112233",
            "alpha_range": {"min": 0.25, "max": 1.0},
            "region": {"x": 10, "y": 20, "width": 100, "height": 80},
            "tolerance": 0.12,
            "max_regions": 8,
        },
        "layer_version_stamp": {
            "target": {"layer_name": "Layer 1"},
            "metadata": {"operation": "test"},
            "merge": True,
        },
        "remove_visual_annotations": {"remove_all_mcp_annotations": True},
        "resource_catalog": {
            "resource_type": "brush",
            "query": "Hardness",
            "limit": 10,
            "include_optional": True,
        },
    }
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name",
    [
        name
        for name in sorted(registered_tools(ScriptedBridge()).keys())
        if name != "validate_targets"
    ],
)
async def test_all_tools_have_fast_success_path(tool_name: str) -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    tool = tools[tool_name]
    kwargs = SUCCESS_TOOL_ARGS.get(tool_name, {})

    result = await tool(**kwargs)

    assert result["success"] is True, f"{tool_name} returned {result!r}"
    assert inspect.iscoroutinefunction(tool)
    if (
        not tool_name.startswith("gimp_dev_")
        and tool_name not in FLOW_TOOL_NAMES
        and tool_name not in LOCAL_TOOL_NAMES
    ):
        assert bridge.calls, f"{tool_name} did not touch the async bridge"


@pytest.mark.asyncio
async def test_generated_layer_names_are_python_literal_escaped() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    hostile_name = "layer 'quote'\nwith newline"

    result = await tools["adjust_brightness_contrast"](layer_name=hostile_name)

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert f"get_layer_by_name({repr(hostile_name)})" in generated
    assert "get_layer_by_name(layer" not in generated


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "kwargs"),
    [
        ("create_image", {"width": 64, "height": 48}),
        ("create_layer", {}),
        ("select_rectangle", {"x": 1, "y": 2, "width": 3, "height": 4}),
        ("draw_rectangle", {"x": 1, "y": 2, "width": 3, "height": 4}),
        ("scale_image", {"new_width": 20, "new_height": 10}),
        ("adjust_brightness_contrast", {}),
        ("apply_gaussian_blur", {}),
        ("undo", {}),
        ("search_pdb", {"query": "png"}),
        ("get_image_bitmap", {}),
        ("get_image_info", {}),
        ("get_context_state", {}),
        ("get_gimp_info", {}),
    ],
)
async def test_tools_return_structured_failures_on_bridge_error(
    tool_name: str, kwargs: dict[str, Any]
) -> None:
    bridge = FailingBridge()
    tools = registered_tools(bridge)

    result = await tools[tool_name](**kwargs)

    assert result["success"] is False
    assert result["operation"] == tool_name
    assert "boom" in result["error"]
