# MCP Tool Reference

This section is generated from the nested `@mcp.tool()` handler docstrings in `src/gimp_mcp_pro/tools`.

!!! info "Generated documentation"
    Regenerate with `uv run python scripts/docs.py generate` before building or publishing docs.

Total tools: **84**

| Category | Tools | Page |
|---|---:|---|
| Agent Tools | 3 | [agent_tools](agent_tools.md) |
| Color Adjustments | 13 | [color_tools](color_tools.md) |
| Drawing and Text | 10 | [drawing_tools](drawing_tools.md) |
| Filters and Effects | 8 | [filter_tools](filter_tools.md) |
| History | 4 | [history_tools](history_tools.md) |
| Image Management | 6 | [image_tools](image_tools.md) |
| Inspection | 8 | [inspect_tools](inspect_tools.md) |
| Layer Operations | 9 | [layer_tools](layer_tools.md) |
| PDB and Escape Hatch | 2 | [pdb_tools](pdb_tools.md) |
| Selections | 8 | [selection_tools](selection_tools.md) |
| Target Resolution | 2 | [target_tools](target_tools.md) |
| Transforms | 11 | [transform_tools](transform_tools.md) |

## Tool inventory

### Agent Tools

- [`begin_edit_transaction`](agent_tools.md#begin-edit-transaction) — Begin a reversible edit transaction backed by a GIMP undo group.
- [`end_edit_transaction`](agent_tools.md#end-edit-transaction) — End a tracked or best-effort GIMP undo transaction.
- [`rollback_transaction`](agent_tools.md#rollback-transaction) — Rollback a transaction using GIMP undo where available.

### Color Adjustments

- [`adjust_brightness_contrast`](color_tools.md#adjust-brightness-contrast) — Adjust brightness and contrast of a layer.
- [`adjust_hue_saturation`](color_tools.md#adjust-hue-saturation) — Adjust hue, saturation, and lightness of a layer.
- [`adjust_levels`](color_tools.md#adjust-levels) — Adjust levels for a layer.
- [`adjust_curves`](color_tools.md#adjust-curves) — Adjust curves for a layer.
- [`desaturate`](color_tools.md#desaturate) — Convert a layer to grayscale while keeping it in RGB mode.
- [`invert_colors`](color_tools.md#invert-colors) — Invert all colors in a layer (negative effect).
- [`apply_threshold`](color_tools.md#apply-threshold) — Apply threshold — convert to pure black and white.
- [`posterize`](color_tools.md#posterize) — Reduce the number of color levels (posterization effect).
- [`color_to_alpha`](color_tools.md#color-to-alpha) — Make a specific color transparent (color to alpha).
- [`auto_white_balance`](color_tools.md#auto-white-balance) — Automatically adjust white balance (stretch colors).
- [`get_colors`](color_tools.md#get-colors) — Get the current foreground and background colors.
- [`swap_colors`](color_tools.md#swap-colors) — Swap foreground and background colors.
- [`sample_color`](color_tools.md#sample-color) — Pick/sample a color from a pixel in the image.

### Drawing and Text

- [`set_foreground_color`](drawing_tools.md#set-foreground-color) — Set the foreground color used for drawing operations.
- [`set_background_color`](drawing_tools.md#set-background-color) — Set the background color.
- [`fill_selection`](drawing_tools.md#fill-selection) — Fill the current selection (or entire layer if no selection) with color.
- [`draw_line`](drawing_tools.md#draw-line) — Draw a straight line between two points.
- [`draw_brush_stroke`](drawing_tools.md#draw-brush-stroke) — Draw a stroke along a series of points.
- [`draw_rectangle`](drawing_tools.md#draw-rectangle) — Draw a rectangle (filled or outline only).
- [`draw_ellipse`](drawing_tools.md#draw-ellipse) — Draw an ellipse/circle (filled or outline only).
- [`draw_polygon`](drawing_tools.md#draw-polygon) — Draw a polygon (filled or outline).
- [`add_text`](drawing_tools.md#add-text) — Add a text layer to the image.
- [`edit_clear`](drawing_tools.md#edit-clear) — Clear the current selection area (make it transparent).

### Filters and Effects

- [`apply_gaussian_blur`](filter_tools.md#apply-gaussian-blur) — Apply Gaussian blur to a layer.
- [`apply_unsharp_mask`](filter_tools.md#apply-unsharp-mask) — Sharpen a layer using unsharp mask.
- [`apply_pixelize`](filter_tools.md#apply-pixelize) — Apply pixelization (mosaic) effect to a layer.
- [`apply_edge_detect`](filter_tools.md#apply-edge-detect) — Apply edge detection to a layer.
- [`apply_emboss`](filter_tools.md#apply-emboss) — Apply emboss effect to a layer.
- [`apply_noise`](filter_tools.md#apply-noise) — Add random noise to a layer.
- [`apply_median`](filter_tools.md#apply-median) — Apply median filter (denoise) to a layer.
- [`apply_drop_shadow`](filter_tools.md#apply-drop-shadow) — Apply a drop shadow effect to a layer.

### History

- [`undo`](history_tools.md#undo) — Undo the last operation(s).
- [`redo`](history_tools.md#redo) — Redo previously undone operation(s).
- [`begin_undo_group`](history_tools.md#begin-undo-group) — Start an undo group — all subsequent operations will be grouped
- [`end_undo_group`](history_tools.md#end-undo-group) — End the current undo group.

### Image Management

- [`create_image`](image_tools.md#create-image) — Create a new blank image in GIMP.
- [`list_images`](image_tools.md#list-images) — List all currently open images in GIMP.
- [`get_image_info`](image_tools.md#get-image-info) — Get detailed metadata about the active image (no bitmap data).
- [`export_image`](image_tools.md#export-image) — Export the active image to a file.
- [`flatten_image`](image_tools.md#flatten-image) — Flatten all layers into a single layer.
- [`duplicate_image`](image_tools.md#duplicate-image) — Duplicate the entire active image (all layers, channels, paths).

### Inspection

- [`session_capabilities`](inspect_tools.md#session-capabilities) — Report GIMP runtime capabilities and safety-relevant environment state.
- [`observe_document_state`](inspect_tools.md#observe-document-state) — Return a compact snapshot of the active GIMP document state.
- [`get_layer_tree_detailed`](inspect_tools.md#get-layer-tree-detailed) — Return detailed layer, group, visibility, lock, and bounds metadata.
- [`observe_region`](inspect_tools.md#observe-region) — Return a bounded visual observation and metadata for a rectangular region.
- [`get_image_bitmap`](inspect_tools.md#get-image-bitmap) — Get the current image as a viewable bitmap (PNG).
- [`get_image_metadata`](inspect_tools.md#get-image-metadata) — Get detailed metadata about the active image without bitmap data.
- [`get_context_state`](inspect_tools.md#get-context-state) — Get current GIMP context state (colors, brush, opacity, settings).
- [`get_gimp_info`](inspect_tools.md#get-gimp-info) — Get GIMP environment info (version, paths, capabilities).

### Layer Operations

- [`create_layer`](layer_tools.md#create-layer) — Create a new layer in the active image.
- [`list_layers`](layer_tools.md#list-layers) — List all layers in the active image with their properties.
- [`set_active_layer`](layer_tools.md#set-active-layer) — Set which layer is active (the one drawing tools operate on).
- [`delete_layer`](layer_tools.md#delete-layer) — Delete a layer from the active image.
- [`set_layer_opacity`](layer_tools.md#set-layer-opacity) — Set a layer's opacity.
- [`set_layer_visibility`](layer_tools.md#set-layer-visibility) — Show or hide a layer.
- [`duplicate_layer`](layer_tools.md#duplicate-layer) — Duplicate a layer.
- [`merge_visible_layers`](layer_tools.md#merge-visible-layers) — Merge all visible layers into one.
- [`add_alpha_channel`](layer_tools.md#add-alpha-channel) — Add an alpha (transparency) channel to a layer.

### PDB and Escape Hatch

- [`search_pdb`](pdb_tools.md#search-pdb) — Search GIMP's Procedure Database for available operations.
- [`execute_python`](pdb_tools.md#execute-python) — Execute raw Python code in GIMP's PyGObject console.

### Selections

- [`select_rectangle`](selection_tools.md#select-rectangle) — Create a rectangular selection.
- [`select_ellipse`](selection_tools.md#select-ellipse) — Create an elliptical selection.
- [`select_polygon`](selection_tools.md#select-polygon) — Create a polygon (freeform) selection.
- [`select_all`](selection_tools.md#select-all) — Select the entire image.
- [`select_none`](selection_tools.md#select-none) — Clear all selections.
- [`select_invert`](selection_tools.md#select-invert) — Invert the current selection (select everything NOT currently selected).
- [`select_grow`](selection_tools.md#select-grow) — Grow the current selection by a number of pixels.
- [`select_shrink`](selection_tools.md#select-shrink) — Shrink the current selection by a number of pixels.

### Target Resolution

- [`resolve_target`](target_tools.md#resolve-target) — Resolve a user or agent target reference into concrete GIMP object IDs.
- [`validate_targets`](target_tools.md#validate-targets) — Validate that proposed targets still exist and support required actions.

### Transforms

- [`scale_image`](transform_tools.md#scale-image) — Scale the entire image (all layers) to new dimensions.
- [`scale_layer`](transform_tools.md#scale-layer) — Scale a single layer to new dimensions.
- [`rotate_image`](transform_tools.md#rotate-image) — Rotate the entire image by 90, 180, or 270 degrees.
- [`rotate_layer`](transform_tools.md#rotate-layer) — Rotate a layer by an arbitrary angle.
- [`flip_image`](transform_tools.md#flip-image) — Flip the entire image.
- [`flip_layer`](transform_tools.md#flip-layer) — Flip a single layer.
- [`crop_to_selection`](transform_tools.md#crop-to-selection) — Crop the image to the current selection bounds.
- [`crop_image`](transform_tools.md#crop-image) — Crop the image to a specific rectangle.
- [`autocrop_image`](transform_tools.md#autocrop-image) — Automatically crop the image to remove border whitespace/transparency.
- [`resize_canvas`](transform_tools.md#resize-canvas) — Resize the image canvas without scaling content.
- [`offset_layer`](transform_tools.md#offset-layer) — Move a layer by an offset (reposition within the canvas).
