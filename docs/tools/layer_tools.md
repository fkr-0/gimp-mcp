# Layer Operations

Source module: `src/gimp_mcp_pro/tools/layer_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`create_layer`](#create-layer) | Create a new layer in the active image. | 9 |
| [`list_layers`](#list-layers) | List all layers in the active image with their properties. | 0 |
| [`set_active_layer`](#set-active-layer) | Set which layer is active (the one drawing tools operate on). | 2 |
| [`delete_layer`](#delete-layer) | Delete a layer from the active image. | 2 |
| [`set_layer_opacity`](#set-layer-opacity) | Set a layer's opacity. | 3 |
| [`set_layer_visibility`](#set-layer-visibility) | Show or hide a layer. | 3 |
| [`set_layer_mode`](#set-layer-mode) | Set a layer's blend mode (normal, multiply, screen, overlay, etc.). | 3 |
| [`set_layer_blend_mode`](#set-layer-blend-mode) | Alias for set_layer_mode with discoverable blend-mode naming. | 3 |
| [`duplicate_layer`](#duplicate-layer) | Duplicate a layer. | 3 |
| [`merge_visible_layers`](#merge-visible-layers) | Merge all visible layers into one. | 0 |
| [`new_layer_from_visible`](#new-layer-from-visible) | Create a new layer from the current visible composite without merging originals. | 3 |
| [`merge_down`](#merge-down) | Merge a layer down into the layer below it. | 3 |
| [`copy_layer_alpha_to_mask`](#copy-layer-alpha-to-mask) | Copy a source layer's alpha silhouette into the target layer mask. | 5 |
| [`selection_to_layer_mask`](#selection-to-layer-mask) | Create or replace a layer mask from the current selection. | 3 |
| [`create_mask_from_color`](#create-mask-from-color) | Create a layer mask from an explicit color or sampled color selection. | 11 |
| [`add_layer_mask`](#add-layer-mask) | Add a layer mask to a layer. | 3 |
| [`get_layer_mask_info`](#get-layer-mask-info) | Get layer mask status for a layer. | 2 |
| [`set_layer_mask_state`](#set-layer-mask-state) | Set layer mask editing/display/apply flags. | 5 |
| [`remove_layer_mask`](#remove-layer-mask) | Remove a layer mask, optionally applying it first. | 3 |
| [`create_layer_group`](#create-layer-group) | Create a group layer in the active image. | 4 |
| [`move_layer_to_group`](#move-layer-to-group) | Move a layer or group under a target layer group. | 5 |
| [`list_channels`](#list-channels) | List custom channels in the active image. | 0 |
| [`save_selection_to_channel`](#save-selection-to-channel) | Save the current selection mask as a named custom channel. | 1 |
| [`channel_to_selection`](#channel-to-selection) | Convert a custom channel into the current selection. | 3 |
| [`create_visual_annotation_layer`](#create-visual-annotation-layer) | Create an MCP-tagged temporary visual annotation layer. | 3 |
| [`remove_visual_annotations`](#remove-visual-annotations) | Remove MCP-managed annotation layers only. | 2 |
| [`layer_version_stamp`](#layer-version-stamp) | Attach namespaced MCP provenance metadata to a layer. | 3 |
| [`add_alpha_channel`](#add-alpha-channel) | Add an alpha (transparency) channel to a layer. | 2 |
| [`edit_channels`](#edit-channels) | Create, inspect, duplicate, rename, or convert channels/selections. | 3 |
| [`manage_channels`](#manage-channels) | Manage saved channels through a consolidated action tool. | 4 |

## `create_layer` {#create-layer}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:113`

