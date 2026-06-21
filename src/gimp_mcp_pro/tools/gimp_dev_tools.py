"""Read-only MCP tools for optional ``gimp.dev`` integration."""

from __future__ import annotations

import asyncio
from functools import partial

from gimp_mcp_pro.gimp_dev_integration import GimpDevAdapter, GimpDevIntegrationError
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult


def register_gimp_dev_tools(
    mcp: MCPToolRegistrar,
    bridge: AsyncToolBridge | None = None,
    adapter: GimpDevAdapter | None = None,
) -> None:
    """Register read-only ``gimp.dev`` catalog/status tools.

    Args:
        mcp: MCP registrar.
        bridge: Unused async GIMP bridge parameter kept for registration-shape
            consistency with other tool modules.
        adapter: Optional adapter, usually injected by the server or tests.
    """
    del bridge
    gimp_dev = adapter or GimpDevAdapter()

    @mcp.tool()
    async def gimp_dev_status() -> ToolResult:
        """Return local ``gimp.dev`` integration availability.

        Returns:
            Operation result containing root, command, allowlist, and availability
            information. This tool never starts GIMP and never mutates the user's
            GIMP profile.
        """
        data = await asyncio.to_thread(gimp_dev.status)
        return OperationResult.ok(
            operation="gimp_dev_status",
            message="gimp.dev integration status collected",
            data=data,
        ).model_dump()

    @mcp.tool()
    async def gimp_dev_plugin_catalog(
        include_raw_catalog: bool = False,
        validate: bool = True,
    ) -> ToolResult:
        """Return the pure ``gimp.dev`` plug-in procedure catalog.

        Args:
            include_raw_catalog: Include the raw catalog JSON from ``gimp-dev``.
                Defaults to false to keep the MCP response compact.
            validate: Ask ``gimp-dev`` to validate the catalog when supported.

        Returns:
            Operation result with compact procedure summary and optional raw
            catalog payload. This tool does not start GIMP.
        """
        try:
            catalog = await asyncio.to_thread(partial(gimp_dev.load_catalog, validate=validate))
            summary = gimp_dev.summarize_catalog(catalog)
        except GimpDevIntegrationError as exc:
            return OperationResult.fail(
                operation="gimp_dev_plugin_catalog",
                error=str(exc),
                data=gimp_dev.status(),
            ).model_dump()

        data = summary.as_dict(include_procedures=True)
        data["policy"] = "read-only catalog discovery; live calls require a separate adapter"
        if include_raw_catalog:
            data["raw_catalog"] = catalog
        return OperationResult.ok(
            operation="gimp_dev_plugin_catalog",
            message=f"Loaded {summary.procedure_count} gimp.dev procedure(s)",
            data=data,
        ).model_dump()
