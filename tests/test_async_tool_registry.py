"""Static/runtime checks for async MCP tool registration."""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pytest

from gimp_mcp_pro.async_bridge import AsyncGimpBridge
from gimp_mcp_pro.bridge import GimpBridge
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
from gimp_mcp_pro.tools.roadmap_tools import register_roadmap_tools
from gimp_mcp_pro.tools.selection_tools import register_selection_tools
from gimp_mcp_pro.tools.target_tools import register_target_tools
from gimp_mcp_pro.tools.transform_tools import register_transform_tools
from gimp_mcp_pro.tools.types import AsyncToolBridge
from gimp_mcp_pro.utils.errors import GimpCommandError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "src" / "gimp_mcp_pro" / "tools"
RegisterFn = Callable[[Any, Any], None]


class CaptureMCP:
    """Tiny FastMCP-compatible capture registrar."""

    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., Any]] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class AsyncNoopBridge:
    """Bridge surface sufficient for registration-time tests."""

    async def async_send_command(
        self,
        command_type: str,
        params: CommandParams | None = None,
        timeout: float | None = None,
    ) -> PluginResponse:
        return {"status": "success", "results": {}}

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        return {"status": "success", "results": []}

    async def async_evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        return {"status": "success", "results": []}

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: BitmapRegion | None = None,
    ) -> PluginResponse:
        return {"status": "success", "results": {"image_data": "", "width": 1, "height": 1}}

    async def async_get_image_metadata(self) -> PluginResponse:
        return {"status": "success", "results": {"width": 10, "height": 10}}

    async def async_get_context_state(self) -> PluginResponse:
        return {"status": "success", "results": {"foreground": "#000000"}}

    async def async_get_gimp_info(self) -> PluginResponse:
        return {"status": "success", "results": {"version": "3.2.4"}}


class OptionalCapabilityBridge(AsyncNoopBridge):
    """Bridge that raises known optional-capability command failures."""

    def __init__(self, message: str) -> None:
        self.message = message

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        raise GimpCommandError(self.message, command="exec")


