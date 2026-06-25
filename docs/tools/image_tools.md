# Image Management

Source module: `src/gimp_mcp_pro/tools/image_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`create_image`](#create-image) | Create a new blank image in GIMP. | 4 |
| [`add_guide`](#add-guide) | Add a horizontal or vertical guide to the active image. | 2 |
| [`delete_guide`](#delete-guide) | Delete a guide from the active image by guide ID. | 1 |
| [`list_guides`](#list-guides) | List guides on the active image with ID, orientation, and position. | 0 |
| [`set_image_grid`](#set-image-grid) | Configure grid spacing, offset, and visual style on the active image. | 5 |
| [`color_management_profile`](#color-management-profile) | Inspect or explicitly request guarded image color-profile operations. | 4 |
| [`list_images`](#list-images) | List all currently open images in GIMP. | 0 |
| [`get_image_info`](#get-image-info) | Get detailed metadata about the active image (no bitmap data). | 0 |
| [`export_with_manifest`](#export-with-manifest) | Export an image and write a JSON provenance sidecar manifest. | 4 |
| [`export_image`](#export-image) | Export the active image to a file. | 3 |
| [`flatten_image`](#flatten-image) | Flatten all layers into a single layer. | 0 |
| [`duplicate_image`](#duplicate-image) | Duplicate the entire active image (all layers, channels, paths). | 0 |

## `create_image` {#create-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:68`

