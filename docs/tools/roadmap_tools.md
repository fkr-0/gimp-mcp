# Roadmap Tools

Source module: `src/gimp_mcp_pro/tools/roadmap_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`edit_channels`](#edit-channels) | Create, inspect, duplicate, rename, or convert channels/selections. | 3 |
| [`manage_channels`](#manage-channels) | Manage saved channels through a consolidated action tool. | 4 |
| [`edit_paths`](#edit-paths) | Inspect, create, transform, stroke, fill, or convert paths. | 4 |
| [`create_and_edit_paths`](#create-and-edit-paths) | Create, list, rename, or update vector paths from typed point data. | 5 |
| [`stroke_or_fill_path`](#stroke-or-fill-path) | Stroke or fill a vector path with supplied paint settings. | 3 |
| [`palette_create_or_update`](#palette-create-or-update) | Create, inspect, or update a palette from provided colors. | 4 |
| [`import_as_layer_with_metadata`](#import-as-layer-with-metadata) | Import an external image as a layer with provenance metadata. | 3 |
| [`batch_export_variants`](#batch-export-variants) | Export multiple bounded variants from the active image. | 3 |
| [`pdb_introspect_typed`](#pdb-introspect-typed) | Return typed PDB procedure metadata for safer wrapper generation. | 3 |
| [`safe_python_eval`](#safe-python-eval) | Run restricted diagnostic Python only when explicitly debug-enabled. | 4 |
| [`manage_guides_and_grid`](#manage-guides-and-grid) | Create, list, move, remove guides, or set document grid settings. | 5 |
| [`preview_gegl_operation`](#preview-gegl-operation) | Render bounded before/after metadata for a GEGL operation without committing. | 4 |

## `edit_channels` {#edit-channels}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:121`

```python
async def edit_channels(action: str, channel: dict[str, Any] | str | None = None, name: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | Channel operation. |
| `channel` | Optional channel reference. |
| `name` | Optional new or target name. |

## Returns

Operation result with channel metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create, inspect, duplicate, rename, or convert channels/selections.

Args:
    action: Channel operation.
    channel: Optional channel reference.
    name: Optional new or target name.

Returns:
    Operation result with channel metadata.

## `manage_channels` {#manage-channels}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:157`

```python
async def manage_channels(action: str = 'list', channel_ref: dict[str, Any] | str | None = None, name: str | None = None, visible: bool | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | list/create/rename/show/hide/to_selection/selection_to_channel. |
| `channel_ref` | Optional channel reference. |
| `name` | Optional channel name. |
| `visible` | Optional visibility flag for update actions. |

## Returns

Operation result with stable channel IDs and selection-change flag.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Manage saved channels through a consolidated action tool.

Args:
    action: list/create/rename/show/hide/to_selection/selection_to_channel.
    channel_ref: Optional channel reference.
    name: Optional channel name.
    visible: Optional visibility flag for update actions.

Returns:
    Operation result with stable channel IDs and selection-change flag.

## `edit_paths` {#edit-paths}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:196`

```python
async def edit_paths(action: str, path: dict[str, Any] | str | None = None, points: list[Any] | None = None, stroke_options: dict[str, Any] | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | Path operation. |
| `path` | Optional path reference. |
| `points` | Optional typed point list. |
| `stroke_options` | Optional stroke/fill options. |

## Returns

Operation result with path metadata and warnings.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Inspect, create, transform, stroke, fill, or convert paths.

Args:
    action: Path operation.
    path: Optional path reference.
    points: Optional typed point list.
    stroke_options: Optional stroke/fill options.

Returns:
    Operation result with path metadata and warnings.

## `create_and_edit_paths` {#create-and-edit-paths}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:235`

```python
async def create_and_edit_paths(action: str, points: list[Any] | None = None, closed: bool = False, path_ref: dict[str, Any] | str | None = None, name: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | create/update/list/rename/delete path action. |
| `points` | Optional flat or object point list. |
| `closed` | Whether a created path should be closed. |
| `path_ref` | Optional existing path reference. |
| `name` | Optional target path name. |

## Returns

Operation result with paths and active path metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create, list, rename, or update vector paths from typed point data.

Args:
    action: create/update/list/rename/delete path action.
    points: Optional flat or object point list.
    closed: Whether a created path should be closed.
    path_ref: Optional existing path reference.
    name: Optional target path name.

Returns:
    Operation result with paths and active path metadata.

## `stroke_or_fill_path` {#stroke-or-fill-path}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:277`

```python
async def stroke_or_fill_path(path_ref: dict[str, Any] | str, mode: str, paint: dict[str, Any] | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `path_ref` | Existing path reference. |
| `mode` | ``stroke`` or ``fill``. |
| `paint` | Optional paint settings. |

## Returns

Operation result with changed bounds and paint settings.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Stroke or fill a vector path with supplied paint settings.

Args:
    path_ref: Existing path reference.
    mode: ``stroke`` or ``fill``.
    paint: Optional paint settings.

Returns:
    Operation result with changed bounds and paint settings.

## `palette_create_or_update` {#palette-create-or-update}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:313`

