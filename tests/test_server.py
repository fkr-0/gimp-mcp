"""Tests for server factory wiring and prompt fallback coverage."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

import gimp_mcp_pro.server as server
from gimp_mcp_pro.config import ServerConfig


class FakeFastMCP:
    """Small FastMCP stand-in for server wiring tests."""

    instances: list[FakeFastMCP] = []

    def __init__(self, name: str) -> None:
        self.name = name
        self.prompts: dict[str, Callable[[], str]] = {}
        self.prompt_descriptions: dict[str, str] = {}
        self.registered_tools: list[str] = []
        FakeFastMCP.instances.append(self)

    def prompt(self, description: str) -> Callable[[Callable[[], str]], Callable[[], str]]:
        def decorator(fn: Callable[[], str]) -> Callable[[], str]:
            self.prompts[fn.__name__] = fn
            self.prompt_descriptions[fn.__name__] = description
            return fn

        return decorator


class FakeAsyncGimpBridge:
    """Capture bridge construction kwargs without opening sockets."""

    last_kwargs: dict[str, Any] = {}

    def __init__(self, **kwargs: Any) -> None:
        FakeAsyncGimpBridge.last_kwargs = kwargs


def patch_tool_registrars(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Patch all tool registrars with capture callables."""
    calls: list[str] = []
    modules = {
        "agent_tools": "register_agent_tools",
        "color_tools": "register_color_tools",
        "drawing_tools": "register_drawing_tools",
        "filter_tools": "register_filter_tools",
        "flow_tools": "register_flow_tools",
        "gimp_dev_tools": "register_gimp_dev_tools",
        "history_tools": "register_history_tools",
        "image_tools": "register_image_tools",
        "inspect_tools": "register_inspect_tools",
        "layer_tools": "register_layer_tools",
        "path_tools": "register_path_tools",
        "pdb_tools": "register_pdb_tools",
        "selection_tools": "register_selection_tools",
        "target_tools": "register_target_tools",
        "transform_tools": "register_transform_tools",
    }
    for module_name, function_name in modules.items():
        module = __import__(f"gimp_mcp_pro.tools.{module_name}", fromlist=[function_name])

        def register(
            mcp: FakeFastMCP,
            bridge: FakeAsyncGimpBridge,
            *args: object,
            name: str = function_name,
        ) -> None:
            del args
            calls.append(name)
            mcp.registered_tools.append(name)
            assert isinstance(bridge, FakeAsyncGimpBridge)

        monkeypatch.setattr(module, function_name, register)
    return calls


def test_create_server_wires_bridge_and_tool_registrars(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeFastMCP.instances.clear()
    monkeypatch.setattr(server, "FastMCP", FakeFastMCP)
    monkeypatch.setattr(server, "AsyncGimpBridge", FakeAsyncGimpBridge)
    monkeypatch.setattr(server, "setup_logging", lambda **_kwargs: None)
    calls = patch_tool_registrars(monkeypatch)

    config = ServerConfig(gimp_host="example.local", gimp_port=9911, reconnect_delays=(0.25,))
    mcp = server.create_server(config)

    assert isinstance(mcp, FakeFastMCP)
    assert mcp.name == "GIMP MCP Pro"
    assert FakeAsyncGimpBridge.last_kwargs["host"] == "example.local"
    assert FakeAsyncGimpBridge.last_kwargs["port"] == 9911
    assert FakeAsyncGimpBridge.last_kwargs["reconnect_delays"] == [0.25]
    assert calls == [
        "register_agent_tools",
        "register_image_tools",
        "register_layer_tools",
        "register_selection_tools",
        "register_path_tools",
        "register_drawing_tools",
        "register_inspect_tools",
        "register_history_tools",
        "register_pdb_tools",
        "register_target_tools",
        "register_transform_tools",
        "register_filter_tools",
        "register_color_tools",
        "register_gimp_dev_tools",
        "register_flow_tools",
    ]


def test_create_server_registers_prompt_fallbacks(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    FakeFastMCP.instances.clear()
    monkeypatch.setattr(server, "FastMCP", FakeFastMCP)
    monkeypatch.setattr(server, "AsyncGimpBridge", FakeAsyncGimpBridge)
    monkeypatch.setattr(server, "setup_logging", lambda **_kwargs: None)
    patch_tool_registrars(monkeypatch)
    monkeypatch.setattr(server.Path, "exists", lambda _self: False)

    mcp = server.create_server(ServerConfig())

    assert set(mcp.prompts) == {
        "gimp_best_practices",
        "gimp_iterative_workflow",
        "gimp_filter_catalog",
        "gimp_api_reference",
    }
    assert "polygon selection" in mcp.prompts["gimp_best_practices"]()
    assert "Golden Rule" in mcp.prompts["gimp_iterative_workflow"]()
    assert "Filter Catalog" in mcp.prompts["gimp_filter_catalog"]()
    assert "developer.gimp.org" in mcp.prompts["gimp_api_reference"]()
