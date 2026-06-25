# Filters and Effects

Source module: `src/gimp_mcp_pro/tools/filter_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`preview_filter`](#preview-filter) | Apply a supported filter to a temporary preview layer. | 5 |
| [`commit_filter_preview`](#commit-filter-preview) | Commit or discard a temporary filter preview layer. | 3 |
| [`apply_gaussian_blur`](#apply-gaussian-blur) | Apply Gaussian blur to a layer. | 4 |
| [`apply_motion_blur`](#apply-motion-blur) | Apply linear, circular, or zoom motion blur to a layer. | 8 |
| [`apply_unsharp_mask`](#apply-unsharp-mask) | Sharpen a layer using unsharp mask. | 5 |
| [`apply_pixelize`](#apply-pixelize) | Apply pixelization (mosaic) effect to a layer. | 4 |
| [`apply_edge_detect`](#apply-edge-detect) | Apply edge detection to a layer. | 4 |
| [`apply_emboss`](#apply-emboss) | Apply emboss effect to a layer. | 5 |
| [`apply_noise`](#apply-noise) | Add random noise to a layer. | 3 |
| [`apply_median`](#apply-median) | Apply median filter (denoise) to a layer. | 3 |
| [`apply_drop_shadow`](#apply-drop-shadow) | Apply a drop shadow effect to a layer. | 7 |
| [`preview_gegl_operation`](#preview-gegl-operation) | Render bounded before/after metadata for a GEGL operation without committing. | 4 |
| [`apply_gegl_operation`](#apply-gegl-operation) | Apply or dry-run an allowlisted GEGL DrawableFilter operation. | 4 |

## `preview_filter` {#preview-filter}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:292`

```python
async def preview_filter(filter: str, parameters: dict[str, object] | None = None, preview_mode: str = 'temporary_layer', layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `filter` | Supported filter name such as ``gaussian_blur``. |
| `parameters` | Filter-specific parameter dictionary. |
| `preview_mode` | Currently ``temporary_layer``. |
| `layer_name` | Target layer by name. |
| `layer_index` | Target layer by index. |

## Returns

Operation result with preview metadata and warnings. Contract: The original drawable is not filtered. A copied preview layer receives the GEGL filter so the caller can inspect before committing.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Apply a supported filter to a temporary preview layer.

Args:
    filter: Supported filter name such as ``gaussian_blur``.
    parameters: Filter-specific parameter dictionary.
    preview_mode: Currently ``temporary_layer``.
    layer_name: Target layer by name.
    layer_index: Target layer by index.

Returns:
    Operation result with preview metadata and warnings.

Contract:
    The original drawable is not filtered. A copied preview layer receives
    the GEGL filter so the caller can inspect before committing.

## `commit_filter_preview` {#commit-filter-preview}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:346`

```python
async def commit_filter_preview(preview_id: str, action: str, committed_name: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `preview_id` | Preview layer name or ID returned by a preview workflow. |
| `action` | ``commit`` to promote the layer, or ``discard`` to remove it. |
| `committed_name` | Optional final layer name when committing. |

## Returns

Operation result with commit/discard metadata. Contract: Discard always removes the temporary preview layer. Commit is wrapped in a GIMP undo group transaction and never calls export or save APIs.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Commit or discard a temporary filter preview layer.

Args:
    preview_id: Preview layer name or ID returned by a preview workflow.
    action: ``commit`` to promote the layer, or ``discard`` to remove it.
    committed_name: Optional final layer name when committing.

Returns:
    Operation result with commit/discard metadata.

Contract:
    Discard always removes the temporary preview layer. Commit is wrapped
    in a GIMP undo group transaction and never calls export or save APIs.

## `apply_gaussian_blur` {#apply-gaussian-blur}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:395`

```python
async def apply_gaussian_blur(radius_x: float = 5.0, radius_y: float | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `radius_x` | Horizontal blur radius in pixels (0.0-500.0) |
| `radius_y` | Vertical blur radius. Defaults to radius_x for uniform blur. |
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

## `apply_motion_blur` {#apply-motion-blur}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:438`

```python
async def apply_motion_blur(blur_type: str = 'linear', length: float = 10.0, angle: float = 0.0, center_x: float = 0.0, center_y: float = 0.0, factor: float = 0.1, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `blur_type` | "linear", "circular", or "zoom". |
| `length` | Linear blur length in pixels. |
| `angle` | Linear/circular blur angle in degrees. |
| `center_x` | Circular/zoom blur center X coordinate. |
| `center_y` | Circular/zoom blur center Y coordinate. |
| `factor` | Zoom blur factor. |
| `layer_name` | Target layer. Uses active layer if not specified. |
| `layer_index` | Target layer by index. |

## Returns

Operation result dictionary with status, message, and applied blur settings.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Apply linear, circular, or zoom motion blur to a layer.

Args:
    blur_type: "linear", "circular", or "zoom".
    length: Linear blur length in pixels.
    angle: Linear/circular blur angle in degrees.
    center_x: Circular/zoom blur center X coordinate.
    center_y: Circular/zoom blur center Y coordinate.
    factor: Zoom blur factor.
    layer_name: Target layer. Uses active layer if not specified.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and applied blur settings.

## `apply_unsharp_mask` {#apply-unsharp-mask}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:519`

