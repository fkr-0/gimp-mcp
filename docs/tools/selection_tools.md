# Selections

Source module: `src/gimp_mcp_pro/tools/selection_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`select_rectangle`](#select-rectangle) | Create a rectangular selection. | 6 |
| [`select_ellipse`](#select-ellipse) | Create an elliptical selection. | 6 |
| [`select_polygon`](#select-polygon) | Create a polygon (freeform) selection. | 3 |
| [`select_all`](#select-all) | Select the entire image. | 0 |
| [`select_none`](#select-none) | Clear all selections. | 0 |
| [`select_invert`](#select-invert) | Invert the current selection (select everything NOT currently selected). | 0 |
| [`select_by_color`](#select-by-color) | Select all pixels similar in color to the sampled point. | 6 |
| [`select_layer_alpha`](#select-layer-alpha) | Select a layer's alpha channel using GIMP's image.select_item API. | 3 |
| [`fuzzy_select`](#fuzzy-select) | Select the connected fuzzy/magic-wand region touching a sampled point. | 5 |
| [`select_color`](#select-color) | Globally select pixels matching an explicit color value. | 6 |
| [`feather_selection`](#feather-selection) | Feather the current selection by a radius in pixels. | 1 |
| [`border_selection`](#border-selection) | Replace the current selection with its border. | 1 |
| [`stroke_selection`](#stroke-selection) | Stroke the current selection onto a layer. | 4 |
| [`bucket_fill`](#bucket-fill) | Bucket-fill a contiguous region from a seed point. | 7 |
| [`get_selection_info`](#get-selection-info) | Get information about the current selection (bounds, whether it exists). | 0 |
| [`select_grow`](#select-grow) | Grow the current selection by a number of pixels. | 1 |
| [`select_shrink`](#select-shrink) | Shrink the current selection by a number of pixels. | 1 |

## `select_rectangle` {#select-rectangle}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:46`

```python
async def select_rectangle(x: float, y: float, width: float, height: float, operation: str = 'replace', feather_radius: float = 0.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x, y` | Top-left corner |
| `y` | _Undocumented._ |
| `width, height` | Selection dimensions |
| `height` | _Undocumented._ |
| `operation` | "replace", "add", "subtract", or "intersect" |
| `feather_radius` | Edge feather radius (0 = sharp edges, recommended default) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a rectangular selection.

Notes:
    Use this tool before filling a rectangular area, or to constrain
    operations to a specific region.

Args:
    x, y: Top-left corner
    width, height: Selection dimensions
    operation: "replace", "add", "subtract", or "intersect"
    feather_radius: Edge feather radius (0 = sharp edges, recommended default)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_ellipse` {#select-ellipse}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:89`

```python
async def select_ellipse(x: float, y: float, width: float, height: float, operation: str = 'replace', feather_radius: float = 0.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x, y` | Bounding box top-left corner |
| `y` | _Undocumented._ |
| `width, height` | Bounding box dimensions |
| `height` | _Undocumented._ |
| `operation` | "replace", "add", "subtract", or "intersect" |
| `feather_radius` | Edge feather radius (0 = sharp, recommended) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create an elliptical selection.

For a circular selection, set width == height.

Args:
    x, y: Bounding box top-left corner
    width, height: Bounding box dimensions
    operation: "replace", "add", "subtract", or "intersect"
    feather_radius: Edge feather radius (0 = sharp, recommended)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_polygon` {#select-polygon}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:130`