```python
async def create_layer(name: str = 'New Layer', opacity: float = 100.0, blend_mode: str = 'normal', fill: str = 'transparent', has_alpha: bool = True, position: int = 0, width: int | None = None, height: int | None = None, activate: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `name` | Layer name (e.g., "Background", "Eyes", "Shadow") |
| `opacity` | Layer opacity 0-100 (100 = fully opaque) |
| `blend_mode` | Blend mode — "normal", "multiply", "screen", "overlay", etc. |
| `fill` | Initial fill — "transparent", "white", "foreground", "background" |
| `has_alpha` | Whether layer has transparency (usually True) |
| `position` | Stack position (0 = top of stack) |
| `width` | Layer width (defaults to image width) |
| `height` | Layer height (defaults to image height) |
| `activate` | If True (default), make the new layer active so drawing/fill tools target it. |

## Returns

Operation result with layer info.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a new layer in the active image.

Notes:
    Use this tool before drawing new elements. Professional workflows use
    separate layers for background, main subject, details, etc.

Notes:
    Best practice: Create layers BEFORE drawing. Plan your layer structure:
    background -> body -> head -> details -> texture.

Args:
    name: Layer name (e.g., "Background", "Eyes", "Shadow")
    opacity: Layer opacity 0-100 (100 = fully opaque)
    blend_mode: Blend mode — "normal", "multiply", "screen", "overlay", etc.
    fill: Initial fill — "transparent", "white", "foreground", "background"
    has_alpha: Whether layer has transparency (usually True)
    position: Stack position (0 = top of stack)
    width: Layer width (defaults to image width)
    height: Layer height (defaults to image height)
    activate: If True (default), make the new layer active so drawing/fill tools target it.

Returns:
    Operation result with layer info.

## `list_layers` {#list-layers}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:216`

```python
async def list_layers() -> ToolResult
```

## Returns

Layer list with name, visibility, opacity, blend mode, dimensions.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List all layers in the active image with their properties.

Notes:
    Use this tool before drawing (to find the right layer), when debugging
    visual issues, or to understand image structure.

Returns:
    Layer list with name, visibility, opacity, blend mode, dimensions.

## `set_active_layer` {#set-active-layer}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:263`

```python
async def set_active_layer(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Layer name to activate (e.g., "Background") |
| `layer_index` | Layer index (0 = topmost). Alternative to name. |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Set which layer is active (the one drawing tools operate on).

Notes:
    Use this tool before any drawing or editing operation, switch to the
    correct layer. Drawing on the wrong layer is the most common mistake.

Args:
    layer_name: Layer name to activate (e.g., "Background")
    layer_index: Layer index (0 = topmost). Alternative to name.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `delete_layer` {#delete-layer}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:325`

```python
async def delete_layer(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Name of layer to delete. |
| `layer_index` | Index of layer to delete (0 = topmost). |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Delete a layer from the active image.

Args:
    layer_name: Name of layer to delete.
    layer_index: Index of layer to delete (0 = topmost).

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `set_layer_opacity` {#set-layer-opacity}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:361`

```python
async def set_layer_opacity(opacity: float, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `opacity` | Opacity 0-100 (0 = fully transparent, 100 = fully opaque) |
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

Set a layer's opacity.

Args:
    opacity: Opacity 0-100 (0 = fully transparent, 100 = fully opaque)
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `set_layer_visibility` {#set-layer-visibility}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:414`

```python
async def set_layer_visibility(visible: bool, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `visible` | True to show, False to hide. |
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

Show or hide a layer.

Args:
    visible: True to show, False to hide.
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `set_layer_mode` {#set-layer-mode}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:445`

```python
async def set_layer_mode(blend_mode: str, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `blend_mode` | Blend mode name — "normal", "dissolve", "multiply", "screen", "overlay", "soft_light", "hard_light", "color_dodge", "color_burn", "darken_only", "lighten_only", "difference", "exclusion", "hue", "saturation", "color", "luminosity", "addition", "subtract", "grain_extract", "grain_merge", "divide" |
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

Set a layer's blend mode (normal, multiply, screen, overlay, etc.).

Args:
    blend_mode: Blend mode name — "normal", "dissolve", "multiply",
        "screen", "overlay", "soft_light", "hard_light", "color_dodge",
        "color_burn", "darken_only", "lighten_only", "difference",
        "exclusion", "hue", "saturation", "color", "luminosity",
        "addition", "subtract", "grain_extract", "grain_merge", "divide"
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `set_layer_blend_mode` {#set-layer-blend-mode}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:489`

```python
async def set_layer_blend_mode(blend_mode: str, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `blend_mode` | Blend mode name such as "normal", "multiply", or "screen". |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with status, message, and blend-mode metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Alias for set_layer_mode with discoverable blend-mode naming.

Args:
    blend_mode: Blend mode name such as "normal", "multiply", or "screen".
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and blend-mode metadata.

## `duplicate_layer` {#duplicate-layer}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:529`

```python
async def duplicate_layer(layer_name: str | None = None, layer_index: int | None = None, new_name: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Source layer name. |
| `layer_index` | Source layer index. Uses active layer if neither specified. |
| `new_name` | Name for the duplicate. Defaults to "Copy of <original>". |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Duplicate a layer.

Args:
    layer_name: Source layer name.
    layer_index: Source layer index. Uses active layer if neither specified.
    new_name: Name for the duplicate. Defaults to "Copy of <original>".

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `merge_visible_layers` {#merge-visible-layers}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:592`

