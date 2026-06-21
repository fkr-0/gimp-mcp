"""Shared typing protocols for asynchronous MCP tool registration.

Tool modules depend on these protocols instead of concrete bridge or MCP server
implementations. This keeps the registration layer compatible with the
thread-backed ``GimpBridge`` async adapters and the asyncio-native
``AsyncGimpBridge`` transport.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

ToolResult = dict[str, Any]
"""JSON-serializable result shape returned by public MCP tool handlers."""

AsyncToolCallable = Callable[..., Awaitable[ToolResult]]
"""Callable shape expected for public async MCP tool handlers."""

ToolCallableT = TypeVar("ToolCallableT", bound=AsyncToolCallable)
ToolDecorator = Callable[[ToolCallableT], ToolCallableT]
"""Decorator shape returned by the FastMCP ``tool`` registration method."""


class MCPToolRegistrar(Protocol):
    """Minimal FastMCP registration surface used by tool modules."""

    def tool(self, *args: Any, **kwargs: Any) -> ToolDecorator:
        """Return a decorator that registers one coroutine as an MCP tool.

        Args:
            *args: Positional options accepted by the underlying MCP server.
            **kwargs: Keyword options accepted by the underlying MCP server.

        Returns:
            Decorator that preserves the concrete coroutine function type.
        """
        ...


class AsyncToolBridge(Protocol):
    """Async bridge surface required by MCP tool handlers."""

    async def async_send_command(
        self,
        command_type: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ToolResult:
        """Send a typed plug-in command.

        Args:
            command_type: Native command name understood by the GIMP plug-in.
            params: Optional command parameters to serialize into the request.
            timeout: Optional command-specific timeout in seconds.

        Returns:
            Decoded plug-in response dictionary.
        """
        ...

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> ToolResult:
        """Execute Python code in GIMP's plug-in context.

        Args:
            code_lines: Python statements to execute in order.
            timeout: Optional command-specific timeout in seconds.

        Returns:
            Decoded plug-in response dictionary.
        """
        ...

    async def async_evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> ToolResult:
        """Evaluate Python expressions in GIMP's plug-in context.

        Args:
            expressions: Python expressions to evaluate in order.
            timeout: Optional command-specific timeout in seconds.

        Returns:
            Decoded plug-in response dictionary with expression values.
        """
        ...

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: dict[str, int] | None = None,
    ) -> ToolResult:
        """Get the active image as base64-encoded PNG metadata.

        Args:
            max_width: Optional maximum output width.
            max_height: Optional maximum output height.
            region: Optional region rectangle with origin and size fields.

        Returns:
            Decoded plug-in response dictionary containing PNG metadata.
        """
        ...

    async def async_get_image_metadata(self) -> ToolResult:
        """Get active image metadata.

        Returns:
            Decoded plug-in response dictionary containing image metadata.
        """
        ...

    async def async_get_context_state(self) -> ToolResult:
        """Get GIMP context state.

        Returns:
            Decoded plug-in response dictionary containing context state.
        """
        ...

    async def async_get_gimp_info(self) -> ToolResult:
        """Get GIMP environment info.

        Returns:
            Decoded plug-in response dictionary containing version and capability data.
        """
        ...
