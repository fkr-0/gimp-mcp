# Color Adjustments

Source module: `src/gimp_mcp_pro/tools/color_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`adjust_brightness_contrast`](#adjust-brightness-contrast) | Adjust brightness and contrast of a layer. | 4 |
| [`adjust_hue_saturation`](#adjust-hue-saturation) | Adjust hue, saturation, and lightness of a layer. | 5 |
| [`adjust_levels`](#adjust-levels) | Adjust levels for a layer. | 8 |
| [`adjust_curves`](#adjust-curves) | Adjust curves for a layer. | 4 |
| [`desaturate`](#desaturate) | Convert a layer to grayscale while keeping it in RGB mode. | 3 |
| [`invert_colors`](#invert-colors) | Invert all colors in a layer (negative effect). | 2 |
| [`apply_threshold`](#apply-threshold) | Apply threshold — convert to pure black and white. | 4 |
| [`posterize`](#posterize) | Reduce the number of color levels (posterization effect). | 3 |
| [`color_to_alpha`](#color-to-alpha) | Make a specific color transparent (color to alpha). | 3 |
| [`auto_white_balance`](#auto-white-balance) | Automatically adjust white balance (stretch colors). | 2 |
| [`get_colors`](#get-colors) | Get the current foreground and background colors. | 0 |
| [`swap_colors`](#swap-colors) | Swap foreground and background colors. | 0 |
| [`sample_color`](#sample-color) | Pick/sample a color from a pixel in the image. | 3 |

## `adjust_brightness_contrast` {#adjust-brightness-contrast}

Source: `src/gimp_mcp_pro/tools/color_tools.py:52`

```python
async def adjust_brightness_contrast(brightness: int = 0, contrast: int = 0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `brightness`
- `contrast`
- `layer_name`
- `layer_index`

**Docstring**

Adjust brightness and contrast of a layer.

Args:
    brightness: Brightness adjustment (-127 to 127, 0 = no change)
    contrast: Contrast adjustment (-127 to 127, 0 = no change)
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `adjust_hue_saturation` {#adjust-hue-saturation}

Source: `src/gimp_mcp_pro/tools/color_tools.py:89`

```python
async def adjust_hue_saturation(hue: float = 0.0, saturation: float = 0.0, lightness: float = 0.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `hue`
- `saturation`
- `lightness`
- `layer_name`
- `layer_index`

**Docstring**

Adjust hue, saturation, and lightness of a layer.

Args:
    hue: Hue rotation in degrees (-180 to 180, 0 = no change)
    saturation: Saturation adjustment (-100 to 100, 0 = no change)
    lightness: Lightness adjustment (-100 to 100, 0 = no change)
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `adjust_levels` {#adjust-levels}

Source: `src/gimp_mcp_pro/tools/color_tools.py:130`

```python
async def adjust_levels(input_low: int = 0, input_high: int = 255, gamma: float = 1.0, output_low: int = 0, output_high: int = 255, channel: str = 'value', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `input_low`
- `input_high`
- `gamma`
- `output_low`
- `output_high`
- `channel`
- `layer_name`
- `layer_index`

**Docstring**

Adjust levels for a layer.

Notes:
    Use this tool when fine-tuning tonal range, fixing underexposed/overexposed
    images, adjusting individual color channels.

Args:
    input_low: Input black point (0-255)
    input_high: Input white point (0-255)
    gamma: Midtone gamma (0.1-10.0, 1.0 = no change)
    output_low: Output black point (0-255)
    output_high: Output white point (0-255)
    channel: "value" (all), "red", "green", "blue", "alpha"
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `adjust_curves` {#adjust-curves}

Source: `src/gimp_mcp_pro/tools/color_tools.py:193`

```python
async def adjust_curves(control_points: list[float], channel: str = 'value', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `control_points`
- `channel`
- `layer_name`
- `layer_index`

**Docstring**

Adjust curves for a layer.

Notes:
    Use this tool when fine-grained tonal control, creating custom contrast curves,
    cross-processing effects.

Args:
    control_points: Flat list of input/output pairs [in1,out1, in2,out2, ...].
                   Values are 0.0-1.0 (0=black, 1=white).
                   Example: [0,0, 0.25,0.2, 0.5,0.6, 0.75,0.85, 1,1] for S-curve.
    channel: "value", "red", "green", "blue", "alpha"
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `desaturate` {#desaturate}

Source: `src/gimp_mcp_pro/tools/color_tools.py:247`

```python
async def desaturate(method: str = 'luminosity', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `method`
- `layer_name`
- `layer_index`

**Docstring**

Convert a layer to grayscale while keeping it in RGB mode.

Args:
    method: Desaturation method —
            "luminosity" (perceptual, recommended),
            "average" (equal weight),
            "lightness" (HSL lightness),
            "luminance" (linear luminance)
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `invert_colors` {#invert-colors}

Source: `src/gimp_mcp_pro/tools/color_tools.py:291`

```python
async def invert_colors(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `layer_name`
- `layer_index`

**Docstring**

Invert all colors in a layer (negative effect).

Each pixel's color is replaced with its complement.

Args:
    layer_name: Target layer by name. Uses the active layer when omitted.
    layer_index: Target layer by index. Uses the active layer when omitted.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_threshold` {#apply-threshold}

Source: `src/gimp_mcp_pro/tools/color_tools.py:319`

```python
async def apply_threshold(low: int = 128, high: int = 255, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `low`
- `high`
- `layer_name`
- `layer_index`

**Docstring**

Apply threshold — convert to pure black and white.

Pixels darker than `low` become black, lighter than `high` become white.

Args:
    low: Lower threshold (0-255, default 128)
    high: Upper threshold (0-255, default 255)
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `posterize` {#posterize}

Source: `src/gimp_mcp_pro/tools/color_tools.py:354`

```python
async def posterize(levels: int = 4, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `levels`
- `layer_name`
- `layer_index`

**Docstring**

Reduce the number of color levels (posterization effect).

Args:
    levels: Number of color levels per channel (2-256, lower = more dramatic)
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `color_to_alpha` {#color-to-alpha}

Source: `src/gimp_mcp_pro/tools/color_tools.py:386`

```python
async def color_to_alpha(color: str = 'white', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `color`
- `layer_name`
- `layer_index`

**Docstring**

Make a specific color transparent (color to alpha).

Notes:
    Use this tool when removing backgrounds, making white/black transparent
    for compositing, creating cutouts.

Args:
    color: Color to make transparent — name, hex, or rgb.
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `auto_white_balance` {#auto-white-balance}

Source: `src/gimp_mcp_pro/tools/color_tools.py:429`

```python
async def auto_white_balance(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `layer_name`
- `layer_index`

**Docstring**

Automatically adjust white balance (stretch colors).

Performs automatic levels adjustment to normalize color distribution.

Args:
    layer_name: Target layer by name. Uses the active layer when omitted.
    layer_index: Target layer by index. Uses the active layer when omitted.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `get_colors` {#get-colors}

Source: `src/gimp_mcp_pro/tools/color_tools.py:458`

```python
async def get_colors() -> ToolResult
```

**Docstring**

Get the current foreground and background colors.

Notes:
    Use this tool before drawing to verify colors are set correctly,
    especially since the user can change them in GIMP's UI at any time.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `swap_colors` {#swap-colors}

Source: `src/gimp_mcp_pro/tools/color_tools.py:505`

```python
async def swap_colors() -> ToolResult
```

**Docstring**

Swap foreground and background colors.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `sample_color` {#sample-color}

Source: `src/gimp_mcp_pro/tools/color_tools.py:525`

```python
async def sample_color(x: int, y: int, sample_merged: bool = False) -> ToolResult
```

**Parameters**

- `x`
- `y`
- `sample_merged`

**Docstring**

Pick/sample a color from a pixel in the image.

Args:
    x: X coordinate to sample
    y: Y coordinate to sample
    sample_merged: If True, sample from all visible layers merged.
                  If False, sample from active layer only.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
