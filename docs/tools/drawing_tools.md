# Drawing and Text

Source module: `src/gimp_mcp_pro/tools/drawing_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`set_foreground_color`](#set-foreground-color) | Set the foreground color used for drawing operations. | 1 |
| [`set_background_color`](#set-background-color) | Set the background color. | 1 |
| [`fill_selection`](#fill-selection) | Fill the current selection (or entire layer if no selection) with color. | 2 |
| [`draw_line`](#draw-line) | Draw a straight line between two points. | 6 |
| [`draw_brush_stroke`](#draw-brush-stroke) | Draw a stroke along a series of points. | 4 |
| [`draw_rectangle`](#draw-rectangle) | Draw a rectangle (filled or outline only). | 7 |
| [`draw_ellipse`](#draw-ellipse) | Draw an ellipse/circle (filled or outline only). | 7 |
| [`draw_polygon`](#draw-polygon) | Draw a polygon (filled or outline). | 4 |
| [`add_text`](#add-text) | Add a text layer to the image. | 7 |
| [`edit_clear`](#edit-clear) | Clear the current selection area (make it transparent). | 0 |

## `set_foreground_color` {#set-foreground-color}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:50`

```python
async def set_foreground_color(color: str) -> ToolResult
```

**Parameters**

- `color`

**Docstring**

Set the foreground color used for drawing operations.

Notes:
    Use this tool before any drawing, fill, or stroke operation that
    uses the foreground color.

Args:
    color: Color as name ("red"), hex ("#FF0000"), or rgb("rgb(255,0,0)")

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `set_background_color` {#set-background-color}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:80`

```python
async def set_background_color(color: str) -> ToolResult
```

**Parameters**

- `color`

**Docstring**

Set the background color.

Args:
    color: Color as name ("white"), hex ("#FFFFFF"), or rgb("rgb(255,255,255)")

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `fill_selection` {#fill-selection}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:106`

```python
async def fill_selection(fill_type: str = 'foreground', color: str | None = None) -> ToolResult
```

**Parameters**

- `fill_type`
- `color`

**Docstring**

Fill the current selection (or entire layer if no selection) with color.

Notes:
    Use this tool after creating a selection (rectangle, ellipse, polygon),
    fill it with a color to create shapes.

    Best practice guidance:
    - Use polygon selection plus fill for solid shapes instead of paintbrush strokes.
    - Clear the selection after filling; this tool calls select_none automatically.
    - Avoid feathering unless soft edges are intentional.

Args:
    fill_type: "foreground", "background", "white", "transparent", or "pattern"
    color: Optional color to set before filling (sets foreground color).
           Uses current foreground if not specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `draw_line` {#draw-line}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:153`

```python
async def draw_line(x1: float, y1: float, x2: float, y2: float, color: str | None = None, brush_size: float = 2.0) -> ToolResult
```

**Parameters**

- `x1`
- `y1`
- `x2`
- `y2`
- `color`
- `brush_size`

**Docstring**

Draw a straight line between two points.

Args:
    x1, y1: Start coordinates
    x2, y2: End coordinates
    color: Line color. Uses current foreground if not specified.
    brush_size: Line width in pixels (default 2.0)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `draw_brush_stroke` {#draw-brush-stroke}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:192`

```python
async def draw_brush_stroke(points: list[float], tool: str = 'pencil', color: str | None = None, brush_size: float = 2.0) -> ToolResult
```

**Parameters**

- `points`
- `tool`
- `color`
- `brush_size`

**Docstring**

Draw a stroke along a series of points.

Use 'pencil' for hard-edged lines, 'paintbrush' for soft brush strokes.

Notes:
    For filling shapes, do NOT use brush strokes — use polygon
    selection + fill_selection instead. Brush strokes create outlines only.

Args:
    points: Flat list of coordinates [x1, y1, x2, y2, x3, y3, ...]
    tool: "pencil" (hard edge) or "paintbrush" (soft)
    color: Stroke color. Uses current foreground if not specified.
    brush_size: Brush width in pixels

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `draw_rectangle` {#draw-rectangle}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:248`

```python
async def draw_rectangle(x: float, y: float, width: float, height: float, filled: bool = True, color: str | None = None, line_width: float = 2.0) -> ToolResult
```

**Parameters**

- `x`
- `y`
- `width`
- `height`
- `filled`
- `color`
- `line_width`

**Docstring**

Draw a rectangle (filled or outline only).

Notes:
    Best practice: Uses selection + fill for filled rectangles (not brush).
    This produces clean, solid shapes.

Args:
    x, y: Top-left corner coordinates
    width, height: Rectangle dimensions
    filled: True for solid fill, False for outline only
    color: Shape color. Uses current foreground if not specified.
    line_width: Outline width for non-filled rectangles

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `draw_ellipse` {#draw-ellipse}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:307`

```python
async def draw_ellipse(x: float, y: float, width: float, height: float, filled: bool = True, color: str | None = None, line_width: float = 2.0) -> ToolResult
```

**Parameters**

- `x`
- `y`
- `width`
- `height`
- `filled`
- `color`
- `line_width`

**Docstring**

Draw an ellipse/circle (filled or outline only).

For a circle, set width == height.

Args:
    x, y: Bounding box top-left corner
    width, height: Bounding box dimensions
    filled: True for solid fill, False for outline only
    color: Shape color. Uses current foreground if not specified.
    line_width: Outline width for non-filled ellipses

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `draw_polygon` {#draw-polygon}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:362`

```python
async def draw_polygon(points: list[float], filled: bool = True, color: str | None = None, line_width: float = 2.0) -> ToolResult
```

**Parameters**

- `points`
- `filled`
- `color`
- `line_width`

**Docstring**

Draw a polygon (filled or outline).

Notes:
    Best practice: This is THE correct way to draw filled shapes in GIMP.
    Uses polygon selection + fill, producing clean solid shapes.

Args:
    points: Flat list of vertex coordinates [x1,y1, x2,y2, x3,y3, ...]
            Minimum 3 vertices (6 values).
    filled: True for solid fill, False for outline only
    color: Shape color. Uses current foreground if not specified.
    line_width: Outline width for non-filled polygons

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `add_text` {#add-text}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:423`

```python
async def add_text(text: str, x: float = 0.0, y: float = 0.0, font_name: str = 'Sans', font_size: float = 24.0, color: str | None = None, layer_name: str = 'Text') -> ToolResult
```

**Parameters**

- `text`
- `x`
- `y`
- `font_name`
- `font_size`
- `color`
- `layer_name`

**Docstring**

Add a text layer to the image.

Creates a new floating text layer at the specified position.

Args:
    text: The text content to add.
    x: X position for text placement.
    y: Y position for text placement.
    font_name: Font name (e.g., "Sans", "Serif", "Monospace").
    font_size: Font size in pixels.
    color: Text color. Uses current foreground if not specified.
    layer_name: Name for the text layer.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `edit_clear` {#edit-clear}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:493`

```python
async def edit_clear() -> ToolResult
```

**Docstring**

Clear the current selection area (make it transparent).

Notes:
    Use this tool to erase part of a layer. The cleared area becomes
    transparent if the layer has an alpha channel.

Requires: Active layer must have an alpha channel. Use
add_alpha_channel first if needed.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
