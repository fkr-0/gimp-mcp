# Transforms

Source module: `src/gimp_mcp_pro/tools/transform_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`align_and_distribute_layers`](#align-and-distribute-layers) | Align or distribute layers relative to the canvas with verification bounds. | 5 |
| [`scale_image`](#scale-image) | Scale the entire image (all layers) to new dimensions. | 3 |
| [`scale_layer`](#scale-layer) | Scale a single layer to new dimensions. | 5 |
| [`rotate_image`](#rotate-image) | Rotate the entire image by 90, 180, or 270 degrees. | 1 |
| [`rotate_layer`](#rotate-layer) | Rotate a layer by an arbitrary angle. | 4 |
| [`perspective_layer`](#perspective-layer) | Perspective-transform a layer by remapping its four bounding-box corners. | 12 |
| [`shear_layer`](#shear-layer) | Shear a layer horizontally or vertically by a pixel magnitude. | 6 |
| [`flip_image`](#flip-image) | Flip the entire image. | 1 |
| [`flip_layer`](#flip-layer) | Flip a single layer. | 3 |
| [`crop_to_selection`](#crop-to-selection) | Crop the image to the current selection bounds. | 0 |
| [`smart_crop_or_resize`](#smart-crop-or-resize) | Safely crop, pad, or resize with explicit anchors and dry-run support. | 6 |
| [`crop_image`](#crop-image) | Crop the image to a specific rectangle. | 4 |
| [`autocrop_image`](#autocrop-image) | Automatically crop the image to remove border whitespace/transparency. | 0 |
| [`resize_canvas`](#resize-canvas) | Resize the image canvas without scaling content. | 4 |
| [`offset_layer`](#offset-layer) | Move a layer by an offset (reposition within the canvas). | 4 |

## `align_and_distribute_layers` {#align-and-distribute-layers}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:235`

```python
async def align_and_distribute_layers(layers: list[dict[str, object]], align: str | None = None, distribute: str | None = None, reference: str = 'canvas', dry_run: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layers` | Layer references such as layer_name or layer_index mappings. |
| `align` | Optional alignment mode such as left, right, center_x, top, bottom, or center_y. |
| `distribute` | Optional distribution mode, horizontal or vertical. |
| `reference` | Alignment reference. Currently canvas. |
| `dry_run` | When true, report planned offsets without mutating layers. |

## Returns

Operation result with layer references, selected operations, and dry-run metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Align or distribute layers relative to the canvas with verification bounds.

Args:
    layers: Layer references such as layer_name or layer_index mappings.
    align: Optional alignment mode such as left, right, center_x, top, bottom, or center_y.
    distribute: Optional distribution mode, horizontal or vertical.
    reference: Alignment reference. Currently canvas.
    dry_run: When true, report planned offsets without mutating layers.

Returns:
    Operation result with layer references, selected operations, and dry-run metadata.

## `scale_image` {#scale-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:296`

```python
async def scale_image(new_width: int, new_height: int, interpolation: str = 'cubic') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `new_width` | Target width in pixels (1-32768) |
| `new_height` | Target height in pixels (1-32768) |
| `interpolation` | Quality — "none", "linear", "cubic" (recommended), "nohalo", "lohalo" |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Scale the entire image (all layers) to new dimensions.

Notes:
    Use this tool when resizing the final image for output, or changing
    overall canvas dimensions while scaling content.

Args:
    new_width: Target width in pixels (1-32768)
    new_height: Target height in pixels (1-32768)
    interpolation: Quality — "none", "linear", "cubic" (recommended),
                  "nohalo", "lohalo"

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `scale_layer` {#scale-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:347`

```python
async def scale_layer(new_width: int, new_height: int, interpolation: str = 'cubic', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `new_width` | Target width in pixels |
| `new_height` | Target height in pixels |
| `interpolation` | "none", "linear", "cubic", "nohalo", "lohalo" |
| `layer_name` | Target layer by name. Uses active layer if neither specified. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Scale a single layer to new dimensions.

Notes:
    This changes the layer's pixel content, not the canvas.
    The layer may become larger or smaller than the image canvas.

Args:
    new_width: Target width in pixels
    new_height: Target height in pixels
    interpolation: "none", "linear", "cubic", "nohalo", "lohalo"
    layer_name: Target layer by name. Uses active layer if neither specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `rotate_image` {#rotate-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:399`

```python
async def rotate_image(angle: int) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `angle` | Rotation angle — must be 90, 180, or 270. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Rotate the entire image by 90, 180, or 270 degrees.

Args:
    angle: Rotation angle — must be 90, 180, or 270.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `rotate_layer` {#rotate-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:434`

```python
async def rotate_layer(angle_degrees: float, auto_resize: bool = True, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `angle_degrees` | Rotation angle in degrees (positive = counter-clockwise) |
| `auto_resize` | If True, resize layer to fit rotated content |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Rotate a layer by an arbitrary angle.

Args:
    angle_degrees: Rotation angle in degrees (positive = counter-clockwise)
    auto_resize: If True, resize layer to fit rotated content
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `perspective_layer` {#perspective-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:479`

```python
async def perspective_layer(x0: float, y0: float, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, interpolation: str = 'cubic', resize: str = 'adjust', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x0, y0` | New upper-left corner. |
| `y0` | _Undocumented._ |
| `x1, y1` | New upper-right corner. |
| `y1` | _Undocumented._ |
| `x2, y2` | New lower-left corner. |
| `y2` | _Undocumented._ |
| `x3, y3` | New lower-right corner. |
| `y3` | _Undocumented._ |
| `interpolation` | "none", "linear", "cubic", "nohalo", or "lohalo". |
| `resize` | Transform resize policy: "adjust", "clip", "crop", or "crop_with_aspect". |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with status, message, and applied corner coordinates.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Perspective-transform a layer by remapping its four bounding-box corners.

