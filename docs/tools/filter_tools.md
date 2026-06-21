# Filters and Effects

Source module: `src/gimp_mcp_pro/tools/filter_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`apply_gaussian_blur`](#apply-gaussian-blur) | Apply Gaussian blur to a layer. | 4 |
| [`apply_unsharp_mask`](#apply-unsharp-mask) | Sharpen a layer using unsharp mask. | 5 |
| [`apply_pixelize`](#apply-pixelize) | Apply pixelization (mosaic) effect to a layer. | 4 |
| [`apply_edge_detect`](#apply-edge-detect) | Apply edge detection to a layer. | 4 |
| [`apply_emboss`](#apply-emboss) | Apply emboss effect to a layer. | 5 |
| [`apply_noise`](#apply-noise) | Add random noise to a layer. | 3 |
| [`apply_median`](#apply-median) | Apply median filter (denoise) to a layer. | 3 |
| [`apply_drop_shadow`](#apply-drop-shadow) | Apply a drop shadow effect to a layer. | 7 |

## `apply_gaussian_blur` {#apply-gaussian-blur}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:86`

```python
async def apply_gaussian_blur(radius_x: float = 5.0, radius_y: float | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `radius_x`
- `radius_y`
- `layer_name`
- `layer_index`

**Docstring**

Apply Gaussian blur to a layer.

Notes:
    Use this tool when softening images, creating depth-of-field effects,
    blurring backgrounds, smoothing noise.

Args:
    radius_x: Horizontal blur radius in pixels (0.0-500.0)
    radius_y: Vertical blur radius. Defaults to radius_x for uniform blur.
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_unsharp_mask` {#apply-unsharp-mask}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:129`

```python
async def apply_unsharp_mask(amount: float = 0.5, radius: float = 3.0, threshold: float = 0.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `amount`
- `radius`
- `threshold`
- `layer_name`
- `layer_index`

**Docstring**

Sharpen a layer using unsharp mask.

Notes:
    Use this tool when enhancing image detail, sharpening after resize,
    recovering slightly out-of-focus images.

Args:
    amount: Sharpening strength (0.0-5.0, typical 0.3-1.0)
    radius: Detail radius in pixels (0.1-120.0, typical 1.0-5.0)
    threshold: Minimum difference threshold (0.0-1.0, higher = less sharpening of subtle detail)
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_pixelize` {#apply-pixelize}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:172`

```python
async def apply_pixelize(block_width: int = 10, block_height: int | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `block_width`
- `block_height`
- `layer_name`
- `layer_index`

**Docstring**

Apply pixelization (mosaic) effect to a layer.

Notes:
    Use this tool when censoring faces/text, retro pixel art effect, privacy masking.

Args:
    block_width: Pixel block width (1-1024)
    block_height: Pixel block height. Defaults to block_width for square blocks.
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_edge_detect` {#apply-edge-detect}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:214`

```python
async def apply_edge_detect(method: str = 'sobel', amount: float = 1.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `method`
- `amount`
- `layer_name`
- `layer_index`

**Docstring**

Apply edge detection to a layer.

Notes:
    Use this tool when artistic outlines, finding contours, image analysis,
    creating line-art effects.

Args:
    method: Detection algorithm — "sobel", "prewitt", "laplace"
    amount: Edge detection strength (0.0-10.0)
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_emboss` {#apply-emboss}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:256`

```python
async def apply_emboss(azimuth: float = 315.0, elevation: float = 45.0, depth: int = 2, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `azimuth`
- `elevation`
- `depth`
- `layer_name`
- `layer_index`

**Docstring**

Apply emboss effect to a layer.

Creates a raised/carved appearance.

Args:
    azimuth: Light angle in degrees (0-360, default 315 = upper-left)
    elevation: Light elevation in degrees (0-180)
    depth: Emboss depth (1-100)
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_noise` {#apply-noise}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:296`

```python
async def apply_noise(amount: float = 0.2, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `amount`
- `layer_name`
- `layer_index`

**Docstring**

Add random noise to a layer.

Notes:
    Use this tool when adding film grain, texture, or breaking up smooth gradients.

Args:
    amount: Noise intensity (0.0-1.0)
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_median` {#apply-median}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:333`

```python
async def apply_median(radius: int = 3, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `radius`
- `layer_name`
- `layer_index`

**Docstring**

Apply median filter (denoise) to a layer.

Good for removing salt-and-pepper noise while preserving edges.

Args:
    radius: Filter radius (1-20)
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_drop_shadow` {#apply-drop-shadow}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:368`

```python
async def apply_drop_shadow(offset_x: float = 4.0, offset_y: float = 4.0, blur_radius: float = 8.0, color: str = 'black', opacity: float = 60.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `offset_x`
- `offset_y`
- `blur_radius`
- `color`
- `opacity`
- `layer_name`
- `layer_index`

**Docstring**

Apply a drop shadow effect to a layer.

Creates a shadow behind the layer content.

Args:
    offset_x: Shadow horizontal offset (positive = right)
    offset_y: Shadow vertical offset (positive = down)
    blur_radius: Shadow blur amount
    color: Shadow color (default "black")
    opacity: Shadow opacity 0-100
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