```python
async def merge_visible_layers() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Merge all visible layers into one.

Notes:
    Use this tool when consolidate visible work while preserving hidden layers.

Warnings:
    Destructive operation — consider using undo groups.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `new_layer_from_visible` {#new-layer-from-visible}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:638`

```python
async def new_layer_from_visible(name: str = 'Visible', position: int = 0, activate: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `name` | Name for the created visible-composite layer. |
| `position` | Stack position for the new layer. |
| `activate` | If True, make the created layer active. |

## Returns

Operation result dictionary with created layer metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a new layer from the current visible composite without merging originals.

Args:
    name: Name for the created visible-composite layer.
    position: Stack position for the new layer.
    activate: If True, make the created layer active.

Returns:
    Operation result dictionary with created layer metadata.

## `merge_down` {#merge-down}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:687`

```python
async def merge_down(layer_name: str | None = None, layer_index: int | None = None, merge_type: str = 'clip_to_image') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Layer to merge by name. |
| `layer_index` | Layer to merge by index. Uses active layer if neither specified. |
| `merge_type` | GIMP merge mode: expand_as_necessary, clip_to_image, or clip_to_bottom_layer. |

## Returns

Operation result dictionary with merged layer metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Merge a layer down into the layer below it.

Args:
    layer_name: Layer to merge by name.
    layer_index: Layer to merge by index. Uses active layer if neither specified.
    merge_type: GIMP merge mode: expand_as_necessary, clip_to_image, or clip_to_bottom_layer.

Returns:
    Operation result dictionary with merged layer metadata.

## `copy_layer_alpha_to_mask` {#copy-layer-alpha-to-mask}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:735`

```python
async def copy_layer_alpha_to_mask(source_layer_name: str | None = None, source_layer_index: int | None = None, target_layer_name: str | None = None, target_layer_index: int | None = None, replace_existing: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `source_layer_name` | Source layer by name. |
| `source_layer_index` | Source layer by index. |
| `target_layer_name` | Target layer by name. |
| `target_layer_index` | Target layer by index. |
| `replace_existing` | Replace an existing target mask when present. |

## Returns

Operation result dictionary with source-to-target mask metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Copy a source layer's alpha silhouette into the target layer mask.

Args:
    source_layer_name: Source layer by name.
    source_layer_index: Source layer by index.
    target_layer_name: Target layer by name.
    target_layer_index: Target layer by index.
    replace_existing: Replace an existing target mask when present.

Returns:
    Operation result dictionary with source-to-target mask metadata.

## `selection_to_layer_mask` {#selection-to-layer-mask}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:818`

```python
async def selection_to_layer_mask(layer_name: str | None = None, layer_index: int | None = None, replace_existing: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |
| `replace_existing` | Replace an existing target mask when present. |

## Returns

Operation result dictionary with layer mask metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create or replace a layer mask from the current selection.

Args:
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.
    replace_existing: Replace an existing target mask when present.

Returns:
    Operation result dictionary with layer mask metadata.

## `create_mask_from_color` {#create-mask-from-color}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:860`

```python
async def create_mask_from_color(color: str | None = None, x: float | None = None, y: float | None = None, threshold: float = 15.0, contiguous: bool = False, sample_merged: bool = False, source_layer_name: str | None = None, source_layer_index: int | None = None, target_layer_name: str | None = None, target_layer_index: int | None = None, replace_existing: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `color` | Explicit color to select, for example "#ffffff". |
| `x` | Optional sample X coordinate when color is omitted. |
| `y` | Optional sample Y coordinate when color is omitted. |
| `threshold` | Color similarity threshold 0-255. |
| `contiguous` | If True with x/y, use fuzzy connected-region selection. |
| `sample_merged` | If True, sample all visible layers merged. |
| `source_layer_name` | Source drawable layer by name. Uses active layer if omitted. |
| `source_layer_index` | Source drawable layer by index. Uses active layer if omitted. |
| `target_layer_name` | Target layer to receive the mask by name. Uses source/active layer if omitted. |
| `target_layer_index` | Target layer to receive the mask by index. Uses source/active layer if omitted. |
| `replace_existing` | Replace an existing target mask when present. |

## Returns

Operation result dictionary with color-mask metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a layer mask from an explicit color or sampled color selection.

Args:
    color: Explicit color to select, for example "#ffffff".
    x: Optional sample X coordinate when color is omitted.
    y: Optional sample Y coordinate when color is omitted.
    threshold: Color similarity threshold 0-255.
    contiguous: If True with x/y, use fuzzy connected-region selection.
    sample_merged: If True, sample all visible layers merged.
    source_layer_name: Source drawable layer by name. Uses active layer if omitted.
    source_layer_index: Source drawable layer by index. Uses active layer if omitted.
    target_layer_name: Target layer to receive the mask by name. Uses source/active layer if omitted.
    target_layer_index: Target layer to receive the mask by index. Uses source/active layer if omitted.
    replace_existing: Replace an existing target mask when present.

Returns:
    Operation result dictionary with color-mask metadata.

## `add_layer_mask` {#add-layer-mask}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:988`

