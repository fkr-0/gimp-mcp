# Layer Operations

Source module: `src/gimp_mcp_pro/tools/layer_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`create_layer`](#create-layer) | Create a new layer in the active image. | 8 |
| [`list_layers`](#list-layers) | List all layers in the active image with their properties. | 0 |
| [`set_active_layer`](#set-active-layer) | Set which layer is active (the one drawing tools operate on). | 2 |
| [`delete_layer`](#delete-layer) | Delete a layer from the active image. | 2 |
| [`set_layer_opacity`](#set-layer-opacity) | Set a layer's opacity. | 3 |
| [`set_layer_visibility`](#set-layer-visibility) | Show or hide a layer. | 3 |
| [`duplicate_layer`](#duplicate-layer) | Duplicate a layer. | 3 |
| [`merge_visible_layers`](#merge-visible-layers) | Merge all visible layers into one. | 0 |
| [`add_alpha_channel`](#add-alpha-channel) | Add an alpha (transparency) channel to a layer. | 2 |

## `create_layer` {#create-layer}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:47`

```python
async def create_layer(name: str = 'New Layer', opacity: float = 100.0, blend_mode: str = 'normal', fill: str = 'transparent', has_alpha: bool = True, position: int = 0, width: int | None = None, height: int | None = None) -> ToolResult
```

**Parameters**

- `name`
- `opacity`
- `blend_mode`
- `fill`
- `has_alpha`
- `position`
- `width`
- `height`

**Docstring**

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

Returns:
    Operation result with layer info.

## `list_layers` {#list-layers}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:124`

```python
async def list_layers() -> ToolResult
```

**Docstring**

List all layers in the active image with their properties.

Notes:
    Use this tool before drawing (to find the right layer), when debugging
    visual issues, or to understand image structure.

Returns:
    Layer list with name, visibility, opacity, blend mode, dimensions.

## `set_active_layer` {#set-active-layer}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:171`

```python
async def set_active_layer(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `layer_name`
- `layer_index`

**Docstring**

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

Source: `src/gimp_mcp_pro/tools/layer_tools.py:214`

```python
async def delete_layer(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `layer_name`
- `layer_index`

**Docstring**

Delete a layer from the active image.

Args:
    layer_name: Name of layer to delete.
    layer_index: Index of layer to delete (0 = topmost).

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `set_layer_opacity` {#set-layer-opacity}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:247`

```python
async def set_layer_opacity(opacity: float, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `opacity`
- `layer_name`
- `layer_index`

**Docstring**

Set a layer's opacity.

Args:
    opacity: Opacity 0-100 (0 = fully transparent, 100 = fully opaque)
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `set_layer_visibility` {#set-layer-visibility}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:282`

```python
async def set_layer_visibility(visible: bool, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `visible`
- `layer_name`
- `layer_index`

**Docstring**

Show or hide a layer.

Args:
    visible: True to show, False to hide.
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `duplicate_layer` {#duplicate-layer}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:313`

```python
async def duplicate_layer(layer_name: str | None = None, layer_index: int | None = None, new_name: str | None = None) -> ToolResult
```

**Parameters**

- `layer_name`
- `layer_index`
- `new_name`

**Docstring**

Duplicate a layer.

Args:
    layer_name: Source layer name.
    layer_index: Source layer index. Uses active layer if neither specified.
    new_name: Name for the duplicate. Defaults to "Copy of <original>".

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `merge_visible_layers` {#merge-visible-layers}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:349`

```python
async def merge_visible_layers() -> ToolResult
```

**Docstring**

Merge all visible layers into one.

Notes:
    Use this tool when consolidate visible work while preserving hidden layers.

Warnings:
    Destructive operation — consider using undo groups.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `add_alpha_channel` {#add-alpha-channel}

Source: `src/gimp_mcp_pro/tools/layer_tools.py:377`

```python
async def add_alpha_channel(layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

**Parameters**

- `layer_name`
- `layer_index`

**Docstring**

Add an alpha (transparency) channel to a layer.

Notes:
    Use this tool before using transparent fills or edit_clear on a layer
    that was created without alpha (e.g., the default Background layer).

Args:
    layer_name: Target layer by name.
    layer_index: Target layer by index. Uses active layer if neither specified.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