class RecordingAsyncBridge(AsyncNoopBridge):
    """Async bridge that records tool calls for invocation tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def async_send_command(
        self,
        command_type: str,
        params: CommandParams | None = None,
        timeout: float | None = None,
    ) -> PluginResponse:
        self.calls.append(
            ("send_command", {"type": command_type, "params": params, "timeout": timeout})
        )
        return await super().async_send_command(command_type, params, timeout)

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        self.calls.append(("execute_python", code_lines))
        return await super().async_execute_python(code_lines, timeout)

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
        return await super().async_get_image_bitmap(max_width, max_height, region)

    async def async_get_image_metadata(self) -> PluginResponse:
        self.calls.append(("get_image_metadata", None))
        return await super().async_get_image_metadata()


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


def register_functions() -> list[RegisterFn]:
    return [
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
        register_roadmap_tools,
        lambda mcp, bridge: register_gimp_dev_tools(mcp, bridge, FakeGimpDevAdapter()),
        register_flow_tools,
    ]


def registered_tools(bridge: AsyncToolBridge | None = None) -> dict[str, Callable[..., Any]]:
    mcp = CaptureMCP()
    tool_bridge = bridge or AsyncNoopBridge()
    for register in register_functions():
        register(mcp, tool_bridge)
    return mcp.tools


def tool_nodes() -> Iterable[tuple[Path, ast.AsyncFunctionDef | ast.FunctionDef]]:
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name in {"__init__.py", "types.py"}:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if any(
                isinstance(dec, ast.Call) and getattr(dec.func, "attr", None) == "tool"
                for dec in node.decorator_list
            ):
                yield path, node


def _annotation_name(annotation: ast.expr | None) -> str:
    if annotation is None:
        return ""
    return ast.unparse(annotation)


def _accept_async_tool_bridge(bridge: AsyncToolBridge) -> AsyncToolBridge:
    return bridge


def test_all_mcp_tool_handlers_are_async_defs() -> None:
    non_async = [
        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{node.name}"
        for path, node in tool_nodes()
        if not isinstance(node, ast.AsyncFunctionDef)
    ]

    assert non_async == []


def test_all_mcp_tool_handlers_return_tool_result_alias() -> None:
    wrong_annotations = [
        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{node.name}->{_annotation_name(node.returns)}"
        for path, node in tool_nodes()
        if _annotation_name(node.returns) != "ToolResult"
    ]

    assert wrong_annotations == []


def test_all_registered_tools_are_coroutine_functions() -> None:
    tools = registered_tools()

    assert len(tools) == 171
    assert all(inspect.iscoroutinefunction(tool) for tool in tools.values())


def test_tool_modules_use_only_async_bridge_methods() -> None:
    forbidden = [
        "bridge.send_command(",
        "bridge.execute_python(",
        "bridge.evaluate_python(",
        "bridge.get_image_bitmap(",
        "bridge.get_image_metadata(",
        "bridge.get_context_state(",
        "bridge.get_gimp_info(",
    ]
    offenders: list[str] = []
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name in {"__init__.py", "types.py"}:
            continue
        text = path.read_text()
        offenders.extend(
            f"{path.relative_to(PROJECT_ROOT)} contains {pattern}"
            for pattern in forbidden
            if pattern in text
        )

    assert offenders == []


def test_bridge_implementations_satisfy_async_tool_bridge_protocol() -> None:
    assert _accept_async_tool_bridge(AsyncGimpBridge()).__class__ is AsyncGimpBridge
    assert _accept_async_tool_bridge(GimpBridge()).__class__ is GimpBridge


@pytest.mark.asyncio
async def test_representative_tools_await_async_bridge_methods() -> None:
    bridge = RecordingAsyncBridge()
    tools = registered_tools(bridge)

    select_all_result = await tools["select_all"]()
    image_info_result = await tools["get_image_info"]()
    bitmap_result = await tools["get_image_bitmap"](max_width=42, max_height=13)

    assert select_all_result["success"] is True
    assert image_info_result["success"] is True
    assert bitmap_result["success"] is True
    assert bridge.calls[0][0] == "execute_python"
    assert ("get_image_metadata", None) in bridge.calls
    assert (
        "get_image_bitmap",
        {"max_width": 42, "max_height": 13, "region": None},
    ) in bridge.calls


@pytest.mark.asyncio
async def test_optional_324_history_failures_are_machine_readable() -> None:
    tools = registered_tools(
        OptionalCapabilityBridge(
            "Undo is not available via the GIMP 3.0 plugin API. Use Ctrl+Z in GIMP directly."
        )
    )

    result = await tools["undo"]()

    assert result["success"] is False
    assert result["data"]["error_code"] == "optional_capability_unavailable"
    assert result["data"]["procedure"] == "gimp-image-undo"


@pytest.mark.asyncio
async def test_drop_shadow_uses_safe_gegl_filter_not_crashing_script_fu() -> None:
    bridge = RecordingAsyncBridge()
    tools = registered_tools(bridge)

    result = await tools["apply_drop_shadow"](
        offset_x=2.0, offset_y=3.0, blur_radius=4.0, color="black", opacity=50.0
    )

    assert result["success"] is True
    generated = "\n".join(
        "\n".join(call[1])
        for call in bridge.calls
        if call[0] == "execute_python" and isinstance(call[1], list)
    )
    assert "script-fu-drop-shadow" not in generated
    assert "run(cfg)" not in generated
    assert "Gimp.DrawableFilter.new(drawable, 'gegl:dropshadow', '')" in generated
    assert "cfg.set_property('x', 2.0)" in generated
    assert "cfg.set_property('y', 3.0)" in generated
    assert "cfg.set_property('radius', 4.0)" in generated
    assert "cfg.set_property('color', Gegl.Color.new('black'))" in generated
    assert "cfg.set_property('opacity', 0.5)" in generated


@pytest.mark.asyncio
async def test_search_pdb_uses_query_procedures_without_invalid_wildcard_lookup() -> None:
    bridge = RecordingAsyncBridge()
    tools = registered_tools(bridge)

    result = await tools["search_pdb"]("png", max_results=5)

    assert result["success"] is True
    generated = "\n".join(
        "\n".join(call[1])
        for call in bridge.calls
        if call[0] == "execute_python" and isinstance(call[1], list)
    )
    assert "query_procedures" in generated
    assert "lookup_procedure(name)" not in generated
    assert "-*" not in generated


def test_server_uses_asyncio_native_bridge_for_mcp_tools() -> None:
    source = (PROJECT_ROOT / "src" / "gimp_mcp_pro" / "server.py").read_text()

    assert "from gimp_mcp_pro.async_bridge import AsyncGimpBridge" in source
    assert "bridge = AsyncGimpBridge(**config.bridge_kwargs())" in source


def test_live_compat_matrix_declares_async_transport_check() -> None:
    contract = (PROJECT_ROOT / "compat.yml").read_text()
    runner = (PROJECT_ROOT / "tests" / "live_gimp_324_smoke.py").read_text()

    assert "C-025-async-transport" in contract
    assert "C-025-async-transport" in runner
    assert "AsyncGimpBridge" in runner


@pytest.mark.asyncio
async def test_async_native_bridge_can_drive_registered_tool_surface() -> None:
    class ScriptedAsyncBridge(AsyncNoopBridge):
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        async def async_get_gimp_info(self) -> PluginResponse:
            self.calls.append(("get_gimp_info", None))
            return {"status": "success", "results": {"gimp": {"version": "3.2.4"}}}

        async def async_execute_python(
            self,
            code_lines: list[str],
            timeout: float | None = None,
        ) -> PluginResponse:
            self.calls.append(("execute_python", code_lines))
            return {"status": "success", "results": ["ok"]}

        async def async_get_image_metadata(self) -> PluginResponse:
            self.calls.append(("get_image_metadata", None))
            return {"status": "success", "results": {"basic": {"width": 96, "height": 64}}}

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
                "results": {"image_data": "iVBORw0KGgo=", "width": 64, "height": 64},
            }

    bridge = ScriptedAsyncBridge()
    tools = registered_tools(bridge)

    create_result = await tools["create_image"](96, 64, "rgb", "white")
    info_result = await tools["get_image_info"]()
    bitmap_result = await tools["get_image_bitmap"](64, 64)
    gimp_result = await tools["get_gimp_info"]()

    assert create_result["success"] is True
    assert info_result["success"] is True
    assert bitmap_result["success"] is True
    assert gimp_result["success"] is True
    assert len(tools) == 171
    assert ("get_gimp_info", None) in bridge.calls
    assert (
        "get_image_bitmap",
        {"max_width": 64, "max_height": 64, "region": None},
    ) in bridge.calls
