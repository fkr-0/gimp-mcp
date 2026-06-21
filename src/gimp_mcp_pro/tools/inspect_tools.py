"""Inspection tools for GIMP MCP Pro — image viewing, metadata, context state."""

from __future__ import annotations

import logging
from typing import Any

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, CommandParams, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.inspect")


def register_inspect_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register all inspection tools with the MCP server."""

    @mcp.tool()
    async def get_image_bitmap(
        max_width: int | None = 1024,
        max_height: int | None = 1024,
        region_x: int | None = None,
        region_y: int | None = None,
        region_width: int | None = None,
        region_height: int | None = None,
    ) -> ToolResult:
        """Get the current image as a viewable bitmap (PNG).

        Notes:
            Primary use: Verification tool for checking work mid-workflow.

            Best practice guidance:
            - Check after every three to five drawing operations.
            - Use region extraction to verify specific areas at higher quality.
            - Check before the final step so mistakes are caught early.

        Args:
            max_width: Maximum width for scaling (default 1024). Use None for full size.
            max_height: Maximum height for scaling (default 1024). Use None for full size.
            region_x: Optional — extract only this region (left X)
            region_y: Optional — extract only this region (top Y)
            region_width: Optional — region width
            region_height: Optional — region height

        Returns:
            MCP Image object containing PNG data that the AI can view directly.
        """
        params: CommandParams = {}
        if max_width is not None:
            params["max_width"] = max_width
        if max_height is not None:
            params["max_height"] = max_height

        # Build region dict if any region params specified
        if any(v is not None for v in [region_x, region_y, region_width, region_height]):
            if not all(v is not None for v in [region_x, region_y, region_width, region_height]):
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error="All region parameters (region_x, region_y, region_width, region_height) "
                    "must be specified together",
                ).model_dump()
            params["region"] = {
                "origin_x": region_x,
                "origin_y": region_y,
                "width": region_width,
                "height": region_height,
            }

        try:
            result = await bridge.async_get_image_bitmap(
                max_width=params.get("max_width"),
                max_height=params.get("max_height"),
                region=params.get("region"),
            )

            if result.get("status") == "success":
                image_info: dict[str, Any] = result.get("results", {})
                # Return the base64 data and metadata
                return OperationResult.ok(
                    operation="get_image_bitmap",
                    message=(
                        f"Image captured: {image_info.get('width', '?')}x"
                        f"{image_info.get('height', '?')} pixels"
                    ),
                    data={
                        "image_data": image_info.get("image_data", ""),
                        "format": "png",
                        "width": image_info.get("width"),
                        "height": image_info.get("height"),
                        "original_width": image_info.get("original_width"),
                        "original_height": image_info.get("original_height"),
                        "encoding": "base64",
                    },
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_image_bitmap",
                    error=result.get("error", "Failed to get image bitmap"),
                ).model_dump()

        except GimpCommandError as e:
            return OperationResult.fail(operation="get_image_bitmap", error=str(e)).model_dump()

    @mcp.tool()
    async def get_image_metadata() -> ToolResult:
        """Get detailed metadata about the active image without bitmap data.

        Notes:
            Use this tool before any operation — understand canvas dimensions,
            layer structure, and file state. Much faster than get_image_bitmap.

        Notes:
            Returned data includes dimensions, color mode, layers, channels,
            paths, and file information.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        try:
            result = await bridge.async_get_image_metadata()
            if result.get("status") == "success":
                return OperationResult.ok(
                    operation="get_image_metadata",
                    message="Image metadata retrieved",
                    data=result.get("results", {}),
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_image_metadata",
                    error=result.get("error", "Failed to get metadata"),
                ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_image_metadata", error=str(e)).model_dump()

    @mcp.tool()
    async def get_context_state() -> ToolResult:
        """Get current GIMP context state (colors, brush, opacity, settings).

        Warnings:
            Important: Context can be changed by the user in GIMP's UI at any time.
            Check before operations that depend on specific settings.

        Notes:
            Returned data includes foreground and background colors, brush info,
            opacity, paint mode, feather state, and antialiasing state.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        try:
            result = await bridge.async_get_context_state()
            if result.get("status") == "success":
                return OperationResult.ok(
                    operation="get_context_state",
                    message="Context state retrieved",
                    data=result.get("results", {}),
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_context_state",
                    error=result.get("error", "Failed to get context"),
                ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_context_state", error=str(e)).model_dump()

    @mcp.tool()
    async def get_gimp_info() -> ToolResult:
        """Get GIMP environment info (version, paths, capabilities).

        Notes:
            Use this tool for troubleshooting, environment discovery, or
            understanding what features are available.

        Notes:
            Returned data includes the GIMP version, directories, open images,
            PDB availability, current context, system capabilities, and platform info.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        try:
            result = await bridge.async_get_gimp_info()
            if result.get("status") == "success":
                return OperationResult.ok(
                    operation="get_gimp_info",
                    message="GIMP info retrieved",
                    data=result.get("results", {}),
                ).model_dump()
            else:
                return OperationResult.fail(
                    operation="get_gimp_info",
                    error=result.get("error", "Failed to get GIMP info"),
                ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="get_gimp_info", error=str(e)).model_dump()
