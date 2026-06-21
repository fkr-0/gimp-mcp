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
async def create_image(width: int, height: int, color_mode: str = 'rgb', fill: str = 'white') -> dict[str, Any]
```

**Parameters**

- `width`
- `height`
- `color_mode`
- `fill`

**Docstring**

Create a new blank image in GIMP.

WHEN TO USE: Starting a new project, creating a canvas for drawing.

Args:
    width: Image width in pixels (1-32768)
    height: Image height in pixels (1-32768)
    color_mode: Color mode — "rgb", "grayscale", or "indexed"
    fill: Initial fill — "white", "transparent", "foreground", or "background"

Returns:
    Operation result with image info in data field.

## `list_images` {#list-images}

Source: `src/gimp_mcp_pro/tools/image_tools.py:105`

```python
async def list_images() -> dict[str, Any]
```

**Docstring**

List all currently open images in GIMP.

WHEN TO USE: Before operations that need to target a specific image,
or to verify what images are available.

Returns:
    Operation result with list of image info dicts.

## `get_image_info` {#get-image-info}

Source: `src/gimp_mcp_pro/tools/image_tools.py:160`

```python
async def get_image_info() -> dict[str, Any]
```

**Docstring**

Get detailed metadata about the active image (no bitmap data).

WHEN TO USE: Before any operation, to understand the current canvas
dimensions, layer structure, and file state. Much faster than
get_image_bitmap since it doesn't export pixel data.

COMBINES WITH: Use before create_layer (to match dimensions),
before drawing (to verify layer structure), or before export
(to check if image has unsaved changes).

Returns:
    Comprehensive image metadata including layers, channels, file info.

## `export_image` {#export-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:191`

```python
async def export_image(file_path: str, format: str | None = None, quality: int = 85) -> dict[str, Any]
```

**Parameters**

- `file_path`
- `format`
- `quality`

**Docstring**

Export the active image to a file.

WHEN TO USE: Saving the final result as PNG, JPEG, etc.

Args:
    file_path: Output path (e.g., "/home/user/output.png")
    format: Export format — "png", "jpeg", "tiff", "bmp", "webp".
            Auto-detected from file extension if not specified.
    quality: Quality for lossy formats like JPEG (1-100). Default 85.

Returns:
    Operation result confirming export.

## `flatten_image` {#flatten-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:266`

```python
async def flatten_image() -> dict[str, Any]
```

**Docstring**

Flatten all layers into a single layer.

WHEN TO USE: Before final export when you want to merge all layers,
or to simplify a complex layer structure.

WARNING: This is destructive — you lose individual layer editability.
Consider using undo groups so the user can revert.

Returns:
    Operation result.

## `duplicate_image` {#duplicate-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:293`

```python
async def duplicate_image() -> dict[str, Any]
```

**Docstring**

Duplicate the entire active image (all layers, channels, paths).

WHEN TO USE: Creating a copy to experiment on without affecting
the original. Good before destructive operations.

Returns:
    Operation result with info about the new image.
