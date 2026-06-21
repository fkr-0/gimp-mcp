# Inspection

Source module: `src/gimp_mcp_pro/tools/inspect_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`get_image_bitmap`](#get-image-bitmap) | Get the current image as a viewable bitmap (PNG). | 6 |
| [`get_image_metadata`](#get-image-metadata) | Get detailed metadata about the active image without bitmap data. | 0 |
| [`get_context_state`](#get-context-state) | Get current GIMP context state (colors, brush, opacity, settings). | 0 |
| [`get_gimp_info`](#get-gimp-info) | Get GIMP environment info (version, paths, capabilities). | 0 |

## `get_image_bitmap` {#get-image-bitmap}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:19`

```python
async def get_image_bitmap(max_width: int | None = 1024, max_height: int | None = 1024, region_x: int | None = None, region_y: int | None = None, region_width: int | None = None, region_height: int | None = None) -> ToolResult
```

**Parameters**

- `max_width`
- `max_height`
- `region_x`
- `region_y`
- `region_width`
- `region_height`

**Docstring**

Get the current image as a viewable bitmap (PNG).

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

## `get_image_metadata` {#get-image-metadata}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:105`

```python
async def get_image_metadata() -> ToolResult
```

**Docstring**

Get detailed metadata about the active image without bitmap data.

Notes:
    Use this tool before any operation — understand canvas dimensions,
    layer structure, and file state. Much faster than get_image_bitmap.

Notes:
    Returned data includes dimensions, color mode, layers, channels,
    paths, and file information.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `get_context_state` {#get-context-state}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:136`

```python
async def get_context_state() -> ToolResult
```

**Docstring**

Get current GIMP context state (colors, brush, opacity, settings).

Warnings:
    Important: Context can be changed by the user in GIMP's UI at any time.
    Check before operations that depend on specific settings.

Notes:
    Returned data includes foreground and background colors, brush info,
    opacity, paint mode, feather state, and antialiasing state.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `get_gimp_info` {#get-gimp-info}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:167`

```python
async def get_gimp_info() -> ToolResult
```

**Docstring**

Get GIMP environment info (version, paths, capabilities).

Notes:
    Use this tool for troubleshooting, environment discovery, or
    understanding what features are available.

Notes:
    Returned data includes the GIMP version, directories, open images,
    PDB availability, current context, system capabilities, and platform info.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
