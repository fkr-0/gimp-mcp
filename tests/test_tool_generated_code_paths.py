"""Generated-code coverage for the async MCP tool surface.

These tests deliberately avoid a live GIMP process. They exercise the public MCP
handlers against a scripted async bridge so the Python code-generation, parameter
normalisation, and structured OperationResult paths stay covered by fast unit
runs. Live symbol/API coverage remains in tests/live_gimp_324_smoke.py.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from gimp_mcp_pro.protocol import BitmapRegion, CommandParams, PluginResponse
from gimp_mcp_pro.tools.color_tools import register_color_tools
from gimp_mcp_pro.tools.drawing_tools import register_drawing_tools
from gimp_mcp_pro.tools.filter_tools import register_filter_tools
from gimp_mcp_pro.tools.history_tools import register_history_tools
from gimp_mcp_pro.tools.image_tools import register_image_tools
from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools
from gimp_mcp_pro.tools.layer_tools import register_layer_tools
from gimp_mcp_pro.tools.pdb_tools import register_pdb_tools
from gimp_mcp_pro.tools.selection_tools import register_selection_tools
from gimp_mcp_pro.tools.transform_tools import register_transform_tools
from gimp_mcp_pro.utils.errors import GimpCommandError

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
        self.calls.append(("send_command", {"type": command_type, "params": params, "timeout": timeout}))
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


def registered_tools(bridge: ScriptedBridge) -> dict[str, Tool]:
    mcp = CaptureMCP()
    for register in [
        register_image_tools,
        register_layer_tools,
        register_selection_tools,
        register_drawing_tools,
        register_inspect_tools,
        register_history_tools,
        register_pdb_tools,
        register_transform_tools,
        register_filter_tools,
        register_color_tools,
    ]:
        register(mcp, bridge)
    return mcp.tools


SUCCESS_TOOL_ARGS: dict[str, dict[str, Any]] = {
    "add_text": {"text": "hello 'quoted' world", "layer_name": "text-layer"},
    "adjust_curves": {"control_points": [0.0, 0.0, 1.0, 1.0]},
    "create_image": {"width": 64, "height": 48},
    "crop_image": {"x": 1, "y": 2, "width": 32, "height": 24},
    "delete_layer": {"layer_index": 0},
    "draw_brush_stroke": {"points": [0, 0, 10, 10, 20, 0, 30, 10]},
    "draw_ellipse": {"x": 2, "y": 3, "width": 12, "height": 8},
    "draw_line": {"x1": 0, "y1": 0, "x2": 16, "y2": 16},
    "draw_polygon": {"points": [0, 0, 20, 0, 20, 20]},
    "draw_rectangle": {"x": 1, "y": 1, "width": 12, "height": 8},
    "execute_python": {"code": ["x = 1", "print(x)"]},
    "export_image": {"file_path": "/tmp/gimp-mcp-test.png"},
    "get_image_bitmap": {"max_width": 32, "max_height": 24},
    "offset_layer": {"offset_x": 4, "offset_y": 5},
    "resize_canvas": {"new_width": 128, "new_height": 96},
    "rotate_image": {"angle": 90},
    "rotate_layer": {"angle_degrees": 15.0},
    "sample_color": {"x": 2, "y": 3},
    "scale_image": {"new_width": 128, "new_height": 96},
    "scale_layer": {"new_width": 32, "new_height": 24},
    "search_pdb": {"query": "png"},
    "select_ellipse": {"x": 2, "y": 3, "width": 12, "height": 8},
    "select_grow": {"radius": 2},
    "select_polygon": {"points": [0, 0, 20, 0, 20, 20]},
    "select_rectangle": {"x": 2, "y": 3, "width": 12, "height": 8},
    "select_shrink": {"radius": 1},
    "set_active_layer": {"layer_index": 0},
    "set_background_color": {"color": "#ffffff"},
    "set_foreground_color": {"color": "#000000"},
    "set_layer_opacity": {"opacity": 42},
    "set_layer_visibility": {"visible": False},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(registered_tools(ScriptedBridge()).keys()))
async def test_all_tools_have_fast_success_path(tool_name: str) -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    tool = tools[tool_name]
    kwargs = SUCCESS_TOOL_ARGS.get(tool_name, {})

    result = await tool(**kwargs)

    assert result["success"] is True, f"{tool_name} returned {result!r}"
    assert inspect.iscoroutinefunction(tool)
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
