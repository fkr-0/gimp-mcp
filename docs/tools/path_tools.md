# Vector Paths

Source module: `src/gimp_mcp_pro/tools/path_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`create_path`](#create-path) | Create a vector path from a flat point list. | 4 |
| [`list_paths`](#list-paths) | List vector paths in the active image. | 0 |
| [`path_to_selection`](#path-to-selection) | Convert a vector path to the current selection. | 3 |
| [`stroke_path`](#stroke-path) | Stroke a vector path onto a layer using the current or supplied context. | 6 |
| [`remove_path`](#remove-path) | Remove a vector path from the active image. | 2 |

## `create_path` {#create-path}

Source: `src/gimp_mcp_pro/tools/path_tools.py:72`

```python
async def create_path(points: list[float], name: str = 'Path', closed: bool = False, position: int = 0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `points` | Flat list [x1, y1, x2, y2, ...]. Minimum 3 vertices. |
| `name` | New path name. |
| `closed` | Whether to close the path stroke. |
| `position` | Path stack position. |

## Returns

Operation result with created path metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a vector path from a flat point list.

Args:
    points: Flat list [x1, y1, x2, y2, ...]. Minimum 3 vertices.
    name: New path name.
    closed: Whether to close the path stroke.
    position: Path stack position.

Returns:
    Operation result with created path metadata.

## `list_paths` {#list-paths}

Source: `src/gimp_mcp_pro/tools/path_tools.py:123`

```python
async def list_paths() -> ToolResult
```

## Returns

Operation result dictionary with path names, indexes, stroke counts, and total count.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List vector paths in the active image.

Returns:
    Operation result dictionary with path names, indexes, stroke counts, and total count.

## `path_to_selection` {#path-to-selection}

Source: `src/gimp_mcp_pro/tools/path_tools.py:161`

```python
async def path_to_selection(path_name: str | None = None, path_index: int | None = None, operation: str = 'replace') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `path_name` | Target path by name. |
| `path_index` | Target path by index. Uses selected or first path if neither specified. |
| `operation` | "replace", "add", "subtract", or "intersect". |

## Returns

Operation result dictionary with selection conversion metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Convert a vector path to the current selection.

Args:
    path_name: Target path by name.
    path_index: Target path by index. Uses selected or first path if neither specified.
    operation: "replace", "add", "subtract", or "intersect".

Returns:
    Operation result dictionary with selection conversion metadata.

## `stroke_path` {#stroke-path}

Source: `src/gimp_mcp_pro/tools/path_tools.py:198`

```python
async def stroke_path(path_name: str | None = None, path_index: int | None = None, color: str | None = None, brush_size: float | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `path_name` | Target path by name. |
| `path_index` | Target path by index. Uses selected or first path if neither specified. |
| `color` | Optional foreground color to use before stroking. |
| `brush_size` | Optional line width in pixels. |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with path stroke metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Stroke a vector path onto a layer using the current or supplied context.

Args:
    path_name: Target path by name.
    path_index: Target path by index. Uses selected or first path if neither specified.
    color: Optional foreground color to use before stroking.
    brush_size: Optional line width in pixels.
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with path stroke metadata.

## `remove_path` {#remove-path}

Source: `src/gimp_mcp_pro/tools/path_tools.py:251`

```python
async def remove_path(path_name: str | None = None, path_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `path_name` | Target path by name. |
| `path_index` | Target path by index. Uses selected or first path if neither specified. |

## Returns

Operation result dictionary with removed path metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Remove a vector path from the active image.

Args:
    path_name: Target path by name.
    path_index: Target path by index. Uses selected or first path if neither specified.

Returns:
    Operation result dictionary with removed path metadata.
