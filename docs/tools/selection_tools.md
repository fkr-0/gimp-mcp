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
| [`select_grow`](#select-grow) | Grow the current selection by a number of pixels. | 1 |
| [`select_shrink`](#select-shrink) | Shrink the current selection by a number of pixels. | 1 |

## `select_rectangle` {#select-rectangle}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:24`

```python
async def select_rectangle(x: float, y: float, width: float, height: float, operation: str = 'replace', feather_radius: float = 0.0) -> ToolResult
```

**Parameters**

- `x`
- `y`
- `width`
- `height`
- `operation`
- `feather_radius`

**Docstring**

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

Source: `src/gimp_mcp_pro/tools/selection_tools.py:67`

```python
async def select_ellipse(x: float, y: float, width: float, height: float, operation: str = 'replace', feather_radius: float = 0.0) -> ToolResult
```

**Parameters**

- `x`
- `y`
- `width`
- `height`
- `operation`
- `feather_radius`

**Docstring**

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

Source: `src/gimp_mcp_pro/tools/selection_tools.py:108`

```python
async def select_polygon(points: list[float], operation: str = 'replace', feather_radius: float = 0.0) -> ToolResult
```

**Parameters**

- `points`
- `operation`
- `feather_radius`

**Docstring**

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

Source: `src/gimp_mcp_pro/tools/selection_tools.py:153`

```python
async def select_all() -> ToolResult
```

**Docstring**

Select the entire image.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_none` {#select-none}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:172`

```python
async def select_none() -> ToolResult
```

**Docstring**

Clear all selections.

Warnings:
    Important: Always call this after fill/stroke operations on selections
    to avoid unexpected behavior on subsequent operations.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_invert` {#select-invert}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:197`

```python
async def select_invert() -> ToolResult
```

**Docstring**

Invert the current selection (select everything NOT currently selected).

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_grow` {#select-grow}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:218`

```python
async def select_grow(radius: int) -> ToolResult
```

**Parameters**

- `radius`

**Docstring**

Grow the current selection by a number of pixels.

Args:
    radius: Number of pixels to grow the selection by.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `select_shrink` {#select-shrink}

Source: `src/gimp_mcp_pro/tools/selection_tools.py:242`

```python
async def select_shrink(radius: int) -> ToolResult
```

**Parameters**

- `radius`

**Docstring**

Shrink the current selection by a number of pixels.

Args:
    radius: Number of pixels to shrink the selection by.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
