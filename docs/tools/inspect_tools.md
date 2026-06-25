# Inspection

Source module: `src/gimp_mcp_pro/tools/inspect_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`create_contact_sheet`](#create-contact-sheet) | Render contact-sheet metadata for visible or selected layers. | 4 |
| [`compare_snapshots`](#compare-snapshots) | Compare two supplied snapshot, thumbnail, or region payloads. | 6 |
| [`assert_image_state`](#assert-image-state) | Evaluate typed postconditions against supplied or active document state. | 2 |
| [`session_capabilities`](#session-capabilities) | Report GIMP runtime capabilities and safety-relevant environment state. | 2 |
| [`observe_document_state`](#observe-document-state) | Return a compact snapshot of the active GIMP document state. | 3 |
| [`get_layer_tree_detailed`](#get-layer-tree-detailed) | Return detailed layer, group, visibility, lock, and bounds metadata. | 3 |
| [`observe_region`](#observe-region) | Return a bounded visual observation and metadata for a rectangular region. | 6 |
| [`get_image_bitmap`](#get-image-bitmap) | Get the current image as a viewable bitmap (PNG). | 6 |
| [`get_image_metadata`](#get-image-metadata) | Get detailed metadata about the active image without bitmap data. | 0 |
| [`get_context_state`](#get-context-state) | Get current GIMP context state (colors, brush, opacity, settings). | 0 |
| [`get_gimp_info`](#get-gimp-info) | Get GIMP environment info (version, paths, capabilities). | 0 |

## `create_contact_sheet` {#create-contact-sheet}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:534`

```python
async def create_contact_sheet(target: str = 'visible_layers', max_tile_size: int = 128, label_tiles: bool = True, include_hidden_layers: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `target` | Layer candidate set, currently ``visible_layers`` or ``all_layers``. |
| `max_tile_size` | Maximum tile size requested for future bitmap rendering. |
| `label_tiles` | Include stable layer ID/name labels in the tile index. |
| `include_hidden_layers` | Include hidden layers instead of filtering them out. |

## Returns

Operation result with ``contact_sheet_png`` placeholder and authoritative tile index. Contract: This inspection tool is read-only. It labels tiles with stable layer IDs and applies the hidden-layer policy explicitly.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Render contact-sheet metadata for visible or selected layers.

Args:
    target: Layer candidate set, currently ``visible_layers`` or ``all_layers``.
    max_tile_size: Maximum tile size requested for future bitmap rendering.
    label_tiles: Include stable layer ID/name labels in the tile index.
    include_hidden_layers: Include hidden layers instead of filtering them out.

Returns:
    Operation result with ``contact_sheet_png`` placeholder and authoritative tile index.

Contract:
    This inspection tool is read-only. It labels tiles with stable layer IDs
    and applies the hidden-layer policy explicitly.

## `compare_snapshots` {#compare-snapshots}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:581`

```python
async def compare_snapshots(before: dict[str, Any], after: dict[str, Any], metrics: list[str] | None = None, region: dict[str, Any] | None = None, ignore_transparent: bool = False, tolerance: float = 0.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `before` | Snapshot-like payload captured before an operation. |
| `after` | Snapshot-like payload captured after an operation. |
| `metrics` | Optional metric names requested by the caller. |
| `region` | Optional bounded region to limit sampled-color comparison. |
| `ignore_transparent` | Ignore sampled points where either side is fully transparent. |
| `tolerance` | RGBA mean absolute delta threshold for sampled colors. |

## Returns

Operation result with changed sample count, bounding box, mean delta, and changed fields.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Compare two supplied snapshot, thumbnail, or region payloads.

Notes:
    This verification tool is intentionally read-only and deterministic.
    It compares sampled region colors when present, otherwise falls back
    to stable scalar-field differences. Ordinary visual mismatches are
    returned as structured data, not exceptions.

Args:
    before: Snapshot-like payload captured before an operation.
    after: Snapshot-like payload captured after an operation.
    metrics: Optional metric names requested by the caller.
    region: Optional bounded region to limit sampled-color comparison.
    ignore_transparent: Ignore sampled points where either side is fully transparent.
    tolerance: RGBA mean absolute delta threshold for sampled colors.

Returns:
    Operation result with changed sample count, bounding box, mean delta, and changed fields.

## `assert_image_state` {#assert-image-state}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:633`

