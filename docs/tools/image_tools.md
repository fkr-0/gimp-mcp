# Image Management

Source module: `src/gimp_mcp_pro/tools/image_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`create_image`](#create-image) | Create a new blank image in GIMP. | 4 |
| [`list_images`](#list-images) | List all currently open images in GIMP. | 0 |
| [`get_image_info`](#get-image-info) | Get detailed metadata about the active image (no bitmap data). | 0 |
| [`export_image`](#export-image) | Export the active image to a file. | 3 |
| [`flatten_image`](#flatten-image) | Flatten all layers into a single layer. | 0 |
| [`duplicate_image`](#duplicate-image) | Duplicate the entire active image (all layers, channels, paths). | 0 |

## `create_image` {#create-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:33`

```python
async def create_image(width: int, height: int, color_mode: str = 'rgb', fill: str = 'white') -> ToolResult
```

**Parameters**

- `width`
- `height`
- `color_mode`
- `fill`

**Docstring**

Create a new blank image in GIMP.

Notes:
    Use this tool when starting a new project, creating a canvas for drawing.

Args:
    width: Image width in pixels (1-32768)
    height: Image height in pixels (1-32768)
    color_mode: Color mode — "rgb", "grayscale", or "indexed"
    fill: Initial fill — "white", "transparent", "foreground", or "background"

Returns:
    Operation result with image info in data field.

## `list_images` {#list-images}

Source: `src/gimp_mcp_pro/tools/image_tools.py:106`

```python
async def list_images() -> ToolResult
```

**Docstring**

List all currently open images in GIMP.

Notes:
    Use this tool before operations that need to target a specific image,
    or to verify what images are available.

Returns:
    Operation result with list of image info dicts.

## `get_image_info` {#get-image-info}

Source: `src/gimp_mcp_pro/tools/image_tools.py:162`

```python
async def get_image_info() -> ToolResult
```

**Docstring**

Get detailed metadata about the active image (no bitmap data).

Notes:
    Use this tool before any operation, to understand the current canvas
    dimensions, layer structure, and file state. Much faster than
    get_image_bitmap since it doesn't export pixel data.

Notes:
    Works well with: Use before create_layer (to match dimensions),
    before drawing (to verify layer structure), or before export
    (to check if image has unsaved changes).

Returns:
    Comprehensive image metadata including layers, channels, file info.

## `export_image` {#export-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:195`

```python
async def export_image(file_path: str, format: str | None = None, quality: int = 85) -> ToolResult
```

**Parameters**

- `file_path`
- `format`
- `quality`

**Docstring**

Export the active image to a file.

Notes:
    Use this tool when saving the final result as PNG, JPEG, etc.

Args:
    file_path: Output path (e.g., "/home/user/output.png")
    format: Export format — "png", "jpeg", "tiff", "bmp", "webp".
            Auto-detected from file extension if not specified.
    quality: Quality for lossy formats like JPEG (1-100). Default 85.

Returns:
    Operation result confirming export.

## `flatten_image` {#flatten-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:271`

```python
async def flatten_image() -> ToolResult
```

**Docstring**

Flatten all layers into a single layer.

Notes:
    Use this tool before final export when you want to merge all layers,
    or to simplify a complex layer structure.

Warnings:
    This is destructive — you lose individual layer editability.
    Consider using undo groups so the user can revert.

Returns:
    Operation result.

## `duplicate_image` {#duplicate-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:300`

```python
async def duplicate_image() -> ToolResult
```

**Docstring**

Duplicate the entire active image (all layers, channels, paths).

Notes:
    Use this tool when creating a copy to experiment on without affecting
    the original. Good before destructive operations.

Returns:
    Operation result with info about the new image.