```python
async def apply_unsharp_mask(amount: float = 0.5, radius: float = 3.0, threshold: float = 0.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `amount` | Sharpening strength (0.0-5.0, typical 0.3-1.0) |
| `radius` | Detail radius in pixels (0.1-120.0, typical 1.0-5.0) |
| `threshold` | Minimum difference threshold (0.0-1.0, higher = less sharpening of subtle detail) |
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

Source: `src/gimp_mcp_pro/tools/filter_tools.py:562`

```python
async def apply_pixelize(block_width: int = 10, block_height: int | None = None, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `block_width` | Pixel block width (1-1024) |
| `block_height` | Pixel block height. Defaults to block_width for square blocks. |
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

Source: `src/gimp_mcp_pro/tools/filter_tools.py:604`

```python
async def apply_edge_detect(method: str = 'sobel', amount: float = 1.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `method` | Detection algorithm — "sobel", "prewitt", "laplace" |
| `amount` | Edge detection strength (0.0-10.0) |
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

Source: `src/gimp_mcp_pro/tools/filter_tools.py:646`

```python
async def apply_emboss(azimuth: float = 315.0, elevation: float = 45.0, depth: int = 2, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `azimuth` | Light angle in degrees (0-360, default 315 = upper-left) |
| `elevation` | Light elevation in degrees (0-180) |
| `depth` | Emboss depth (1-100) |
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

Source: `src/gimp_mcp_pro/tools/filter_tools.py:686`

```python
async def apply_noise(amount: float = 0.2, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `amount` | Noise intensity (0.0-1.0) |
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

Source: `src/gimp_mcp_pro/tools/filter_tools.py:723`

```python
async def apply_median(radius: int = 3, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `radius` | Filter radius (1-20) |
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

Apply median filter (denoise) to a layer.

Good for removing salt-and-pepper noise while preserving edges.

Args:
    radius: Filter radius (1-20)
    layer_name: Target layer.
    layer_index: Target layer by index.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `apply_drop_shadow` {#apply-drop-shadow}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:758`

```python
async def apply_drop_shadow(offset_x: float = 4.0, offset_y: float = 4.0, blur_radius: float = 8.0, color: str = 'black', opacity: float = 60.0, layer_name: str | None = None, layer_index: int | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `offset_x` | Shadow horizontal offset (positive = right) |
| `offset_y` | Shadow vertical offset (positive = down) |
| `blur_radius` | Shadow blur amount |
| `color` | Shadow color (default "black") |
| `opacity` | Shadow opacity 0-100 |
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

## `preview_gegl_operation` {#preview-gegl-operation}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:816`

```python
async def preview_gegl_operation(target: dict[str, Any] | str, operation: str, properties: dict[str, Any] | None = None, preview_region: dict[str, int] | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `target` | Layer target reference. |
| `operation` | GEGL operation name. |
| `properties` | Operation properties. |
| `preview_region` | Optional bounded preview rectangle. |

## Returns

Operation result with before/after preview placeholders and metrics.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Render bounded before/after metadata for a GEGL operation without committing.

Args:
    target: Layer target reference.
    operation: GEGL operation name.
    properties: Operation properties.
    preview_region: Optional bounded preview rectangle.

Returns:
    Operation result with before/after preview placeholders and metrics.

## `apply_gegl_operation` {#apply-gegl-operation}

Source: `src/gimp_mcp_pro/tools/filter_tools.py:855`

```python
async def apply_gegl_operation(target: dict[str, object] | str, operation: str, properties: dict[str, object] | None = None, dry_run: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `target` | Layer reference such as a layer name or layer_index mapping. |
| `operation` | Allowlisted GEGL operation name. |
| `properties` | Operation properties validated against the operation schema. |
| `dry_run` | Validate and report without mutating the drawable when true. |

## Returns

Operation result with changed-bounds and applied-property metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Apply or dry-run an allowlisted GEGL DrawableFilter operation.

Args:
    target: Layer reference such as a layer name or layer_index mapping.
    operation: Allowlisted GEGL operation name.
    properties: Operation properties validated against the operation schema.
    dry_run: Validate and report without mutating the drawable when true.

Returns:
    Operation result with changed-bounds and applied-property metadata.