```python
async def assert_image_state(assertions: list[dict[str, Any]] | None = None, state: dict[str, Any] | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `assertions` | List of typed assertion dictionaries. |
| `state` | Optional state payload. When absent, the active GIMP document is observed. |

## Returns

Operation result whose data contains ``passed`` plus per-assertion results.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Evaluate typed postconditions against supplied or active document state.

Notes:
    Use this after edits to verify facts such as layer existence,
    layer visibility, canvas dimensions, non-empty selection, and color
    closeness. Failed assertions are reported in ``data.results`` while
    the tool call itself still succeeds.

Args:
    assertions: List of typed assertion dictionaries.
    state: Optional state payload. When absent, the active GIMP document is observed.

Returns:
    Operation result whose data contains ``passed`` plus per-assertion results.

## `session_capabilities` {#session-capabilities}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:700`

```python
async def session_capabilities(include_pdb_probe: bool = True, include_export_probe: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `include_pdb_probe` | Probe selected PDB procedures by name. |
| `include_export_probe` | Include export-specific procedure availability. |

## Returns

Operation result with version, capability, unavailable-procedure, and safety data.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:733`

```python
async def observe_document_state(include_thumbnail: bool = False, include_layer_previews: bool = False, max_preview_size: int = 256) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `include_thumbnail` | Include a bounded PNG thumbnail of the active document. |
| `include_layer_previews` | Reserved flag for future per-layer previews. |
| `max_preview_size` | Maximum thumbnail width/height when thumbnail is requested. |

## Returns

Operation result with document state and optional thumbnail metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:791`

```python
async def get_layer_tree_detailed(image_id: int | None = None, include_pixel_bounds: bool = True, include_text_metadata: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `image_id` | Optional image ID hint. Current implementation observes the active image. |
| `include_pixel_bounds` | Include layer pixel bounds when available. |
| `include_text_metadata` | Include text-layer metadata when available. |

## Returns

Operation result with layers, groups, and editability warnings.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:827`

```python
async def observe_region(x: int, y: int, width: int, height: int, max_size: int = 512, include_histogram: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x` | Region left coordinate in canvas pixels. |
| `y` | Region top coordinate in canvas pixels. |
| `width` | Region width in pixels. |
| `height` | Region height in pixels. |
| `max_size` | Maximum output width/height for the region PNG. |
| `include_histogram` | Reserve space for histogram data when implemented. |

## Returns

Operation result with cropped PNG data, region bounds, samples, and metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:904`

```python
async def get_image_bitmap(max_width: int | None = 1024, max_height: int | None = 1024, region_x: int | None = None, region_y: int | None = None, region_width: int | None = None, region_height: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `max_width` | Optional maximum width for scaling (default 1024). Use None for full size. |
| `max_height` | Optional maximum height for scaling (default 1024). Use None for full size. |
| `region_x` | Optional — extract only this region (left X) |
| `region_y` | Optional — extract only this region (top Y) |
| `region_width` | Optional — region width |
| `region_height` | Optional — region height |

## Returns

MCP Image object containing PNG data that the AI can view directly.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Get the current image as a viewable bitmap (PNG).

Notes:
    Primary use: Verification tool for checking work mid-workflow.

    Best practice guidance:
    - Check after every three to five drawing operations.
    - Use region extraction to verify specific areas at higher quality.
    - Check before the final step so mistakes are caught early.

Args:
    max_width: Optional maximum width for scaling (default 1024). Use None for full size.
    max_height: Optional maximum height for scaling (default 1024). Use None for full size.
    region_x: Optional — extract only this region (left X)
    region_y: Optional — extract only this region (top Y)
    region_width: Optional — region width
    region_height: Optional — region height

Returns:
    MCP Image object containing PNG data that the AI can view directly.

## `get_image_metadata` {#get-image-metadata}

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:988`

```python
async def get_image_metadata() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:1019`

```python
async def get_context_state() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/inspect_tools.py:1050`

```python
async def get_gimp_info() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Get GIMP environment info (version, paths, capabilities).

Notes:
    Use this tool for troubleshooting, environment discovery, or
    understanding what features are available.

Notes:
    Returned data includes the GIMP version, directories, open images,
    PDB availability, current context, system capabilities, and platform info.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
