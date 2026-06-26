"""Shared generated-code backend helpers for native GIMP tool implementations."""

from __future__ import annotations

import json
import logging
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gimp_mcp_pro.bridge import LONG_TIMEOUT
from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.types import AsyncToolBridge, ToolResult
from gimp_mcp_pro.utils.errors import GimpCommandError

logger = logging.getLogger("gimp_mcp_pro.tools.native_backend")

SUPPORTED_EXPORT_FORMATS = {"png", "jpeg", "jpg", "webp", "tiff", "tif", "psd", "xcf"}
SUPPORTED_CHANNEL_ACTIONS = {
    "list",
    "create",
    "rename",
    "duplicate",
    "show",
    "hide",
    "to_selection",
    "selection_to_channel",
}
SUPPORTED_PATH_ACTIONS = {"list", "create", "rename", "delete", "to_selection", "stroke", "fill"}
SUPPORTED_GUIDE_GRID_ACTIONS = {"list", "add", "move", "remove", "set_grid"}


class CodeBuilder:
    """Small deterministic helper for building bridge-executed Python snippets."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, line: str) -> CodeBuilder:
        self.lines.append(line)
        return self

    def extend(self, lines: list[str] | tuple[str, ...]) -> CodeBuilder:
        self.lines.extend(lines)
        return self

    def block(self, header: str, body: list[str] | tuple[str, ...]) -> CodeBuilder:
        self.lines.append("\n".join([header, *("    " + line for line in body)]))
        return self

    def dedent(self, block: str) -> CodeBuilder:
        self.lines.append(textwrap.dedent(block).strip("\n"))
        return self

    def emit_json(self, variable: str = "result") -> CodeBuilder:
        self.lines.append(f"print(json.dumps({variable}, sort_keys=True))")
        return self


@dataclass(frozen=True)
class NativeOperation:
    """Registered generated-code backend operation."""

    name: str
    generator: Callable[[dict[str, Any]], list[str]]
    required_payload_keys: tuple[str, ...] = ()

    def build(self, payload: dict[str, Any]) -> list[str]:
        missing = [key for key in self.required_payload_keys if key not in payload]
        if missing:
            raise ValueError(f"missing native payload key(s) for {self.name}: {', '.join(missing)}")
        return self.generator(payload)


def py_literal(value: object) -> str:
    """Return a safe Python literal for generated GIMP plug-in code."""
    return repr(value)


def _dedent(block: str) -> str:
    """Dedent a generated Python block for bridge execution."""
    return textwrap.dedent(block).strip("\n")


def _json_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Extract a JSON object printed by generated plug-in code."""
    raw = result.get("results")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        for item in reversed(raw):
            if isinstance(item, dict):
                return item
            if isinstance(item, str):
                stripped = item.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
    return {}


def generated_context_helpers(names: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    """Return generated GIMP-side context manager helpers by name."""
    return native_context.generated_context_helpers(names)


# Import after helper definitions: native_* modules import NativeOperation and helpers from this module.
# Split-module references kept explicit for tests:
# from gimp_mcp_pro.tools import native_channels
# from gimp_mcp_pro.tools import native_exports
# from gimp_mcp_pro.tools import native_gegl
# from gimp_mcp_pro.tools import native_misc
# from gimp_mcp_pro.tools import native_paths
# from gimp_mcp_pro.tools import native_pdb
from gimp_mcp_pro.tools import (  # noqa: E402
    native_channels,
    native_context,
    native_exports,
    native_gegl,
    native_misc,
    native_paths,
    native_pdb,
)


def _build_native_operations() -> dict[str, NativeOperation]:
    operations: dict[str, NativeOperation] = {}
    for module in (
        native_channels,
        native_paths,
        native_exports,
        native_pdb,
        native_gegl,
        native_misc,
    ):
        operations.update(module.operations())
    return operations


NATIVE_OPERATIONS: dict[str, NativeOperation] = _build_native_operations()


def native_extra_for(operation: str, payload: dict[str, Any]) -> list[str]:
    """Return native GIMP backend code for a registered promoted operation."""
    op = NATIVE_OPERATIONS.get(operation)
    if op is None:
        raise ValueError(f"unknown native backend operation: {operation}")
    return op.build(payload)


def build_json_code(
    marker: str, payload: dict[str, Any], extra_lines: list[str] | None = None
) -> list[str]:
    """Build a deterministic JSON-emitting code block for GIMP-side execution."""
    operation = str(payload.get("operation", ""))
    builder = CodeBuilder()
    builder.extend(
        [
            "from gi.repository import Gimp, Gegl",
            "import json, os, time, tempfile",
            f"# {marker}",
            f"result = {py_literal(payload)}",
        ]
    )
    builder.extend(native_extra_for(operation, payload))
    builder.extend(extra_lines or [])
    builder.emit_json("result")
    return builder.lines


async def execute_json_tool(
    bridge: AsyncToolBridge,
    *,
    operation: str,
    marker: str,
    payload: dict[str, Any],
    message: str,
    extra_lines: list[str] | None = None,
) -> ToolResult:
    """Run generated GIMP code and return a structured operation result."""
    try:
        response = await bridge.async_execute_python(
            build_json_code(marker, dict(payload, operation=operation), extra_lines),
            timeout=LONG_TIMEOUT,
        )
        data = _json_payload(response)
        if not data:
            data = payload
        return OperationResult.ok(operation=operation, message=message, data=data).model_dump()
    except ValueError as exc:
        return OperationResult.fail(operation=operation, error=str(exc)).model_dump()
    except GimpCommandError as exc:
        return OperationResult.fail(operation=operation, error=str(exc)).model_dump()


def normalise_format(value: object) -> str:
    """Normalize an export format token."""
    return str(value).strip().lower().lstrip(".")


def validate_formats(formats: list[object]) -> list[str]:
    """Return unsupported export formats."""
    return [
        fmt
        for fmt in (normalise_format(item) for item in formats)
        if fmt not in SUPPORTED_EXPORT_FORMATS
    ]


def validate_positive_size(width: object, height: object) -> tuple[int, int]:
    """Coerce and validate a positive two-dimensional size."""
    width_int = int(str(width))
    height_int = int(str(height))
    if width_int < 1 or height_int < 1:
        raise ValueError("width and height must be positive")
    return width_int, height_int
