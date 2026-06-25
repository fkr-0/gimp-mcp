"""Reusable registry for the existing decorated async tool callables."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class OperationRegistry:
    """Capture MCP-style decorated functions for direct local execution."""

    def __init__(self) -> None:
        self._operations: dict[str, Callable[..., Any]] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._operations[func.__name__] = func
            return func

        return decorator

    def get(self, name: str) -> Callable[..., Any]:
        try:
            return self._operations[name]
        except KeyError as exc:
            raise KeyError(f"unknown flow operation: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._operations)


def build_operation_registry(bridge: Any, gimp_dev_adapter: Any | None = None) -> OperationRegistry:
    """Register the production MCP operations into a local callable registry."""
    from gimp_mcp_pro.tools.agent_tools import register_agent_tools
    from gimp_mcp_pro.tools.color_tools import register_color_tools
    from gimp_mcp_pro.tools.drawing_tools import register_drawing_tools
    from gimp_mcp_pro.tools.filter_tools import register_filter_tools
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

    registry = OperationRegistry()
    for register in (
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
    ):
        register(registry, bridge)
    if gimp_dev_adapter is not None:
        from gimp_mcp_pro.tools.gimp_dev_tools import register_gimp_dev_tools

        register_gimp_dev_tools(registry, bridge, gimp_dev_adapter)
    return registry