```python
async def create_image(width: int, height: int, color_mode: str = 'rgb', fill: str = 'white') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `width` | Image width in pixels (1-32768) |
| `height` | Image height in pixels (1-32768) |
| `color_mode` | Color mode — "rgb", "grayscale", or "indexed" |
| `fill` | Initial fill — "white", "transparent", "foreground", or "background" |

## Returns

Operation result with image info in data field.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

## `add_guide` {#add-guide}

Source: `src/gimp_mcp_pro/tools/image_tools.py:141`

```python
async def add_guide(orientation: str = 'horizontal', position: int = 0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `orientation` | "horizontal"/"h" or "vertical"/"v". |
| `position` | Pixel position from the top for horizontal guides or from the left for vertical guides. |

## Returns

Operation result dictionary with guide orientation and position.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Add a horizontal or vertical guide to the active image.

Args:
    orientation: "horizontal"/"h" or "vertical"/"v".
    position: Pixel position from the top for horizontal guides or from the left for vertical guides.

Returns:
    Operation result dictionary with guide orientation and position.

## `delete_guide` {#delete-guide}

Source: `src/gimp_mcp_pro/tools/image_tools.py:177`

```python
async def delete_guide(guide_id: int) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `guide_id` | GIMP guide ID returned by add_guide or list_guides. |

## Returns

Operation result dictionary with the deleted guide ID.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Delete a guide from the active image by guide ID.

Args:
    guide_id: GIMP guide ID returned by add_guide or list_guides.

Returns:
    Operation result dictionary with the deleted guide ID.

## `list_guides` {#list-guides}

Source: `src/gimp_mcp_pro/tools/image_tools.py:204`

```python
async def list_guides() -> ToolResult
```

## Returns

Operation result dictionary containing a guides list and count.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List guides on the active image with ID, orientation, and position.

Returns:
    Operation result dictionary containing a guides list and count.

## `set_image_grid` {#set-image-grid}

Source: `src/gimp_mcp_pro/tools/image_tools.py:245`

```python
async def set_image_grid(xspacing: float = 10.0, yspacing: float = 10.0, xoffset: float = 0.0, yoffset: float = 0.0, style: str = 'intersections') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `xspacing` | Horizontal grid spacing in pixels. |
| `yspacing` | Vertical grid spacing in pixels. |
| `xoffset` | Horizontal grid offset in pixels. |
| `yoffset` | Vertical grid offset in pixels. |
| `style` | Grid style such as dots, intersections, on_off_dash, double_dash, or solid. |

## Returns

Operation result dictionary with applied grid settings.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Configure grid spacing, offset, and visual style on the active image.

Args:
    xspacing: Horizontal grid spacing in pixels.
    yspacing: Vertical grid spacing in pixels.
    xoffset: Horizontal grid offset in pixels.
    yoffset: Vertical grid offset in pixels.
    style: Grid style such as dots, intersections, on_off_dash, double_dash, or solid.

Returns:
    Operation result dictionary with applied grid settings.

## `color_management_profile` {#color-management-profile}

Source: `src/gimp_mcp_pro/tools/image_tools.py:305`

```python
async def color_management_profile(action: str = 'inspect', profile_ref: str | None = None, rendering_intent: str = 'perceptual', confirm: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `action` | inspect, assign, or convert. |
| `profile_ref` | Optional profile reference for assign/convert operations. |
| `rendering_intent` | Requested rendering intent label. |
| `confirm` | Required for assign/convert operations. |

## Returns

Operation result with profile metadata or guarded operation request metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Inspect or explicitly request guarded image color-profile operations.

Args:
    action: inspect, assign, or convert.
    profile_ref: Optional profile reference for assign/convert operations.
    rendering_intent: Requested rendering intent label.
    confirm: Required for assign/convert operations.

Returns:
    Operation result with profile metadata or guarded operation request metadata.

## `list_images` {#list-images}

Source: `src/gimp_mcp_pro/tools/image_tools.py:360`

```python
async def list_images() -> ToolResult
```

## Returns

Operation result with list of image info dicts.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List all currently open images in GIMP.

Notes:
    Use this tool before operations that need to target a specific image,
    or to verify what images are available.

Returns:
    Operation result with list of image info dicts.

## `get_image_info` {#get-image-info}

Source: `src/gimp_mcp_pro/tools/image_tools.py:416`

```python
async def get_image_info() -> ToolResult
```

## Returns

Comprehensive image metadata including layers, channels, file info.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

## `export_with_manifest` {#export-with-manifest}

Source: `src/gimp_mcp_pro/tools/image_tools.py:449`

```python
async def export_with_manifest(format: str, destination: str, include_sidecar: bool = True, export_settings: dict[str, Any] | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `format` | Export format: png, jpeg/jpg, webp, tiff/tif, psd, or xcf. |
| `destination` | Output file path. |
| `include_sidecar` | Write ``.manifest.json`` next to the export. |
| `export_settings` | Optional format-specific settings. |

## Returns

Operation result with export path and manifest metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Export an image and write a JSON provenance sidecar manifest.

Args:
    format: Export format: png, jpeg/jpg, webp, tiff/tif, psd, or xcf.
    destination: Output file path.
    include_sidecar: Write ``.manifest.json`` next to the export.
    export_settings: Optional format-specific settings.

Returns:
    Operation result with export path and manifest metadata.

## `export_image` {#export-image}

Source: `src/gimp_mcp_pro/tools/image_tools.py:528`

```python
async def export_image(file_path: str, format: str | None = None, quality: int = 85) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `file_path` | Output path (e.g., "/home/user/output.png") |
| `format` | Export format — "png", "jpeg", "tiff", "bmp", "webp". Auto-detected from file extension if not specified. |
| `quality` | Quality for lossy formats like JPEG (1-100). Default 85. |

## Returns

Operation result confirming export.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/image_tools.py:604`

```python
async def flatten_image() -> ToolResult
```

## Returns

Operation result.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

Source: `src/gimp_mcp_pro/tools/image_tools.py:633`

```python
async def duplicate_image() -> ToolResult
```

## Returns

Operation result with info about the new image.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Duplicate the entire active image (all layers, channels, paths).

Notes:
    Use this tool when creating a copy to experiment on without affecting
    the original. Good before destructive operations.

Returns:
    Operation result with info about the new image.
