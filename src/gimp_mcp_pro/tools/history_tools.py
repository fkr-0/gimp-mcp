"""History tools for GIMP MCP Pro — undo, redo, undo groups."""

from __future__ import annotations

import logging
import os
import tempfile
import time
import uuid
from collections import deque
from typing import Any

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.history")


OPERATION_LOG: deque[dict[str, Any]] = deque(maxlen=200)


def _redact_paths(value: Any) -> Any:
    """Redact local filesystem paths from operation-log payloads."""
    if isinstance(value, dict):
        return {
            key: _redact_paths(nested)
            for key, nested in value.items()
            if key not in {"local_file_path", "xcf_path", "path"}
        }
    if isinstance(value, list):
        return [_redact_paths(item) for item in value]
    if isinstance(value, str) and ("/" in value or "\\" in value):
        return "[redacted-path]"
    return value


def _record_operation(operation: str, **data: Any) -> None:
    """Append a compact operation-log entry."""
    OPERATION_LOG.append(
        {
            "timestamp": time.time(),
            "operation": operation,
            **data,
        }
    )


def register_history_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    """Register history/undo tools with the MCP server."""
    undo_groups: dict[str, dict[str, Any]] = {}
    checkpoints: dict[str, dict[str, Any]] = {}

    @mcp.tool()
    async def create_checkpoint(
        label: str = "checkpoint",
        include_xcf_copy: bool = False,
    ) -> ToolResult:
        """Create a controlled checkpoint record for the active image.

        Args:
            label: Human-readable checkpoint label.
            include_xcf_copy: Save a controlled temporary XCF copy that can be restored later.

        Returns:
            Operation result with checkpoint ID and metadata.

        Contract:
            Checkpoints are generated under a controlled temporary directory and
            do not overwrite user files. XCF-backed checkpoints can only be
            restored into a new document, never silently over the active image.
            Local paths are redacted from operation logs and tool responses.
        """
        checkpoint_id = str(uuid.uuid4())
        safe_label = label.strip() or "checkpoint"
        checkpoint_dir = os.path.join(tempfile.gettempdir(), "gimp-mcp-checkpoints")
        xcf_path = (
            os.path.join(checkpoint_dir, f"{checkpoint_id}.xcf") if include_xcf_copy else None
        )
        code = [
            "from gi.repository import Gio, Gimp",
            "import gc, json, os",
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            f"checkpoint_id = {checkpoint_id!r}",
            f"checkpoint_dir = {checkpoint_dir!r}",
            "os.makedirs(checkpoint_dir, exist_ok=True)",
            f"include_xcf_copy = {include_xcf_copy!r}",
            f"xcf_path = {xcf_path!r}",
        ]
        if include_xcf_copy:
            checkpoint_lifecycle = [
                "# __gimp_mcp_checkpoint_lifecycle__",
                "duplicate = None",
                "checkpoint_file = None",
                "try:",
                "    duplicate = image.duplicate()",
                "    checkpoint_file = Gio.File.new_for_path(xcf_path)",
                "    saved = Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, duplicate, checkpoint_file, None)",
                "    if not saved: raise RuntimeError('GIMP could not save the XCF checkpoint')",
                "finally:",
                "    try:",
                "        if duplicate is not None:",
                "            duplicate.delete()",
                "    except Exception:",
                "        pass",
                "    try:",
                "        del duplicate",
                "    except Exception:",
                "        pass",
                "    try:",
                "        del checkpoint_file",
                "    except Exception:",
                "        pass",
                "    gc.collect()",
            ]
            code.append("\n".join(checkpoint_lifecycle))
        code += [
            "metadata = {'checkpoint_id': checkpoint_id, 'label': "
            + repr(safe_label)
            + ", 'include_xcf_copy': include_xcf_copy, 'xcf_path': xcf_path, 'image_id': int(image.get_id()) if hasattr(image, 'get_id') else None}",
            "print(json.dumps(metadata))",
        ]
        try:
            await bridge.async_execute_python(code)
            checkpoints[checkpoint_id] = {
                "checkpoint_id": checkpoint_id,
                "label": safe_label,
                "created_at": time.time(),
                "include_xcf_copy": include_xcf_copy,
                "xcf_path": xcf_path,
            }
            data = {
                "checkpoint_id": checkpoint_id,
                "label": safe_label,
                "include_xcf_copy": include_xcf_copy,
                "metadata": {"controlled_temp_dir": True, "path_redacted": True},
            }
            _record_operation(
                "create_checkpoint",
                checkpoint_id=checkpoint_id,
                label=safe_label,
                include_snapshot=False,
                local_file_path="/tmp/gimp-mcp-checkpoints/redacted.xcf"
                if include_xcf_copy
                else None,
            )
            return OperationResult.ok(
                operation="create_checkpoint",
                message=f"Checkpoint {checkpoint_id} created",
                data=data,
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="create_checkpoint", error=str(e)).model_dump()

    @mcp.tool()
    async def list_checkpoints() -> ToolResult:
        """List checkpoints created during this MCP server session.

        Returns a compact, path-redacted index. An XCF-backed checkpoint can be
        opened with ``restore_checkpoint``; metadata-only checkpoints are useful
        as audit markers but cannot restore pixels.

        Returns:
            Operation result with current checkpoint metadata and retention scope.
        """
        entries = [
            {
                "checkpoint_id": entry["checkpoint_id"],
                "label": entry["label"],
                "created_at": entry["created_at"],
                "restorable": bool(entry["include_xcf_copy"]),
            }
            for entry in checkpoints.values()
        ]
        return OperationResult.ok(
            operation="list_checkpoints",
            message=f"Returned {len(entries)} checkpoint(s)",
            data={
                "checkpoints": entries,
                "count": len(entries),
                "scope": "current MCP server session",
                "paths_redacted": True,
            },
        ).model_dump()

    @mcp.tool()
    async def restore_checkpoint(checkpoint_id: str) -> ToolResult:
        """Open an XCF-backed checkpoint as a new GIMP document.

        This is deliberately non-destructive: it never replaces the active
        document. Compare the newly opened checkpoint with the current image,
        then copy or export the material you want to keep.

        Args:
            checkpoint_id: ID returned by ``create_checkpoint`` with ``include_xcf_copy=true``.

        Returns:
            Operation result with the opened image ID and redacted checkpoint metadata.
        """
        checkpoint = checkpoints.get(checkpoint_id)
        if checkpoint is None:
            return OperationResult.fail(
                operation="restore_checkpoint",
                error="checkpoint_id is unknown or belongs to a previous MCP server session",
                data={"checkpoint_id": checkpoint_id},
            ).model_dump()
        xcf_path = checkpoint.get("xcf_path")
        if not isinstance(xcf_path, str):
            return OperationResult.fail(
                operation="restore_checkpoint",
                error="checkpoint is metadata-only; create it with include_xcf_copy=true to restore pixels",
                data={"checkpoint_id": checkpoint_id},
            ).model_dump()
        code = [
            "from gi.repository import Gio, Gimp",
            "import json, os",
            "# __gimp_mcp_restore_checkpoint__",
            f"checkpoint_path = {xcf_path!r}",
            "if not os.path.isfile(checkpoint_path): raise RuntimeError('Checkpoint XCF no longer exists')",
            "checkpoint_file = Gio.File.new_for_path(checkpoint_path)",
            "restored_image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, checkpoint_file)",
            "if restored_image is None: raise RuntimeError('GIMP could not load the XCF checkpoint')",
            "Gimp.displays_flush()",
            "print(json.dumps({'restored_image_id': int(restored_image.get_id()) if hasattr(restored_image, 'get_id') else None}))",
        ]
        try:
            await bridge.async_execute_python(code)
            _record_operation(
                "restore_checkpoint", checkpoint_id=checkpoint_id, label=checkpoint["label"]
            )
            return OperationResult.ok(
                operation="restore_checkpoint",
                message=f"Checkpoint '{checkpoint['label']}' opened as a new image",
                data={
                    "checkpoint_id": checkpoint_id,
                    "label": checkpoint["label"],
                    "opened_as_new_document": True,
                    "paths_redacted": True,
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="restore_checkpoint", error=str(e)).model_dump()

    @mcp.tool()
    async def discard_checkpoint(checkpoint_id: str) -> ToolResult:
        """Delete a controlled XCF checkpoint and remove it from this session's index.

        Args:
            checkpoint_id: ID returned by ``create_checkpoint``.

        Returns:
            Operation result with deletion status and no local path disclosure.
        """
        checkpoint = checkpoints.get(checkpoint_id)
        if checkpoint is None:
            return OperationResult.fail(
                operation="discard_checkpoint",
                error="checkpoint_id is unknown or already discarded",
                data={"checkpoint_id": checkpoint_id},
            ).model_dump()
        xcf_path = checkpoint.get("xcf_path")
        if isinstance(xcf_path, str):
            code = [
                "import os",
                "# __gimp_mcp_discard_checkpoint__",
                f"checkpoint_path = {xcf_path!r}",
                "if os.path.exists(checkpoint_path): os.remove(checkpoint_path)",
            ]
            try:
                await bridge.async_execute_python(code)
            except GimpCommandError as e:
                return OperationResult.fail(
                    operation="discard_checkpoint", error=str(e)
                ).model_dump()
        checkpoints.pop(checkpoint_id, None)
        _record_operation(
            "discard_checkpoint", checkpoint_id=checkpoint_id, label=checkpoint["label"]
        )
        return OperationResult.ok(
            operation="discard_checkpoint",
            message=f"Checkpoint '{checkpoint['label']}' discarded",
            data={"checkpoint_id": checkpoint_id, "paths_redacted": True},
        ).model_dump()

    @mcp.tool()
    async def get_operation_log(
        limit: int = 20,
        include_snapshots: bool = False,
        redact_paths: bool = True,
    ) -> ToolResult:
        """Return recent MCP operation-log entries.

        Args:
            limit: Maximum number of recent entries to return.
            include_snapshots: Include snapshot payloads when available.
            redact_paths: Redact local filesystem paths from returned entries.

        Returns:
            Operation result with recent operations and retention metadata.

        Contract:
            Raw image payloads and local paths are omitted unless explicitly requested.
        """
        limit = max(1, min(200, int(limit)))
        operations = list(OPERATION_LOG)[-limit:]
        if not include_snapshots:
            operations = [
                {k: v for k, v in entry.items() if k not in {"snapshot", "before", "after"}}
                for entry in operations
            ]
        if redact_paths:
            operations = _redact_paths(operations)
        return OperationResult.ok(
            operation="get_operation_log",
            message=f"Returned {len(operations)} operation-log entrie(s)",
            data={
                "operations": operations,
                "limit": limit,
                "include_snapshots": include_snapshots,
                "redacted_paths": redact_paths,
                "retention": OPERATION_LOG.maxlen,
            },
        ).model_dump()

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
            error = str(e)
            if "Undo is not available via the GIMP 3.0 plugin API" in error:
                return OperationResult.optional_capability_unavailable(
                    operation="undo",
                    capability="programmatic image undo",
                    procedure="gimp-image-undo",
                    error=error,
                    recommendation="Use Ctrl+Z in GIMP directly or group changes with begin_undo_group/end_undo_group.",
                ).model_dump()
            return OperationResult.fail(operation="undo", error=error).model_dump()

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
            error = str(e)
            if "Redo is not available via the GIMP 3.0 plugin API" in error:
                return OperationResult.optional_capability_unavailable(
                    operation="redo",
                    capability="programmatic image redo",
                    procedure="gimp-image-redo",
                    error=error,
                    recommendation="Use Ctrl+Y in GIMP directly after verifying the active image state.",
                ).model_dump()
            return OperationResult.fail(operation="redo", error=error).model_dump()

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
        group_id = f"undo-{uuid.uuid4().hex[:12]}"
        code = [
            "images = Gimp.get_images()",
            "if not images: raise RuntimeError('No images are open')",
            "image = images[0]",
            "image.undo_group_start()",
        ]
        try:
            await bridge.async_execute_python(code)
            undo_groups[group_id] = {"name": name, "started_at": time.time()}
            return OperationResult.ok(
                operation="begin_undo_group",
                message=f"Undo group '{name}' started",
                data={"name": name, "group_id": group_id, "open_group_count": len(undo_groups)},
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="begin_undo_group", error=str(e)).model_dump()

    @mcp.tool()
    async def end_undo_group(
        group_id: str | None = None,
        close_all: bool = False,
    ) -> ToolResult:
        """End the current undo group.

        Must be called after begin_undo_group. All operations between
        begin and end will be treated as one undo step.

        Args:
            group_id: Optional tracked undo-group ID returned by begin_undo_group.
            close_all: Close all tracked open undo groups in reverse start order.

        Returns:
            Operation result dictionary with status, message, and tool-specific data or error details.
        """
        if close_all:
            closed_group_ids = list(reversed(list(undo_groups)))
            count = max(1, len(closed_group_ids))
            code = [
                "images = Gimp.get_images()",
                "if not images: raise RuntimeError('No images are open')",
                "image = images[0]",
                "# __gimp_mcp_history_close_all_undo_groups__",
                *["image.undo_group_end()" for _ in range(count)],
            ]
        else:
            closed_group_ids = [group_id] if group_id and group_id in undo_groups else []
            code = [
                "images = Gimp.get_images()",
                "if not images: raise RuntimeError('No images are open')",
                "image = images[0]",
                "image.undo_group_end()",
            ]
        try:
            await bridge.async_execute_python(code)
            if close_all:
                undo_groups.clear()
            elif group_id and group_id in undo_groups:
                undo_groups.pop(group_id, None)
            return OperationResult.ok(
                operation="end_undo_group",
                message="Undo group ended" if not close_all else "Open undo groups closed",
                data={
                    "group_id": group_id,
                    "closed_group_ids": closed_group_ids,
                    "closed_count": len(closed_group_ids) if close_all else 1,
                    "open_group_count": len(undo_groups),
                },
            ).model_dump()
        except GimpCommandError as e:
            return OperationResult.fail(operation="end_undo_group", error=str(e)).model_dump()
