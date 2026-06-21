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
from gimp_mcp_pro.tools.types import AsyncToolBridge

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


def register_functions() -> list[RegisterFn]:
    return [
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

    assert len(tools) == 75
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


def test_server_uses_asyncio_native_bridge_for_mcp_tools() -> None:
    source = (PROJECT_ROOT / "src" / "gimp_mcp_pro" / "server.py").read_text()

    assert "from gimp_mcp_pro.async_bridge import AsyncGimpBridge" in source
    assert "bridge = AsyncGimpBridge(**config.bridge_kwargs())" in source
