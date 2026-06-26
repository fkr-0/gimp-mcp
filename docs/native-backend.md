# Native Backend Helpers

`src/gimp_mcp_pro/tools/native_backend.py` is the shared generated-code backend for tool-category modules that need to execute small, native GIMP Python snippets through the plug-in bridge.

It is **not an MCP tool category**. It does not register tools, expose user-facing commands, or appear in the tool reference. Category modules such as `image_tools.py`, `layer_tools.py`, `path_tools.py`, `filter_tools.py`, `color_tools.py`, and `pdb_tools.py` import it when a public MCP tool needs common generated-code plumbing.

## Purpose

The native backend module exists to keep promoted native helper behavior in one neutral place after the temporary roadmap wrapper module was removed.

It centralizes three related responsibilities:

- building deterministic Python code blocks that run inside GIMP and print one JSON payload;
- executing those generated blocks through the async bridge and converting plug-in responses into `OperationResult` dictionaries;
- providing native operation snippets for promoted tools whose public handlers live in category modules.

This avoids duplicating JSON parsing, bridge error handling, format validation, and native snippets across every category module.

## When to use it

Use `native_backend.py` when a category tool is already a real MCP tool but needs shared backend support for generated GIMP code.

Good fits include:

- a category tool that prepares a payload and wants a standard `OperationResult` response;
- promoted tools that need one of the shared native snippets in `native_extra_for`;
- tools that need the shared action or format constants such as `SUPPORTED_CHANNEL_ACTIONS`, `SUPPORTED_PATH_ACTIONS`, `SUPPORTED_GUIDE_GRID_ACTIONS`, or `SUPPORTED_EXPORT_FORMATS`;
- tools that need the shared `validate_formats` helper before generating export code.

Do not use it for tool registration. Tool registration belongs in category modules through their `register_*_tools` functions. Do not add user-facing MCP handlers to `native_backend.py`.

## How a category tool uses it

A category module usually imports the helper it needs and keeps the public contract local to the category file:

```python
from gimp_mcp_pro.tools.native_backend import execute_json_tool
```

The category tool then validates user input, constructs a plain payload, and delegates only the generated-code execution to `execute_json_tool`.

`execute_json_tool` calls `build_json_code`, injects matching operation snippets from `native_extra_for`, runs the generated code through `bridge.async_execute_python`, and returns a normalized `OperationResult` model dump.

That keeps the boundary clear:

- category modules own public tool names, parameters, validation, and user-facing messages;
- `native_backend.py` owns common generated-code wrapping, JSON extraction, and shared native snippets;
- the bridge owns transport to the running GIMP plug-in process.

## Example

This simplified pattern mirrors the promoted native tools:

```python
from typing import Any

from gimp_mcp_pro.models.common import OperationResult
from gimp_mcp_pro.tools.native_backend import SUPPORTED_CHANNEL_ACTIONS, execute_json_tool
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult


def register_layer_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    @mcp.tool()
    async def edit_channels(action: str = "list", name: str | None = None) -> ToolResult:
        """Edit or inspect GIMP channels."""
        normalized = action.strip().lower().replace("-", "_")
        if normalized not in SUPPORTED_CHANNEL_ACTIONS:
            return OperationResult.fail(
                operation="edit_channels",
                error="unsupported channel action",
            ).model_dump()

        payload: dict[str, Any] = {
            "action": normalized,
            "name": name,
            "channels": [],
        }
        return await execute_json_tool(
            bridge,
            operation="edit_channels",
            marker="__gimp_mcp_edit_channels__",
            payload=payload,
            message="Channel operation prepared",
        )
```

For `operation="edit_channels"`, `native_extra_for` appends the shared native GIMP channel code to the generated block. The public handler remains in `layer_tools.py`, while the common execution and JSON result handling stay in the backend helper.



## Current architecture

The backend now uses a small registry-driven code generation layer:

- `NativeOperation` records the operation name, required payload keys, and generator function.
- `NATIVE_OPERATIONS` is the only dispatch table for promoted native backend operations.
- `native_extra_for()` now fails loudly for unknown operations instead of silently emitting payload-only code.
- `CodeBuilder` provides minimal deterministic helpers for adding lines, adding indented blocks, and emitting JSON without introducing a full template engine.
- `generated_context_helpers()` emits GIMP-side context managers for lifecycle-sensitive snippets such as PDB configs, file objects, drawable filters, and temporary duplicate images.

The context managers are generated into the Python that runs inside GIMP. They are not host-side context managers around the bridge call. That distinction matters because GIMP object references, temporary images, PDB configs, and drawable filters must be released in the same interpreter that creates them.

## Native operation lifecycle helpers

Use generated context helpers when a native snippet creates temporary GIMP-side objects:

- `managed_pdb_config(proc)` wraps `proc.create_config()` and releases the config reference.
- `managed_file_obj(path)` wraps `Gio.File.new_for_path(...)` and releases the file object reference.
- `managed_drawable_filter(drawable, operation)` wraps `Gimp.DrawableFilter.new(...)`, exposes `(df, cfg)`, attempts filter removal when available, and releases local references.
- `temporary_duplicate_image(image)` wraps preview-image duplication and deletes the duplicate image in `finally`.

These helpers are currently used by the promoted import/export/PDB/GEGL backend paths. New native snippets should prefer these helpers over hand-written `try/finally` blocks unless the operation needs category-specific rollback behavior.



## Split generator modules

`native_backend.py` now owns only the shared infrastructure: `CodeBuilder`, `NativeOperation`, JSON extraction, generated context-helper snippets, operation registry composition, and bridge execution.

Operation-specific generated code lives in focused modules:

- `native_channels.py` for channel operations.
- `native_paths.py` for path operations.
- `native_exports.py` for import/export operations.
- `native_pdb.py` for PDB introspection and allowlisted PDB calls.
- `native_gegl.py` for GEGL preview/apply operations.
- `native_misc.py` for small promoted helpers that do not yet warrant dedicated modules.

Each split module exposes an `operations()` function returning `dict[str, NativeOperation]`. The core backend composes `NATIVE_OPERATIONS` from those modules, so adding a backend operation means adding it to the correct concern module and registering it there. Keep public MCP tool registration in the category module; the split modules only generate GIMP-side Python snippets.

## Design rules

Keep the module small and infrastructure-focused:

- add public MCP tools to category modules, not here;
- add input validation in category modules before calling `execute_json_tool`;
- keep generated snippets deterministic and JSON-emitting;
- keep operation markers stable so generated-code tests can assert the produced backend path;
- add focused tests whenever a new operation branch is added to `native_extra_for`.

If a native snippet becomes large or category-specific, prefer moving it into the category module or a smaller dedicated helper rather than growing this module indefinitely.
