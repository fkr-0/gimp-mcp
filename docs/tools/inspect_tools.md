# Inspection

Source module: `src/gimp_mcp_pro/tools/inspect_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`session_capabilities`](#session-capabilities) | Report GIMP runtime capabilities and safety-relevant environment state. | 2 |
| [`observe_document_state`](#observe-document-state) | Return a compact snapshot of the active GIMP document state. | 3 |
| [`get_layer_tree_detailed`](#get-layer-tree-detailed) | Return detailed layer, group, visibility, lock, and bounds metadata. | 3 |
| [`observe_region`](#observe-region) | Return a bounded visual observation and metadata for a rectangular region. | 6 |
| [`get_image_bitmap`](#get-image-bitmap) | Get the current image as a viewable bitmap (PNG). | 6 |
| [`get_image_metadata`](#get-image-metadata) | Get detailed metadata about the active image without bitmap data. | 0 |
| [`get_context_state`](#get-context-state) | Get current GIMP context state (colors, brush, opacity, settings). | 0 |
| [`get_gimp_info`](#get-gimp-info) | Get GIMP environment info (version, paths, capabilities). | 0 |

## `session_capabilities` {#session-capabilities}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:226`

```python
async def session_capabilities(include_pdb_probe: bool = True, include_export_probe: bool = True) -> ToolResult
```

**Parameters**

- `include_pdb_probe`
- `include_export_probe`

**Docstring**

Report GIMP runtime capabilities and safety-relevant environment state.

Notes:
    This read-only tool should be the first call in an autonomous workflow.
    It tells the agent which GIMP version, plug-in version, PDB procedures,
    export procedures, and safety mode are currently available.

Args:
    include_pdb_probe: Probe selected PDB procedures by name.
    include_export_probe: Include export-specific procedure availability.

Returns:
    Operation result with version, capability, unavailable-procedure, and safety data.

## `observe_document_state` {#observe-document-state}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:259`

```python
async def observe_document_state(include_thumbnail: bool = False, include_layer_previews: bool = False, max_preview_size: int = 256) -> ToolResult
```

**Parameters**

- `include_thumbnail`
- `include_layer_previews`
- `max_preview_size`

**Docstring**

Return a compact snapshot of the active GIMP document state.

Notes:
    Use this before planning edits. It includes stable image/layer IDs,
    dimensions, active layer, selected layers, layer tree, selection state,
    guides, paths, channels, and optional bounded thumbnail evidence.

Args:
    include_thumbnail: Include a bounded PNG thumbnail of the active document.
    include_layer_previews: Reserved flag for future per-layer previews.
    max_preview_size: Maximum thumbnail width/height when thumbnail is requested.

Returns:
    Operation result with document state and optional thumbnail metadata.

## `get_layer_tree_detailed` {#get-layer-tree-detailed}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:317`

```python
async def get_layer_tree_detailed(image_id: int | None = None, include_pixel_bounds: bool = True, include_text_metadata: bool = True) -> ToolResult
```

**Parameters**

- `image_id`
- `include_pixel_bounds`
- `include_text_metadata`

**Docstring**

Return detailed layer, group, visibility, lock, and bounds metadata.

Notes:
    Use this before mutating layers. It identifies hidden or content-locked
    layers and returns stable IDs, names, indices, dimensions, offsets,
    opacity, mode, alpha, type hints, and group hints where GIMP exposes them.

Args:
    image_id: Optional image ID hint. Current implementation observes the active image.
    include_pixel_bounds: Include layer pixel bounds when available.
    include_text_metadata: Include text-layer metadata when available.

Returns:
    Operation result with layers, groups, and editability warnings.

## `observe_region` {#observe-region}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:353`

```python
async def observe_region(x: int, y: int, width: int, height: int, max_size: int = 512, include_histogram: bool = False) -> ToolResult
```

**Parameters**

- `x`
- `y`
- `width`
- `height`
- `max_size`
- `include_histogram`

**Docstring**

Return a bounded visual observation and metadata for a rectangular region.

Notes:
    Use this to inspect details without transferring the full canvas. The
    bitmap is downsampled to max_size and accompanied by actual source
    bounds plus a small set of sampled colors.

Args:
    x: Region left coordinate in canvas pixels.
    y: Region top coordinate in canvas pixels.
    width: Region width in pixels.
    height: Region height in pixels.
    max_size: Maximum output width/height for the region PNG.
    include_histogram: Reserve space for histogram data when implemented.

Returns:
    Operation result with cropped PNG data, region bounds, samples, and metadata.

## `get_image_bitmap` {#get-image-bitmap}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:430`

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:514`

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:545`

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:576`

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
