# Color Adjustments

Source module: `src/gimp_mcp_pro/tools/color_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`adjust_brightness_contrast`](#adjust-brightness-contrast) | Adjust brightness and contrast of a layer. | 4 |
| [`adjust_hue_saturation`](#adjust-hue-saturation) | Adjust hue, saturation, and lightness of a layer. | 5 |
| [`adjust_color_balance`](#adjust-color-balance) | Adjust shadows, midtones, or highlights color balance for a layer. | 7 |
| [`adjust_levels`](#adjust-levels) | Adjust levels for a layer. | 8 |
| [`adjust_curves`](#adjust-curves) | Adjust curves for a layer. | 4 |
| [`desaturate`](#desaturate) | Convert a layer to grayscale while keeping it in RGB mode. | 3 |
| [`invert_colors`](#invert-colors) | Invert all colors in a layer (negative effect). | 2 |
| [`apply_threshold`](#apply-threshold) | Apply threshold — convert to pure black and white. | 4 |
| [`posterize`](#posterize) | Reduce the number of color levels (posterization effect). | 3 |
| [`color_to_alpha`](#color-to-alpha) | Make a specific color transparent (color to alpha). | 3 |
| [`replace_color`](#replace-color) | Replace pixels matching a source color with a replacement color. | 7 |
| [`auto_white_balance`](#auto-white-balance) | Automatically adjust white balance (stretch colors). | 2 |
| [`brush_inventory`](#brush-inventory) | List paint resources with current-context markers. | 4 |
| [`set_paint_resource`](#set-paint-resource) | Set one active paint resource by validated name. | 2 |
| [`set_paint_context`](#set-paint-context) | Set multiple paint context fields with validation and read-back. | 8 |
| [`resource_catalog`](#resource-catalog) | List bounded searchable resources with optional capability notes. | 4 |
| [`list_gimp_resources`](#list-gimp-resources) | List available GIMP brushes, patterns, fonts, and gradients. | 2 |
| [`get_colors`](#get-colors) | Get the current foreground and background colors. | 0 |
| [`swap_colors`](#swap-colors) | Swap foreground and background colors. | 0 |
| [`analyze_color_palette`](#analyze-color-palette) | Extract a deterministic approximate color palette for a layer or region. | 5 |
| [`dominant_colors`](#dominant-colors) | Return dominant colors for a layer or region. | 5 |
| [`analyze_color_histogram`](#analyze-color-histogram) | Analyze channel histogram summary statistics for a layer. | 5 |
| [`sample_pixels`](#sample-pixels) | Sample colors at multiple points or over a rectangular grid. | 7 |
| [`sample_color`](#sample-color) | Pick/sample a color from a pixel in the image. | 3 |
| [`palette_create_or_update`](#palette-create-or-update) | Create, inspect, or update a palette from provided colors. | 4 |

## `adjust_brightness_contrast` {#adjust-brightness-contrast}

Source: `src/gimp_mcp_pro/tools/color_tools.py:34`

```python
async def adjust_brightness_contrast(brightness: int = 0, contrast: int = 0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `brightness` | Brightness adjustment (-127 to 127, 0 = no change) |
| `contrast` | Contrast adjustment (-127 to 127, 0 = no change) |
| `layer_name` | Target layer. Uses active layer if not specified. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Adjust brightness and contrast of a layer.

Args:
    brightness: Brightness adjustment (-127 to 127, 0 = no change)
    contrast: Contrast adjustment (-127 to 127, 0 = no change)
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `adjust_hue_saturation` {#adjust-hue-saturation}

Source: `src/gimp_mcp_pro/tools/color_tools.py:72`

```python
async def adjust_hue_saturation(hue: float = 0.0, saturation: float = 0.0, lightness: float = 0.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `hue` | Hue rotation in degrees (-180 to 180, 0 = no change) |
| `saturation` | Saturation adjustment (-100 to 100, 0 = no change) |
| `lightness` | Lightness adjustment (-100 to 100, 0 = no change) |
| `layer_name` | Target layer. Uses active layer if not specified. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Adjust hue, saturation, and lightness of a layer.

Args:
    hue: Hue rotation in degrees (-180 to 180, 0 = no change)
    saturation: Saturation adjustment (-100 to 100, 0 = no change)
    lightness: Lightness adjustment (-100 to 100, 0 = no change)
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `adjust_color_balance` {#adjust-color-balance}

Source: `src/gimp_mcp_pro/tools/color_tools.py:114`

```python
async def adjust_color_balance(range: str = 'midtones', cyan_red: float = 0.0, magenta_green: float = 0.0, yellow_blue: float = 0.0, preserve_luminosity: bool = True, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `range` | Tonal range to adjust: "shadows", "midtones", or "highlights". |
| `cyan_red` | Cyan-to-red shift (-100 to 100, 0 = no change). |
| `magenta_green` | Magenta-to-green shift (-100 to 100, 0 = no change). |
| `yellow_blue` | Yellow-to-blue shift (-100 to 100, 0 = no change). |
| `preserve_luminosity` | Keep luminance stable while shifting colors. |
| `layer_name` | Target layer. Uses active layer if not specified. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Adjust shadows, midtones, or highlights color balance for a layer.

Args:
    range: Tonal range to adjust: "shadows", "midtones", or "highlights".
    cyan_red: Cyan-to-red shift (-100 to 100, 0 = no change).
    magenta_green: Magenta-to-green shift (-100 to 100, 0 = no change).
    yellow_blue: Yellow-to-blue shift (-100 to 100, 0 = no change).
    preserve_luminosity: Keep luminance stable while shifting colors.
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `adjust_levels` {#adjust-levels}

Source: `src/gimp_mcp_pro/tools/color_tools.py:184`

```python
async def adjust_levels(input_low: int = 0, input_high: int = 255, gamma: float = 1.0, output_low: int = 0, output_high: int = 255, channel: str = 'value', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `input_low` | Input black point (0-255) |
| `input_high` | Input white point (0-255) |
| `gamma` | Midtone gamma (0.1-10.0, 1.0 = no change) |
| `output_low` | Output black point (0-255) |
| `output_high` | Output white point (0-255) |
| `channel` | "value" (all), "red", "green", "blue", "alpha" |
| `layer_name` | Target layer. Uses active layer if not specified. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/color_tools.py:248`

```python
async def adjust_curves(control_points: list[float], channel: str = 'value', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `control_points` | Flat list of input/output pairs [in1,out1, in2,out2, ...]. Values are 0.0-1.0 (0=black, 1=white). |
| `channel` | "value", "red", "green", "blue", "alpha" |
| `layer_name` | Target layer. Uses active layer if not specified. |
| `layer_index` | Target layer by index. |
| `Example` | [0,0, 0.25,0.2, 0.5,0.6, 0.75,0.85, 1,1] for S-curve. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/color_tools.py:301`

```python
async def desaturate(method: str = 'luminosity', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `method` | Desaturation method — "luminosity" (perceptual, recommended), "average" (equal weight), "lightness" (HSL lightness), "luminance" (linear luminance) |
| `layer_name` | Target layer. Uses active layer if not specified. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/color_tools.py:344`

```python
async def invert_colors(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Target layer by name. Uses the active layer when omitted. |
| `layer_index` | Target layer by index. Uses the active layer when omitted. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Invert all colors in a layer (negative effect).

Each pixel's color is replaced with its complement.

Args:
    layer_name: Target layer by name. Uses the active layer when omitted.
    layer_index: Target layer by index. Uses the active layer when omitted.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_threshold` {#apply-threshold}

Source: `src/gimp_mcp_pro/tools/color_tools.py:371`

```python
async def apply_threshold(low: int = 128, high: int = 255, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `low` | Lower threshold (0-255, default 128) |
| `high` | Upper threshold (0-255, default 255) |
| `layer_name` | Target layer. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/color_tools.py:407`

```python
async def posterize(levels: int = 4, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `levels` | Number of color levels per channel (2-256, lower = more dramatic) |
| `layer_name` | Target layer. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Reduce the number of color levels (posterization effect).

Args:
    levels: Number of color levels per channel (2-256, lower = more dramatic)
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `color_to_alpha` {#color-to-alpha}

Source: `src/gimp_mcp_pro/tools/color_tools.py:438`

```python
async def color_to_alpha(color: str = 'white', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `color` | Color to make transparent — name, hex, or rgb. |
| `layer_name` | Target layer. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

## `replace_color` {#replace-color}

Source: `src/gimp_mcp_pro/tools/color_tools.py:504`

```python
async def replace_color(source_color: str, replacement_color: str, threshold: float = 15.0, sample_merged: bool = False, layer_name: str | None = None, layer_index: int | None = None, preserve_selection: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `source_color` | Color to replace, for example "#ffffff" or "white". |
| `replacement_color` | Color to fill into the selected source-color pixels. |
| `threshold` | Color similarity threshold 0-255. |
| `sample_merged` | If True, use GIMP's sample-merged context while selecting. |
| `layer_name` | Target layer by name. Uses active layer if omitted. |
| `layer_index` | Target layer by index. Uses active layer if omitted. |
| `preserve_selection` | Restore the previous selection after replacement. |

## Returns

Operation result dictionary with replacement metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Replace pixels matching a source color with a replacement color.

Args:
    source_color: Color to replace, for example "#ffffff" or "white".
    replacement_color: Color to fill into the selected source-color pixels.
    threshold: Color similarity threshold 0-255.
    sample_merged: If True, use GIMP's sample-merged context while selecting.
    layer_name: Target layer by name. Uses active layer if omitted.
    layer_index: Target layer by index. Uses active layer if omitted.
    preserve_selection: Restore the previous selection after replacement.

Returns:
    Operation result dictionary with replacement metadata.

## `auto_white_balance` {#auto-white-balance}

Source: `src/gimp_mcp_pro/tools/color_tools.py:583`

```python
async def auto_white_balance(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Target layer by name. Uses the active layer when omitted. |
| `layer_index` | Target layer by index. Uses the active layer when omitted. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Automatically adjust white balance (stretch colors).

Performs automatic levels adjustment to normalize color distribution.

Args:
    layer_name: Target layer by name. Uses the active layer when omitted.
    layer_index: Target layer by index. Uses the active layer when omitted.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `brush_inventory` {#brush-inventory}

Source: `src/gimp_mcp_pro/tools/color_tools.py:611`

```python
async def brush_inventory(asset_types: list[str] | None = None, filter: str | None = None, limit: int = 100, include_current: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `asset_types` | Resource types to list. Supported: brushes, patterns, gradients, fonts, palettes. |
| `filter` | Optional case-insensitive substring filter. |
| `limit` | Maximum entries per requested resource type. |
| `include_current` | Mark resources currently active in GIMP context. |

## Returns

Operation result with flat ``assets`` list and current resource map.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List paint resources with current-context markers.

Args:
    asset_types: Resource types to list. Supported: brushes, patterns, gradients, fonts, palettes.
    filter: Optional case-insensitive substring filter.
    limit: Maximum entries per requested resource type.
    include_current: Mark resources currently active in GIMP context.

Returns:
    Operation result with flat ``assets`` list and current resource map.

## `set_paint_resource` {#set-paint-resource}

Source: `src/gimp_mcp_pro/tools/color_tools.py:659`

```python
async def set_paint_resource(resource_type: str, name: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `resource_type` | One of brush, pattern, gradient, font, or palette. |
| `name` | Resource name to validate and activate. |

## Returns

Operation result with previous_resource and active_resource read-back.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Set one active paint resource by validated name.

Args:
    resource_type: One of brush, pattern, gradient, font, or palette.
    name: Resource name to validate and activate.

Returns:
    Operation result with previous_resource and active_resource read-back.

## `set_paint_context` {#set-paint-context}

Source: `src/gimp_mcp_pro/tools/color_tools.py:692`

```python
async def set_paint_context(brush: str | None = None, size: float | None = None, opacity: float | None = None, dynamics: str | None = None, pattern: str | None = None, gradient: str | None = None, foreground: str | None = None, background: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `brush` | Optional brush name. |
| `size` | Optional brush size. |
| `opacity` | Optional context opacity percent, 0..100. |
| `dynamics` | Optional dynamics name. Applied with read-back warning because GIMP does not expose list validation. |
| `pattern` | Optional pattern name. |
| `gradient` | Optional gradient name. |
| `foreground` | Optional foreground color. |
| `background` | Optional background color. |

## Returns

Operation result with previous_context, new_context, and warnings.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Set multiple paint context fields with validation and read-back.

Args:
    brush: Optional brush name.
    size: Optional brush size.
    opacity: Optional context opacity percent, 0..100.
    dynamics: Optional dynamics name. Applied with read-back warning because GIMP does not expose list validation.
    pattern: Optional pattern name.
    gradient: Optional gradient name.
    foreground: Optional foreground color.
    background: Optional background color.

Returns:
    Operation result with previous_context, new_context, and warnings.

## `resource_catalog` {#resource-catalog}

Source: `src/gimp_mcp_pro/tools/color_tools.py:753`

```python
async def resource_catalog(resource_type: str, query: str | None = None, limit: int = 50, include_optional: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `resource_type` | Resource kind such as brush, pattern, gradient, font, palette, dynamics, or tool preset. |
| `query` | Optional case-insensitive search string. |
| `limit` | Maximum number of resources to return. |
| `include_optional` | Include structured optional-capability notes for missing resource APIs. |

## Returns

Operation result with resource records, count, and optional-capability metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List bounded searchable resources with optional capability notes.

Args:
    resource_type: Resource kind such as brush, pattern, gradient, font, palette, dynamics, or tool preset.
    query: Optional case-insensitive search string.
    limit: Maximum number of resources to return.
    include_optional: Include structured optional-capability notes for missing resource APIs.

Returns:
    Operation result with resource records, count, and optional-capability metadata.

## `list_gimp_resources` {#list-gimp-resources}

Source: `src/gimp_mcp_pro/tools/color_tools.py:802`

```python
async def list_gimp_resources(resource_type: str = 'all', limit: int = 100) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `resource_type` | One of "all", "brushes", "patterns", "fonts", or "gradients". |
| `limit` | Maximum number of names returned per resource category. |

## Returns

Operation result dictionary with status, message, and resource name lists.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List available GIMP brushes, patterns, fonts, and gradients.

Args:
    resource_type: One of "all", "brushes", "patterns", "fonts", or "gradients".
    limit: Maximum number of names returned per resource category.

Returns:
    Operation result dictionary with status, message, and resource name lists.

## `get_colors` {#get-colors}

Source: `src/gimp_mcp_pro/tools/color_tools.py:883`

```python
async def get_colors() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Get the current foreground and background colors.

Notes:
    Use this tool before drawing to verify colors are set correctly,
    especially since the user can change them in GIMP's UI at any time.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `swap_colors` {#swap-colors}

Source: `src/gimp_mcp_pro/tools/color_tools.py:930`

```python
async def swap_colors() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Swap foreground and background colors.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `analyze_color_palette` {#analyze-color-palette}

Source: `src/gimp_mcp_pro/tools/color_tools.py:950`

```python
async def analyze_color_palette(max_colors: int = 8, ignore_transparent: bool = True, region: dict[str, Any] | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `max_colors` | Maximum number of dominant colors to return. |
| `ignore_transparent` | Skip fully transparent samples. |
| `region` | Optional ``x/y/width/height`` rectangle in layer coordinates. |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. |

## Returns

Operation result with palette entries, coverage, contrast notes, and stats. Contract: The generated sampler is deterministic for the same pixels and region.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Extract a deterministic approximate color palette for a layer or region.

Args:
    max_colors: Maximum number of dominant colors to return.
    ignore_transparent: Skip fully transparent samples.
    region: Optional ``x/y/width/height`` rectangle in layer coordinates.
    layer_name: Target layer by name.
    layer_index: Target layer by index.

Returns:
    Operation result with palette entries, coverage, contrast notes, and stats.

Contract:
    The generated sampler is deterministic for the same pixels and region.

## `dominant_colors` {#dominant-colors}

Source: `src/gimp_mcp_pro/tools/color_tools.py:1023`

```python
async def dominant_colors(max_colors: int = 8, ignore_transparent: bool = True, region: dict[str, Any] | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `max_colors` | Maximum number of dominant colors to return. |
| `ignore_transparent` | Skip fully transparent samples. |
| `region` | Optional x/y/width/height rectangle in layer coordinates. |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. |

## Returns

Operation result with dominant color entries and coverage metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Return dominant colors for a layer or region.

Args:
    max_colors: Maximum number of dominant colors to return.
    ignore_transparent: Skip fully transparent samples.
    region: Optional x/y/width/height rectangle in layer coordinates.
    layer_name: Target layer by name.
    layer_index: Target layer by index.

Returns:
    Operation result with dominant color entries and coverage metadata.

## `analyze_color_histogram` {#analyze-color-histogram}

Source: `src/gimp_mcp_pro/tools/color_tools.py:1065`

```python
async def analyze_color_histogram(channels: list[str] | None = None, start_range: float = 0.0, end_range: float = 1.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `channels` | Channels to inspect: value, red, green, blue, alpha. Defaults to all common channels. |
| `start_range` | Lower histogram range bound from 0.0 to 1.0. |
| `end_range` | Upper histogram range bound from 0.0 to 1.0. |
| `layer_name` | Target layer by name. Uses active layer if omitted. |
| `layer_index` | Target layer by index. Uses active layer if omitted. |

## Returns

Operation result with mean, standard deviation, median, pixel count, selected count, and percentile per channel.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Analyze channel histogram summary statistics for a layer.

Args:
    channels: Channels to inspect: value, red, green, blue, alpha. Defaults to all common channels.
    start_range: Lower histogram range bound from 0.0 to 1.0.
    end_range: Upper histogram range bound from 0.0 to 1.0.
    layer_name: Target layer by name. Uses active layer if omitted.
    layer_index: Target layer by index. Uses active layer if omitted.

Returns:
    Operation result with mean, standard deviation, median, pixel count, selected count, and percentile per channel.

## `sample_pixels` {#sample-pixels}

Source: `src/gimp_mcp_pro/tools/color_tools.py:1116`

```python
async def sample_pixels(points: list[dict[str, Any]] | None = None, grid: dict[str, Any] | None = None, sample_merged: bool = False, sample_average: bool = False, average_radius: float = 0.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `points` | Explicit point dictionaries with x and y coordinates. |
| `grid` | Optional grid spec with x, y, width, height, columns, and rows. |
| `sample_merged` | If True, sample the visible composite image. |
| `sample_average` | If True, average a radius around each point via GIMP pick_color. |
| `average_radius` | Radius used when sample_average is enabled. |
| `layer_name` | Target layer by name when not sampling merged output. |
| `layer_index` | Target layer by index when not sampling merged output. |

## Returns

Operation result with sampled RGBA/hex colors and request metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Sample colors at multiple points or over a rectangular grid.

Args:
    points: Explicit point dictionaries with x and y coordinates.
    grid: Optional grid spec with x, y, width, height, columns, and rows.
    sample_merged: If True, sample the visible composite image.
    sample_average: If True, average a radius around each point via GIMP pick_color.
    average_radius: Radius used when sample_average is enabled.
    layer_name: Target layer by name when not sampling merged output.
    layer_index: Target layer by index when not sampling merged output.

Returns:
    Operation result with sampled RGBA/hex colors and request metadata.

## `sample_color` {#sample-color}

Source: `src/gimp_mcp_pro/tools/color_tools.py:1183`

```python
async def sample_color(x: int, y: int, sample_merged: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `x` | X coordinate to sample |
| `y` | Y coordinate to sample |
| `sample_merged` | If True, sample from all visible layers merged. If False, sample from active layer only. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Pick/sample a color from a pixel in the image.

Args:
    x: X coordinate to sample
    y: Y coordinate to sample
    sample_merged: If True, sample from all visible layers merged.
                  If False, sample from active layer only.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `palette_create_or_update` {#palette-create-or-update}

Source: `src/gimp_mcp_pro/tools/color_tools.py:1211`

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