```python
async def palette_create_or_update(action: str, palette_name: str, colors: list[dict[str, Any]] | None = None, overwrite: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | create/update/inspect. |
| `palette_name` | Palette name. |
| `colors` | Optional named color entries. |
| `overwrite` | Allow replacing an existing palette. |

## Returns

Operation result with palette metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create, inspect, or update a palette from provided colors.

Args:
    action: create/update/inspect.
    palette_name: Palette name.
    colors: Optional named color entries.
    overwrite: Allow replacing an existing palette.

Returns:
    Operation result with palette metadata.

## `import_as_layer_with_metadata` {#import-as-layer-with-metadata}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:353`

```python
async def import_as_layer_with_metadata(source: str, layer_name: str | None = None, placement: dict[str, int] | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `source` | Controlled local source path. |
| `layer_name` | Optional layer name. |
| `placement` | Optional x/y placement. |

## Returns

Operation result with layer and provenance metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Import an external image as a layer with provenance metadata.

Args:
    source: Controlled local source path.
    layer_name: Optional layer name.
    placement: Optional x/y placement.

Returns:
    Operation result with layer and provenance metadata.

## `batch_export_variants` {#batch-export-variants}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:384`

```python
async def batch_export_variants(variants: list[dict[str, Any]], base_path: str, overwrite: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `variants` | Variant definitions with format and optional dimensions. |
| `base_path` | Controlled output base path. |
| `overwrite` | Whether existing files may be overwritten. |

## Returns

Operation result with exported files and warnings.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Export multiple bounded variants from the active image.

Args:
    variants: Variant definitions with format and optional dimensions.
    base_path: Controlled output base path.
    overwrite: Whether existing files may be overwritten.

Returns:
    Operation result with exported files and warnings.

## `pdb_introspect_typed` {#pdb-introspect-typed}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:421`

```python
async def pdb_introspect_typed(query: str, include_deprecated: bool = False, max_results: int = 25) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `query` | Procedure-name search string. |
| `include_deprecated` | Include deprecated procedures where detectable. |
| `max_results` | Maximum procedures to return. |

## Returns

Operation result with procedure signatures and deprecation notes.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Return typed PDB procedure metadata for safer wrapper generation.

Args:
    query: Procedure-name search string.
    include_deprecated: Include deprecated procedures where detectable.
    max_results: Maximum procedures to return.

Returns:
    Operation result with procedure signatures and deprecation notes.

## `safe_python_eval` {#safe-python-eval}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:453`

```python
async def safe_python_eval(code: str, mode: str = 'expression', timeout: float = 1.0, require_debug_enabled: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `code` | Python expression or statement. |
| `mode` | expression or statement. |
| `timeout` | Timeout in seconds. |
| `require_debug_enabled` | Must be true to execute this diagnostic escape hatch. |

## Returns

Operation result with stdout/stderr/result metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Run restricted diagnostic Python only when explicitly debug-enabled.

Args:
    code: Python expression or statement.
    mode: expression or statement.
    timeout: Timeout in seconds.
    require_debug_enabled: Must be true to execute this diagnostic escape hatch.

Returns:
    Operation result with stdout/stderr/result metadata.

## `manage_guides_and_grid` {#manage-guides-and-grid}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:497`

```python
async def manage_guides_and_grid(action: str = 'list', orientation: str | None = None, position: float | None = None, guide_id: int | None = None, grid: dict[str, Any] | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | list/add/move/remove/set_grid. |
| `orientation` | Optional horizontal/vertical orientation. |
| `position` | Optional guide position. |
| `guide_id` | Optional existing guide ID. |
| `grid` | Optional grid settings. |

## Returns

Operation result with guides and grid metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create, list, move, remove guides, or set document grid settings.

Args:
    action: list/add/move/remove/set_grid.
    orientation: Optional horizontal/vertical orientation.
    position: Optional guide position.
    guide_id: Optional existing guide ID.
    grid: Optional grid settings.

Returns:
    Operation result with guides and grid metadata.

## `preview_gegl_operation` {#preview-gegl-operation}

Source: `src/gimp_mcp_pro/tools/roadmap_tools.py:538`

```python
async def preview_gegl_operation(target: dict[str, Any] | str, operation: str, properties: dict[str, Any] | None = None, preview_region: dict[str, int] | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `target` | Layer target reference. |
| `operation` | GEGL operation name. |
| `properties` | Operation properties. |
| `preview_region` | Optional bounded preview rectangle. |

## Returns

Operation result with before/after preview placeholders and metrics.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Render bounded before/after metadata for a GEGL operation without committing.

Args:
    target: Layer target reference.
    operation: GEGL operation name.
    properties: Operation properties.
    preview_region: Optional bounded preview rectangle.

Returns:
    Operation result with before/after preview placeholders and metrics.
