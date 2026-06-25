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
| [`create_text_box`](#create-text-box) | Create a new text layer at an explicit rectangle with styling. | 4 |
| [`add_text`](#add-text) | Add a text layer to the image. | 7 |
| [`gradient_fill`](#gradient-fill) | Fill the current drawable/selection with a gradient between two points. | 12 |
| [`edit_text_layer`](#edit-text-layer) | Edit an existing text layer's content and core text properties. | 7 |
| [`edit_clear`](#edit-clear) | Clear the current selection area (make it transparent). | 0 |

## `set_foreground_color` {#set-foreground-color}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:124`

```python
async def set_foreground_color(color: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `color` | Color as name ("red"), hex ("#FF0000"), or rgb("rgb(255,0,0)") |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Set the foreground color used for drawing operations.

Notes:
    Use this tool before any drawing, fill, or stroke operation that
    uses the foreground color.

Args:
    color: Color as name ("red"), hex ("#FF0000"), or rgb("rgb(255,0,0)")

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `set_background_color` {#set-background-color}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:154`

```python
async def set_background_color(color: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `color` | Color as name ("white"), hex ("#FFFFFF"), or rgb("rgb(255,255,255)") |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Set the background color.

Args:
    color: Color as name ("white"), hex ("#FFFFFF"), or rgb("rgb(255,255,255)")

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `fill_selection` {#fill-selection}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:180`

```python
async def fill_selection(fill_type: str = 'foreground', color: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `fill_type` | "foreground", "background", "white", "transparent", or "pattern" |
| `color` | Optional color to set before filling (sets foreground color). Uses current foreground if not specified. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:227`

```python
async def draw_line(x1: float, y1: float, x2: float, y2: float, color: str | None = None, brush_size: float = 2.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x1, y1` | Start coordinates |
| `y1` | _Undocumented._ |
| `x2, y2` | End coordinates |
| `y2` | _Undocumented._ |
| `color` | Line color. Uses current foreground if not specified. |
| `brush_size` | Line width in pixels (default 2.0) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Draw a straight line between two points.

Args:
    x1, y1: Start coordinates
    x2, y2: End coordinates
    color: Line color. Uses current foreground if not specified.
    brush_size: Line width in pixels (default 2.0)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `draw_brush_stroke` {#draw-brush-stroke}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:266`

```python
async def draw_brush_stroke(points: list[float], tool: str = 'pencil', color: str | None = None, brush_size: float = 2.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `points` | Flat list of coordinates [x1, y1, x2, y2, x3, y3, ...] |
| `tool` | "pencil" (hard edge) or "paintbrush" (soft) |
| `color` | Stroke color. Uses current foreground if not specified. |
| `brush_size` | Brush width in pixels |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:322`

```python
async def draw_rectangle(x: float, y: float, width: float, height: float, filled: bool = True, color: str | None = None, line_width: float = 2.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x, y` | Top-left corner coordinates |
| `y` | _Undocumented._ |
| `width, height` | Rectangle dimensions |
| `height` | _Undocumented._ |
| `filled` | True for solid fill, False for outline only |
| `color` | Shape color. Uses current foreground if not specified. |
| `line_width` | Outline width for non-filled rectangles |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:381`

```python
async def draw_ellipse(x: float, y: float, width: float, height: float, filled: bool = True, color: str | None = None, line_width: float = 2.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x, y` | Bounding box top-left corner |
| `y` | _Undocumented._ |
| `width, height` | Bounding box dimensions |
| `height` | _Undocumented._ |
| `filled` | True for solid fill, False for outline only |
| `color` | Shape color. Uses current foreground if not specified. |
| `line_width` | Outline width for non-filled ellipses |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:436`

```python
async def draw_polygon(points: list[float], filled: bool = True, color: str | None = None, line_width: float = 2.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `points` | Flat list of vertex coordinates [x1,y1, x2,y2, x3,y3, ...] Minimum 3 vertices (6 values). |
| `filled` | True for solid fill, False for outline only |
| `color` | Shape color. Uses current foreground if not specified. |
| `line_width` | Outline width for non-filled polygons |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

## `create_text_box` {#create-text-box}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:497`

```python
async def create_text_box(text: str, rectangle: dict[str, int], style: dict[str, object] | None = None, name: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `text` | Text content for the new layer. |
| `rectangle` | Mapping with x, y, width, and height. |
| `style` | Optional font, font_size, color, and justification settings. |
| `name` | Optional layer name. |

## Returns

Operation result with requested text-box bounds and style metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a new text layer at an explicit rectangle with styling.

Args:
    text: Text content for the new layer.
    rectangle: Mapping with x, y, width, and height.
    style: Optional font, font_size, color, and justification settings.
    name: Optional layer name.

Returns:
    Operation result with requested text-box bounds and style metadata.

## `add_text` {#add-text}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:545`

```python
async def add_text(text: str, x: float = 0.0, y: float = 0.0, font_name: str = 'Sans', font_size: float = 24.0, color: str | None = None, layer_name: str = 'Text') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `text` | The text content to add. |
| `x` | X position for text placement. |
| `y` | Y position for text placement. |
| `font_name` | Font name (e.g., "Sans", "Serif", "Monospace"). |
| `font_size` | Font size in pixels. |
| `color` | Text color. Uses current foreground if not specified. |
| `layer_name` | Name for the text layer. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

## `gradient_fill` {#gradient-fill}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:615`

```python
async def gradient_fill(x1: float, y1: float, x2: float, y2: float, gradient_type: str = 'linear', foreground_color: str | None = None, background_color: str | None = None, offset: float = 0.0, dither: bool = True, supersample: bool = False, supersample_max_depth: int = 3, supersample_threshold: float = 0.2) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x1, y1` | Gradient start coordinate. |
| `y1` | _Undocumented._ |
| `x2, y2` | Gradient end coordinate. |
| `y2` | _Undocumented._ |
| `gradient_type` | linear, bilinear, radial, square, conical_symmetric, conical_asymmetric, shapeburst_angular, shapeburst_spherical, shapeburst_dimpled, spiral_clockwise, or spiral_anticlockwise. |
| `foreground_color` | Optional foreground color for FG/BG gradients. |
| `background_color` | Optional background color for FG/BG gradients. |
| `offset` | Mode-dependent gradient offset. |
| `dither` | Whether to dither to reduce banding. |
| `supersample` | Whether to use adaptive supersampling. |
| `supersample_max_depth` | Maximum supersampling recursion depth. |
| `supersample_threshold` | Supersampling threshold. |

## Returns

Operation result dictionary with status, message, and gradient metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Fill the current drawable/selection with a gradient between two points.

Args:
    x1, y1: Gradient start coordinate.
    x2, y2: Gradient end coordinate.
    gradient_type: linear, bilinear, radial, square, conical_symmetric,
        conical_asymmetric, shapeburst_angular, shapeburst_spherical,
        shapeburst_dimpled, spiral_clockwise, or spiral_anticlockwise.
    foreground_color: Optional foreground color for FG/BG gradients.
    background_color: Optional background color for FG/BG gradients.
    offset: Mode-dependent gradient offset.
    dither: Whether to dither to reduce banding.
    supersample: Whether to use adaptive supersampling.
    supersample_max_depth: Maximum supersampling recursion depth.
    supersample_threshold: Supersampling threshold.

Returns:
    Operation result dictionary with status, message, and gradient metadata.

## `edit_text_layer` {#edit-text-layer}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:701`

```python
async def edit_text_layer(text: str | None = None, layer_name: str | None = None, layer_index: int | None = None, font_name: str | None = None, font_size: float | None = None, color: str | None = None, justification: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `text` | New text content. Leave unset to keep existing text. |
| `layer_name` | Text layer name to edit. |
| `layer_index` | Text layer index to edit. Uses active layer if neither specified. |
| `font_name` | Optional new font name. |
| `font_size` | Optional new font size in pixels. |
| `color` | Optional text color. |
| `justification` | Optional alignment: left, right, center, or fill. |

## Returns

Operation result dictionary with status, message, and edited fields.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Edit an existing text layer's content and core text properties.

Args:
    text: New text content. Leave unset to keep existing text.
    layer_name: Text layer name to edit.
    layer_index: Text layer index to edit. Uses active layer if neither specified.
    font_name: Optional new font name.
    font_size: Optional new font size in pixels.
    color: Optional text color.
    justification: Optional alignment: left, right, center, or fill.

Returns:
    Operation result dictionary with status, message, and edited fields.

## `edit_clear` {#edit-clear}

Source: `src/gimp_mcp_pro/tools/drawing_tools.py:819`

```python
async def edit_clear() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Clear the current selection area (make it transparent).

Notes:
    Use this tool to erase part of a layer. The cleared area becomes
    transparent if the layer has an alpha channel.

Requires: Active layer must have an alpha channel. Use
add_alpha_channel first if needed.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
