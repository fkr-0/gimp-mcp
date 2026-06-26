"""Inspection tools for GIMP MCP Pro.

This module intentionally stays as a thin registrar. Focused implementation lives in:
- inspect_context_backend.py
- inspect_geometry_backend.py
- inspect_snapshot_backend.py
- inspect_bitmap_backend.py
"""

from __future__ import annotations

import logging

from gimp_mcp_pro.tools.inspect_bitmap_backend import register_bitmap_inspect_tools
from gimp_mcp_pro.tools.inspect_context_backend import register_context_inspect_tools
from gimp_mcp_pro.tools.inspect_geometry_backend import register_geometry_inspect_tools
from gimp_mcp_pro.tools.inspect_snapshot_backend import register_snapshot_inspect_tools
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar

logger = logging.getLogger("gimp_mcp_pro.tools.inspect")


def register_inspect_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all inspection tools from focused backend modules."""
    register_context_inspect_tools(mcp, bridge)
    register_geometry_inspect_tools(mcp, bridge)
    register_snapshot_inspect_tools(mcp, bridge)
    register_bitmap_inspect_tools(mcp, bridge)