```python
async def add_layer_mask(mask_type: str = 'white', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `mask_type` | "white", "black", "alpha", "alpha_transfer", "selection", or "copy". |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result with mask metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Add a layer mask to a layer.

Args:
    mask_type: "white", "black", "alpha", "alpha_transfer", "selection", or "copy".
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result with mask metadata.

## `get_layer_mask_info` {#get-layer-mask-info}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1033`

```python
async def get_layer_mask_info(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with layer mask status metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Get layer mask status for a layer.

Args:
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with layer mask status metadata.

## `set_layer_mask_state` {#set-layer-mask-state}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1076`

```python
async def set_layer_mask_state(edit_mask: bool | None = None, show_mask: bool | None = None, apply_mask: bool | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `edit_mask` | If True, painting/editing targets the mask. |
| `show_mask` | If True, display the mask itself. |
| `apply_mask` | If True, layer renders with the mask applied. |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with the updated mask state metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Set layer mask editing/display/apply flags.

Args:
    edit_mask: If True, painting/editing targets the mask.
    show_mask: If True, display the mask itself.
    apply_mask: If True, layer renders with the mask applied.
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with the updated mask state metadata.

## `remove_layer_mask` {#remove-layer-mask}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1121`

```python
async def remove_layer_mask(apply: bool = False, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `apply` | True applies the mask to the layer; False discards it. |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. Uses active layer if neither specified. |

## Returns

Operation result dictionary with removal/apply status metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Remove a layer mask, optionally applying it first.

Args:
    apply: True applies the mask to the layer; False discards it.
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with removal/apply status metadata.

## `create_layer_group` {#create-layer-group}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1153`

```python
async def create_layer_group(name: str = 'Group', position: int = 0, parent_group_name: str | None = None, parent_group_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `name` | Name for the new group layer. |
| `position` | Stack position inside the image or parent group. |
| `parent_group_name` | Optional parent group layer name. |
| `parent_group_index` | Optional parent group index when name is not supplied. |

## Returns

Operation result dictionary with created group metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a group layer in the active image.

Args:
    name: Name for the new group layer.
    position: Stack position inside the image or parent group.
    parent_group_name: Optional parent group layer name.
    parent_group_index: Optional parent group index when name is not supplied.

Returns:
    Operation result dictionary with created group metadata.

## `move_layer_to_group` {#move-layer-to-group}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1210`

```python
async def move_layer_to_group(layer_name: str | None = None, layer_index: int | None = None, group_name: str | None = None, group_index: int | None = None, position: int = 0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `layer_name` | Layer name to move. |
| `layer_index` | Layer index to move. Uses active layer if neither layer selector is supplied. |
| `group_name` | Destination group layer name. |
| `group_index` | Destination group index when name is not supplied. |
| `position` | Position inside the destination group. |

## Returns

Operation result dictionary with move metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Move a layer or group under a target layer group.

Args:
    layer_name: Layer name to move.
    layer_index: Layer index to move. Uses active layer if neither layer selector is supplied.
    group_name: Destination group layer name.
    group_index: Destination group index when name is not supplied.
    position: Position inside the destination group.

Returns:
    Operation result dictionary with move metadata.

## `list_channels` {#list-channels}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1262`

```python
async def list_channels() -> ToolResult
```

## Returns

Operation result dictionary with channel names, indexes, visibility, and total count.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List custom channels in the active image.

Returns:
    Operation result dictionary with channel names, indexes, visibility, and total count.

## `save_selection_to_channel` {#save-selection-to-channel}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1304`

```python
async def save_selection_to_channel(name: str = 'Selection') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `name` | Name for the created channel. |

## Returns

Operation result dictionary with created channel metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Save the current selection mask as a named custom channel.

Args:
    name: Name for the created channel.

Returns:
    Operation result dictionary with created channel metadata.

## `channel_to_selection` {#channel-to-selection}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1341`

