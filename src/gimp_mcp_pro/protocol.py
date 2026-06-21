"""Shared JSON protocol types for GIMP MCP Pro.

These aliases describe the boundary between MCP tool handlers, bridge
implementations, and the GIMP plug-in transport. They intentionally stay light:
GIMP procedure payloads differ by command, but the outer envelopes are stable.
"""

from __future__ import annotations

from typing import Any, Literal, TypeAlias, TypedDict

CommandParams: TypeAlias = dict[str, Any]
"""JSON-serializable command parameters sent to the GIMP plug-in."""

ToolResult: TypeAlias = dict[str, Any]
"""JSON-serializable result shape returned by public MCP tool handlers."""


class PluginResponse(TypedDict, total=False):
    """Response envelope returned by the GIMP plug-in transport.

    Attributes:
        id: Optional command identifier echoed by the plug-in.
        status: Transport-level command status.
        results: Command-specific success payload.
        error: Human-readable error message on failure.
        traceback: Optional plug-in traceback text on failure.
    """

    id: int
    status: Literal["success", "error"]
    results: Any
    error: str
    traceback: str


class BitmapRegion(TypedDict):
    """Rectangle passed to the image bitmap command.

    Attributes:
        origin_x: Left coordinate of the region.
        origin_y: Top coordinate of the region.
        width: Region width in pixels.
        height: Region height in pixels.
    """

    origin_x: int
    origin_y: int
    width: int
    height: int