Args:
    x0, y0: New upper-left corner.
    x1, y1: New upper-right corner.
    x2, y2: New lower-left corner.
    x3, y3: New lower-right corner.
    interpolation: "none", "linear", "cubic", "nohalo", or "lohalo".
    resize: Transform resize policy: "adjust", "clip", "crop", or "crop_with_aspect".
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and applied corner coordinates.

## `shear_layer` {#shear-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:539`

```python
async def shear_layer(direction: str = 'horizontal', magnitude: float = 0.0, interpolation: str = 'cubic', resize: str = 'adjust', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `direction` | "horizontal"/"h" or "vertical"/"v". |
| `magnitude` | Shear magnitude in pixels; may be negative. |
| `interpolation` | "none", "linear", "cubic", "nohalo", or "lohalo". |
| `resize` | Transform resize policy: "adjust", "clip", "crop", or "crop_with_aspect". |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with status, message, and applied shear settings.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Shear a layer horizontally or vertically by a pixel magnitude.

Args:
    direction: "horizontal"/"h" or "vertical"/"v".
    magnitude: Shear magnitude in pixels; may be negative.
    interpolation: "none", "linear", "cubic", "nohalo", or "lohalo".
    resize: Transform resize policy: "adjust", "clip", "crop", or "crop_with_aspect".
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and applied shear settings.

## `flip_image` {#flip-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:597`

```python
async def flip_image(direction: str = 'horizontal') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `direction` | "horizontal" (mirror left/right) or "vertical" (mirror top/bottom) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Flip the entire image.

Args:
    direction: "horizontal" (mirror left/right) or "vertical" (mirror top/bottom)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `flip_layer` {#flip-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:633`

```python
async def flip_layer(direction: str = 'horizontal', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `direction` | "horizontal" or "vertical" |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Flip a single layer.

Args:
    direction: "horizontal" or "vertical"
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `crop_to_selection` {#crop-to-selection}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:678`

```python
async def crop_to_selection() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Crop the image to the current selection bounds.

Notes:
    Use this tool after making a selection around the area you want to keep.
    The image canvas will be resized to fit the selection.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `smart_crop_or_resize` {#smart-crop-or-resize}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:703`

```python
async def smart_crop_or_resize(mode: str, target_size: dict[str, int], anchor: str = 'center', preserve_layers: bool = True, background: str | None = None, dry_run: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `mode` | ``crop``, ``pad``, or ``resize``. |
| `target_size` | Mapping with integer ``width`` and ``height``. |
| `anchor` | center, top_left, top_right, bottom_left, or bottom_right. |
| `preserve_layers` | Keep layer structure where the selected operation supports it. |
| `background` | Optional background color used when padding. |
| `dry_run` | Report planned changes and clipping warnings without mutation. |

## Returns

Operation result with old/new dimensions, offset, would_clip, and warnings. Contract: Dry-run mode never mutates GIMP. Destructive crop/pad operations report clipping risk in the result for verification.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Safely crop, pad, or resize with explicit anchors and dry-run support.

Args:
    mode: ``crop``, ``pad``, or ``resize``.
    target_size: Mapping with integer ``width`` and ``height``.
    anchor: center, top_left, top_right, bottom_left, or bottom_right.
    preserve_layers: Keep layer structure where the selected operation supports it.
    background: Optional background color used when padding.
    dry_run: Report planned changes and clipping warnings without mutation.

Returns:
    Operation result with old/new dimensions, offset, would_clip, and warnings.

Contract:
    Dry-run mode never mutates GIMP. Destructive crop/pad operations report
    clipping risk in the result for verification.

## `crop_image` {#crop-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:782`

```python
async def crop_image(x: int, y: int, width: int, height: int) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x` | Left edge X coordinate |
| `y` | Top edge Y coordinate |
| `width` | Crop width in pixels |
| `height` | Crop height in pixels |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Crop the image to a specific rectangle.

Args:
    x: Left edge X coordinate
    y: Top edge Y coordinate
    width: Crop width in pixels
    height: Crop height in pixels

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `autocrop_image` {#autocrop-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:819`

```python
async def autocrop_image() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Automatically crop the image to remove border whitespace/transparency.

Notes:
    Use this tool after drawing, to trim unused canvas around the content.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `resize_canvas` {#resize-canvas}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:847`

```python
async def resize_canvas(new_width: int, new_height: int, offset_x: int = 0, offset_y: int = 0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `new_width` | New canvas width |
| `new_height` | New canvas height |
| `offset_x` | Horizontal offset for existing content (can be negative) |
| `offset_y` | Vertical offset for existing content (can be negative) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Resize the image canvas without scaling content.

Content stays the same size; canvas grows or shrinks around it.
Use offsets to position existing content within the new canvas.

Args:
    new_width: New canvas width
    new_height: New canvas height
    offset_x: Horizontal offset for existing content (can be negative)
    offset_y: Vertical offset for existing content (can be negative)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `offset_layer` {#offset-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:889`

```python
async def offset_layer(offset_x: int, offset_y: int, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `offset_x` | Horizontal offset in pixels (positive = right) |
| `offset_y` | Vertical offset in pixels (positive = down) |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Move a layer by an offset (reposition within the canvas).

Args:
    offset_x: Horizontal offset in pixels (positive = right)
    offset_y: Vertical offset in pixels (positive = down)
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
