"""History tools for GIMP MCP Pro — undo, redo, undo groups."""

from __future__ import annotations

import logging

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.history")


def register_history_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register history/undo tools with the MCP server."""

    @mcp.tool()
    async def undo(steps: int = 1) -> ToolResult:
        """Undo the last operation(s).

        Args:
            steps: Number of undo steps (default 1)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "pdb = Gimp.get_pdb()",
            "proc = pdb.lookup_procedure('gimp-image-undo')",
            "if not proc: raise RuntimeError('Undo is not available via the GIMP 3.0 plugin API. Use Ctrl+Z in GIMP directly.')",
            "cfg = proc.create_config()",
            "cfg.set_property('image', image)",
            "proc.run(cfg)",
            "Gimp.displays_flush()",
        ]

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="undo",
                message=f"Undid {steps} step(s)",
                data={"steps": steps},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="undo", error=str(e)).model_dump()

    @mcp.tool()
    async def redo(steps: int = 1) -> ToolResult:
        """Redo previously undone operation(s).

        Args:
            steps: Number of redo steps (default 1)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "from gi.repository import Gimp",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "pdb = Gimp.get_pdb()",
            "proc = pdb.lookup_procedure('gimp-image-redo')",
            "if not proc: raise RuntimeError('Redo is not available via the GIMP 3.0 plugin API. Use Ctrl+Y in GIMP directly.')",
            "cfg = proc.create_config()",
            "cfg.set_property('image', image)",
            "proc.run(cfg)",
            "Gimp.displays_flush()",
        ]

        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="redo",
                message=f"Redid {steps} step(s)",
                data={"steps": steps},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="redo", error=str(e)).model_dump()

    @mcp.tool()
    async def begin_undo_group(name: str = "AI Operation") -> ToolResult:
        """Start an undo group — all subsequent operations will be grouped
        as a single undo step.

        Notes:
            Use this tool before multi-step workflows. This lets the user
            undo the entire AI operation with a single Ctrl+Z.

        Warnings:
            Important: Always call end_undo_group when done.

        Args:
            name: Name for the undo group (shown in GIMP's undo history)

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "image.undo_group_start()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="begin_undo_group",
                message=f"Undo group '{name}' started",
                data={"name": name},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="begin_undo_group", error=str(e)).model_dump()

    @mcp.tool()
    async def end_undo_group() -> ToolResult:
        """End the current undo group.

        Must be called after begin_undo_group. All operations between
        begin and end will be treated as one undo step.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "image.undo_group_end()",
        ]
        try:
            await bridge.async_execute_python(code)
            return OperationResult.ok(
                operation="end_undo_group",
                message="Undo group ended",
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="end_undo_group", error=str(e)).model_dump()