```python
async def select_polygon(points: list[float], operation: str = 'replace', feather_radius: float = 0.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `points` | Flat list [x1,y1, x2,y2, x3,y3, ...]. Min 3 vertices (6 values). |
| `operation` | "replace", "add", "subtract", or "intersect" |
| `feather_radius` | Edge feather radius (0 = sharp, recommended) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a polygon (freeform) selection.

Notes:
    Best practice: Use polygon selection + fill_selection for solid shapes.
    This is the recommended way to draw filled shapes in GIMP.

Args:
    points: Flat list [x1,y1, x2,y2, x3,y3, ...]. Min 3 vertices (6 values).
    operation: "replace", "add", "subtract", or "intersect"
    feather_radius: Edge feather radius (0 = sharp, recommended)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_all` {#select-all}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:175`

```python
async def select_all() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Select the entire image.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_none` {#select-none}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:194`

```python
async def select_none() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Clear all selections.

Warnings:
    Important: Always call this after fill/stroke operations on selections
    to avoid unexpected behavior on subsequent operations.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_invert` {#select-invert}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:219`

```python
async def select_invert() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Invert the current selection (select everything NOT currently selected).

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_by_color` {#select-by-color}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:240`

```python
async def select_by_color(x: float, y: float, threshold: float = 15.0, operation: str = 'replace', sample_merged: bool = False, contiguous: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x` | Sample point X coordinate (pixel to sample color from) |
| `y` | Sample point Y coordinate |
| `threshold` | Color similarity threshold 0-255 (lower = more exact match, higher = more tolerance). Default 15. |
| `operation` | "replace", "add", "subtract", or "intersect" |
| `sample_merged` | If True, sample color from all visible layers merged. If False (default), sample from active layer only. |
| `contiguous` | If True, select only the connected blob touching (x, y). If False (default), select matching color globally across the drawable. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Select all pixels similar in color to the sampled point.

Notes:
    Useful for selecting uniform backgrounds, solid-color regions, or
    isolating objects by their surrounding color.

Args:
    x: Sample point X coordinate (pixel to sample color from)
    y: Sample point Y coordinate
    threshold: Color similarity threshold 0-255 (lower = more exact match,
        higher = more tolerance). Default 15.
    operation: "replace", "add", "subtract", or "intersect"
    sample_merged: If True, sample color from all visible layers merged.
        If False (default), sample from active layer only.
    contiguous: If True, select only the connected blob touching (x, y).
        If False (default), select matching color globally across the drawable.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_layer_alpha` {#select-layer-alpha}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:331`

```python
async def select_layer_alpha(layer_name: str | None = None, layer_index: int | None = None, operation: str = 'replace') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Layer name to select from. |
| `layer_index` | Layer index to select from. Uses the active layer if neither is supplied. |
| `operation` | "replace", "add", "subtract", or "intersect". |

## Returns

Operation result dictionary with alpha-selection metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Select a layer's alpha channel using GIMP's image.select_item API.

Args:
    layer_name: Layer name to select from.
    layer_index: Layer index to select from. Uses the active layer if neither is supplied.
    operation: "replace", "add", "subtract", or "intersect".

Returns:
    Operation result dictionary with alpha-selection metadata.

## `fuzzy_select` {#fuzzy-select}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:375`

```python
async def fuzzy_select(x: float, y: float, threshold: float = 15.0, operation: str = 'replace', sample_merged: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x` | Sample point X coordinate. |
| `y` | Sample point Y coordinate. |
| `threshold` | Color similarity threshold 0-255. |
| `operation` | "replace", "add", "subtract", or "intersect". |
| `sample_merged` | If True, sample all visible layers merged. |

## Returns

Operation result dictionary with selection bounds and fuzzy-select metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Select the connected fuzzy/magic-wand region touching a sampled point.

Args:
    x: Sample point X coordinate.
    y: Sample point Y coordinate.
    threshold: Color similarity threshold 0-255.
    operation: "replace", "add", "subtract", or "intersect".
    sample_merged: If True, sample all visible layers merged.

Returns:
    Operation result dictionary with selection bounds and fuzzy-select metadata.

## `select_color` {#select-color}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:410`

```python
async def select_color(color: str, threshold: float = 15.0, operation: str = 'replace', sample_merged: bool = False, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `color` | Color to select, for example "#f2dfc0", "white", or "rgb(255,0,0)". |
| `threshold` | Color similarity threshold 0-255. |
| `operation` | "replace", "add", "subtract", or "intersect". |
| `sample_merged` | If True, configure GIMP's sample-merged context while selecting. |
| `layer_name` | Drawable layer by name. Uses active layer if omitted. |
| `layer_index` | Drawable layer index. Uses active layer if omitted. |

## Returns

Operation result dictionary with selection bounds and explicit-color metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Globally select pixels matching an explicit color value.

Args:
    color: Color to select, for example "#f2dfc0", "white", or "rgb(255,0,0)".
    threshold: Color similarity threshold 0-255.
    operation: "replace", "add", "subtract", or "intersect".
    sample_merged: If True, configure GIMP's sample-merged context while selecting.
    layer_name: Drawable layer by name. Uses active layer if omitted.
    layer_index: Drawable layer index. Uses active layer if omitted.

Returns:
    Operation result dictionary with selection bounds and explicit-color metadata.

## `feather_selection` {#feather-selection}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:493`

```python
async def feather_selection(radius: float) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `radius` | Feather radius. Use 0 for no feather; positive values soften edges. |

## Returns

Operation result dictionary with status, message, and radius metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Feather the current selection by a radius in pixels.

Args:
    radius: Feather radius. Use 0 for no feather; positive values soften edges.

Returns:
    Operation result dictionary with status, message, and radius metadata.

## `border_selection` {#border-selection}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:523`

```python
async def border_selection(radius: int) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `radius` | Border radius in pixels. Must be greater than 0. |

## Returns

Operation result dictionary with status, message, and radius metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Replace the current selection with its border.

Args:
    radius: Border radius in pixels. Must be greater than 0.

Returns:
    Operation result dictionary with status, message, and radius metadata.

## `stroke_selection` {#stroke-selection}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:553`

```python
async def stroke_selection(color: str | None = None, brush_size: float | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `color` | Optional foreground color to use for the stroke. |
| `brush_size` | Optional stroke line width in pixels. |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with status, message, and stroke metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Stroke the current selection onto a layer.

Args:
    color: Optional foreground color to use for the stroke.
    brush_size: Optional stroke line width in pixels.
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and stroke metadata.

## `bucket_fill` {#bucket-fill}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:656`

```python
async def bucket_fill(x: float, y: float, color: str | None = None, threshold: float = 15.0, sample_merged: bool = False, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x` | Seed point X coordinate. |
| `y` | Seed point Y coordinate. |
| `color` | Optional foreground color to use before filling. |
| `threshold` | Color similarity threshold 0-255. |
| `sample_merged` | If True, sample from merged visible layers. |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with status, message, and fill metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Bucket-fill a contiguous region from a seed point.

Args:
    x: Seed point X coordinate.
    y: Seed point Y coordinate.
    color: Optional foreground color to use before filling.
    threshold: Color similarity threshold 0-255.
    sample_merged: If True, sample from merged visible layers.
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and fill metadata.

## `get_selection_info` {#get-selection-info}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:774`

```python
async def get_selection_info() -> ToolResult
```

## Returns

Selection info: has_selection, bounds (x, y, width, height), and whether it covers the full image.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Get information about the current selection (bounds, whether it exists).

Notes:
    Use this to check whether a selection is active and where it is
    before performing fill, stroke, or other selection-dependent operations.

Returns:
    Selection info: has_selection, bounds (x, y, width, height),
    and whether it covers the full image.

## `select_grow` {#select-grow}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:830`

```python
async def select_grow(radius: int) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `radius` | Number of pixels to grow the selection by. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Grow the current selection by a number of pixels.

Args:
    radius: Number of pixels to grow the selection by.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_shrink` {#select-shrink}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:854`

```python
async def select_shrink(radius: int) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `radius` | Number of pixels to shrink the selection by. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Shrink the current selection by a number of pixels.

Args:
    radius: Number of pixels to shrink the selection by.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