```python
async def channel_to_selection(channel_name: str | None = None, channel_index: int | None = None, operation: str = 'replace') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `channel_name` | Channel name to select from. |
| `channel_index` | Channel index to select from. Uses the first channel if neither selector is supplied. |
| `operation` | Selection operation: "replace", "add", "subtract", or "intersect". |

## Returns

Operation result dictionary with channel-to-selection metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Convert a custom channel into the current selection.

Args:
    channel_name: Channel name to select from.
    channel_index: Channel index to select from. Uses the first channel if neither selector is supplied.
    operation: Selection operation: "replace", "add", "subtract", or "intersect".

Returns:
    Operation result dictionary with channel-to-selection metadata.

## `create_visual_annotation_layer` {#create-visual-annotation-layer}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1385`

```python
async def create_visual_annotation_layer(annotations: list[dict[str, object]], layer_name: str | None = None, temporary: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `annotations` | Typed annotation definitions such as boxes, arrows, or labels. |
| `layer_name` | Optional annotation layer name. |
| `temporary` | Mark the layer as a removable MCP annotation. |

## Returns

Operation result with annotation layer metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create an MCP-tagged temporary visual annotation layer.

Args:
    annotations: Typed annotation definitions such as boxes, arrows, or labels.
    layer_name: Optional annotation layer name.
    temporary: Mark the layer as a removable MCP annotation.

Returns:
    Operation result with annotation layer metadata.

## `remove_visual_annotations` {#remove-visual-annotations}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1463`

```python
async def remove_visual_annotations(annotation_layer_ids: list[int] | None = None, remove_all_mcp_annotations: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `annotation_layer_ids` | Explicit annotation layer IDs to remove. |
| `remove_all_mcp_annotations` | Remove all layers tagged as MCP annotations. |

## Returns

Operation result with removed layer IDs.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Remove MCP-managed annotation layers only.

Args:
    annotation_layer_ids: Explicit annotation layer IDs to remove.
    remove_all_mcp_annotations: Remove all layers tagged as MCP annotations.

Returns:
    Operation result with removed layer IDs.

## `layer_version_stamp` {#layer-version-stamp}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1519`

```python
async def layer_version_stamp(target: dict[str, object] | str, metadata: dict[str, object], merge: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `target` | Layer target reference, commonly {"layer_name": "..."}. |
| `metadata` | Metadata payload to attach. |
| `merge` | Merge with existing MCP metadata where possible. |

## Returns

Operation result with stamped metadata namespace.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Attach namespaced MCP provenance metadata to a layer.

Args:
    target: Layer target reference, commonly {"layer_name": "..."}.
    metadata: Metadata payload to attach.
    merge: Merge with existing MCP metadata where possible.

Returns:
    Operation result with stamped metadata namespace.

## `add_alpha_channel` {#add-alpha-channel}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1602`

```python
async def add_alpha_channel(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
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

Add an alpha (transparency) channel to a layer.

Notes:
    Use this tool before using transparent fills or edit_clear on a layer
    that was created without alpha (e.g., the default Background layer).

Args:
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `edit_channels` {#edit-channels}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1645`

```python
async def edit_channels(action: str, channel: dict[str, Any] | str | None = None, name: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | Channel operation. |
| `channel` | Optional channel reference. |
| `name` | Optional new or target name. |

## Returns

Operation result with channel metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create, inspect, duplicate, rename, or convert channels/selections.

Args:
    action: Channel operation.
    channel: Optional channel reference.
    name: Optional new or target name.

Returns:
    Operation result with channel metadata.

## `manage_channels` {#manage-channels}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:1681`

```python
async def manage_channels(action: str = 'list', channel_ref: dict[str, Any] | str | None = None, name: str | None = None, visible: bool | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | list/create/rename/show/hide/to_selection/selection_to_channel. |
| `channel_ref` | Optional channel reference. |
| `name` | Optional channel name. |
| `visible` | Optional visibility flag for update actions. |

## Returns

Operation result with stable channel IDs and selection-change flag.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Manage saved channels through a consolidated action tool.

Args:
    action: list/create/rename/show/hide/to_selection/selection_to_channel.
    channel_ref: Optional channel reference.
    name: Optional channel name.
    visible: Optional visibility flag for update actions.

Returns:
    Operation result with stable channel IDs and selection-change flag.
