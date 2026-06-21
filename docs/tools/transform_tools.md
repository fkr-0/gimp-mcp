# Transforms

Source module: `src/gimp_mcp_pro/tools/transform_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`scale_image`](#scale-image) | Scale the entire image (all layers) to new dimensions. | 3 |
| [`scale_layer`](#scale-layer) | Scale a single layer to new dimensions. | 5 |
| [`rotate_image`](#rotate-image) | Rotate the entire image by 90, 180, or 270 degrees. | 1 |
| [`rotate_layer`](#rotate-layer) | Rotate a layer by an arbitrary angle. | 4 |
| [`flip_image`](#flip-image) | Flip the entire image. | 1 |
| [`flip_layer`](#flip-layer) | Flip a single layer. | 3 |
| [`crop_to_selection`](#crop-to-selection) | Crop the image to the current selection bounds. | 0 |
| [`crop_image`](#crop-image) | Crop the image to a specific rectangle. | 4 |
| [`autocrop_image`](#autocrop-image) | Automatically crop the image to remove border whitespace/transparency. | 0 |
| [`resize_canvas`](#resize-canvas) | Resize the image canvas without scaling content. | 4 |
| [`offset_layer`](#offset-layer) | Move a layer by an offset (reposition within the canvas). | 4 |

## `scale_image` {#scale-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:57`

```python
async def scale_image(new_width: int, new_height: int, interpolation: str = 'cubic') -> dict[str, Any]
```

**Parameters**

- `new_width`
- `new_height`
- `interpolation`

**Docstring**

Scale the entire image (all layers) to new dimensions.

WHEN TO USE: Resizing the final image for output, or changing
overall canvas dimensions while scaling content.

Args:
    new_width: Target width in pixels (1-32768)
    new_height: Target height in pixels (1-32768)
    interpolation: Quality — "none", "linear", "cubic" (recommended),
                  "nohalo", "lohalo"

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `scale_layer` {#scale-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:107`

```python
async def scale_layer(new_width: int, new_height: int, interpolation: str = 'cubic', layer_name: str | None = None, layer_index: int | None = None) -> dict[str, Any]
```

**Parameters**

- `new_width`
- `new_height`
- `interpolation`
- `layer_name`
- `layer_index`

**Docstring**

Scale a single layer to new dimensions.

NOTE: This changes the layer's pixel content, not the canvas.
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

Source: `src/gimp_mcp_pro/tools/transform_tools.py:158`

```python
async def rotate_image(angle: int) -> dict[str, Any]
```

**Parameters**

- `angle`

**Docstring**

Rotate the entire image by 90, 180, or 270 degrees.

Args:
    angle: Rotation angle — must be 90, 180, or 270.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `rotate_layer` {#rotate-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:193`

```python
async def rotate_layer(angle_degrees: float, auto_resize: bool = True, layer_name: str | None = None, layer_index: int | None = None) -> dict[str, Any]
```

**Parameters**

- `angle_degrees`
- `auto_resize`
- `layer_name`
- `layer_index`

**Docstring**

Rotate a layer by an arbitrary angle.

Args:
    angle_degrees: Rotation angle in degrees (positive = counter-clockwise)
    auto_resize: If True, resize layer to fit rotated content
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `flip_image` {#flip-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:238`

```python
async def flip_image(direction: str = 'horizontal') -> dict[str, Any]
```

**Parameters**

- `direction`

**Docstring**

Flip the entire image.

Args:
    direction: "horizontal" (mirror left/right) or "vertical" (mirror top/bottom)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `flip_layer` {#flip-layer}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:274`

```python
async def flip_layer(direction: str = 'horizontal', layer_name: str | None = None, layer_index: int | None = None) -> dict[str, Any]
```

**Parameters**

- `direction`
- `layer_name`
- `layer_index`

**Docstring**

Flip a single layer.

Args:
    direction: "horizontal" or "vertical"
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `crop_to_selection` {#crop-to-selection}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:319`

```python
async def crop_to_selection() -> dict[str, Any]
```

**Docstring**

Crop the image to the current selection bounds.

WHEN TO USE: After making a selection around the area you want to keep.
The image canvas will be resized to fit the selection.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `crop_image` {#crop-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:343`

```python
async def crop_image(x: int, y: int, width: int, height: int) -> dict[str, Any]
```

**Parameters**

- `x`
- `y`
- `width`
- `height`

**Docstring**

Crop the image to a specific rectangle.

Args:
    x: Left edge X coordinate
    y: Top edge Y coordinate
    width: Crop width in pixels
    height: Crop height in pixels

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `autocrop_image` {#autocrop-image}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:380`

```python
async def autocrop_image() -> dict[str, Any]
```

**Docstring**

Automatically crop the image to remove border whitespace/transparency.

WHEN TO USE: After drawing, to trim unused canvas around the content.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `resize_canvas` {#resize-canvas}

Source: `src/gimp_mcp_pro/tools/transform_tools.py:407`

```python
async def resize_canvas(new_width: int, new_height: int, offset_x: int = 0, offset_y: int = 0) -> dict[str, Any]
```

**Parameters**

- `new_width`
- `new_height`
- `offset_x`
- `offset_y`

**Docstring**

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

Source: `src/gimp_mcp_pro/tools/transform_tools.py:449`

```python
async def offset_layer(offset_x: int, offset_y: int, layer_name: str | None = None, layer_index: int | None = None) -> dict[str, Any]
```

**Parameters**

- `offset_x`
- `offset_y`
- `layer_name`
- `layer_index`

**Docstring**

Move a layer by an offset (reposition within the canvas).

Args:
    offset_x: Horizontal offset in pixels (positive = right)
    offset_y: Vertical offset in pixels (positive = down)
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
