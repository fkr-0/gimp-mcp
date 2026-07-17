# MCP Tool Reference

This section is generated from the nested `@mcp.tool()` handler docstrings in `src/gimp_mcp_pro/tools`.

!!! info "Generated documentation"
    Regenerate with `uv run python scripts/docs.py generate` before building or publishing docs.

Total tools: **183**

| Category | Tools | Page |
|---|---:|---|
| Agent Tools | 3 | [agent_tools](agent_tools.md) |
| Color Adjustments | 25 | [color_tools](color_tools.md) |
| Drawing and Text | 13 | [drawing_tools](drawing_tools.md) |
| Filters and Effects | 13 | [filter_tools](filter_tools.md) |
| Repeatable Flows and Macros | 11 | [flow_tools](flow_tools.md) |
| gimp.dev Integration | 2 | [gimp_dev_tools](gimp_dev_tools.md) |
| History | 6 | [history_tools](history_tools.md) |
| Image Management | 15 | [image_tools](image_tools.md) |
| Inspection | 17 | [inspect_tools](inspect_tools.md) |
| Layer Operations | 30 | [layer_tools](layer_tools.md) |
| Vector Paths | 8 | [path_tools](path_tools.md) |
| PDB and Escape Hatch | 5 | [pdb_tools](pdb_tools.md) |
| Selections | 17 | [selection_tools](selection_tools.md) |
| Target Resolution | 3 | [target_tools](target_tools.md) |
| Transforms | 15 | [transform_tools](transform_tools.md) |

## Tool inventory

### Agent Tools

- [`begin_edit_transaction`](agent_tools.md#begin-edit-transaction) — Begin a reversible edit transaction backed by a GIMP undo group.
- [`end_edit_transaction`](agent_tools.md#end-edit-transaction) — End a tracked or best-effort GIMP undo transaction.
- [`rollback_transaction`](agent_tools.md#rollback-transaction) — Rollback a transaction using GIMP undo where available.

### Color Adjustments

- [`adjust_brightness_contrast`](color_tools.md#adjust-brightness-contrast) — Adjust brightness and contrast of a layer.
- [`adjust_hue_saturation`](color_tools.md#adjust-hue-saturation) — Adjust hue, saturation, and lightness of a layer.
- [`adjust_color_balance`](color_tools.md#adjust-color-balance) — Adjust shadows, midtones, or highlights color balance for a layer.
- [`adjust_levels`](color_tools.md#adjust-levels) — Adjust levels for a layer.
- [`adjust_curves`](color_tools.md#adjust-curves) — Adjust curves for a layer.
- [`desaturate`](color_tools.md#desaturate) — Convert a layer to grayscale while keeping it in RGB mode.
- [`invert_colors`](color_tools.md#invert-colors) — Invert all colors in a layer (negative effect).
- [`apply_threshold`](color_tools.md#apply-threshold) — Apply threshold — convert to pure black and white.
- [`posterize`](color_tools.md#posterize) — Reduce the number of color levels (posterization effect).
- [`color_to_alpha`](color_tools.md#color-to-alpha) — Make a specific color transparent (color to alpha).
- [`replace_color`](color_tools.md#replace-color) — Replace pixels matching a source color with a replacement color.
- [`auto_white_balance`](color_tools.md#auto-white-balance) — Automatically adjust white balance (stretch colors).
- [`brush_inventory`](color_tools.md#brush-inventory) — List paint resources with current-context markers.
- [`set_paint_resource`](color_tools.md#set-paint-resource) — Set one active paint resource by validated name.
- [`set_paint_context`](color_tools.md#set-paint-context) — Set multiple paint context fields with validation and read-back.
- [`resource_catalog`](color_tools.md#resource-catalog) — List bounded searchable resources with optional capability notes.
- [`list_gimp_resources`](color_tools.md#list-gimp-resources) — List available GIMP brushes, patterns, fonts, and gradients.
- [`get_colors`](color_tools.md#get-colors) — Get the current foreground and background colors.
- [`swap_colors`](color_tools.md#swap-colors) — Swap foreground and background colors.
- [`analyze_color_palette`](color_tools.md#analyze-color-palette) — Extract a deterministic approximate color palette for a layer or region.
- [`dominant_colors`](color_tools.md#dominant-colors) — Return dominant colors for a layer or region.
- [`analyze_color_histogram`](color_tools.md#analyze-color-histogram) — Analyze channel histogram summary statistics for a layer.
- [`sample_pixels`](color_tools.md#sample-pixels) — Sample colors at multiple points or over a rectangular grid.
- [`sample_color`](color_tools.md#sample-color) — Pick/sample a color from a pixel in the image.
- [`palette_create_or_update`](color_tools.md#palette-create-or-update) — Create, inspect, or update a palette from provided colors.

### Drawing and Text

- [`set_foreground_color`](drawing_tools.md#set-foreground-color) — Set the foreground color used for drawing operations.
- [`set_background_color`](drawing_tools.md#set-background-color) — Set the background color.
- [`fill_selection`](drawing_tools.md#fill-selection) — Fill the current selection (or entire layer if no selection) with color.
- [`draw_line`](drawing_tools.md#draw-line) — Draw a straight line between two points.
- [`draw_brush_stroke`](drawing_tools.md#draw-brush-stroke) — Draw a stroke along a series of points.
- [`draw_rectangle`](drawing_tools.md#draw-rectangle) — Draw a rectangle (filled or outline only).
- [`draw_ellipse`](drawing_tools.md#draw-ellipse) — Draw an ellipse/circle (filled or outline only).
- [`draw_polygon`](drawing_tools.md#draw-polygon) — Draw a polygon (filled or outline).
- [`create_text_box`](drawing_tools.md#create-text-box) — Create a new text layer at an explicit rectangle with styling.
- [`add_text`](drawing_tools.md#add-text) — Add a text layer to the image.
- [`gradient_fill`](drawing_tools.md#gradient-fill) — Fill the current drawable/selection with a gradient between two points.
- [`edit_text_layer`](drawing_tools.md#edit-text-layer) — Edit an existing text layer's content and core text properties.
- [`edit_clear`](drawing_tools.md#edit-clear) — Clear the current selection area (make it transparent).

### Filters and Effects

- [`preview_filter`](filter_tools.md#preview-filter) — Apply a supported filter to a temporary preview layer.
- [`commit_filter_preview`](filter_tools.md#commit-filter-preview) — Commit or discard a temporary filter preview layer.
- [`apply_gaussian_blur`](filter_tools.md#apply-gaussian-blur) — Apply Gaussian blur to a layer.
- [`apply_motion_blur`](filter_tools.md#apply-motion-blur) — Apply linear, circular, or zoom motion blur to a layer.
- [`apply_unsharp_mask`](filter_tools.md#apply-unsharp-mask) — Sharpen a layer using unsharp mask.
- [`apply_pixelize`](filter_tools.md#apply-pixelize) — Apply pixelization (mosaic) effect to a layer.
- [`apply_edge_detect`](filter_tools.md#apply-edge-detect) — Apply edge detection to a layer.
- [`apply_emboss`](filter_tools.md#apply-emboss) — Apply emboss effect to a layer.
- [`apply_noise`](filter_tools.md#apply-noise) — Add random noise to a layer.
- [`apply_median`](filter_tools.md#apply-median) — Apply median filter (denoise) to a layer.
- [`apply_drop_shadow`](filter_tools.md#apply-drop-shadow) — Apply a drop shadow effect to a layer.
- [`preview_gegl_operation`](filter_tools.md#preview-gegl-operation) — Render bounded before/after metadata for a GEGL operation without committing.
- [`apply_gegl_operation`](filter_tools.md#apply-gegl-operation) — Apply or dry-run an allowlisted GEGL DrawableFilter operation.

### Repeatable Flows and Macros

- [`propose_flow`](flow_tools.md#propose-flow) — Save an agent-authored flow proposal as an inactive draft.
- [`list_flows`](flow_tools.md#list-flows) — List user-local flows, optionally filtered by lifecycle state.
- [`get_flow`](flow_tools.md#get-flow) — Return one complete flow definition.
- [`validate_flow`](flow_tools.md#validate-flow) — Statically validate operation names and arguments, then mark valid drafts.
- [`activate_flow`](flow_tools.md#activate-flow) — Explicitly activate a validated flow.
- [`deactivate_flow`](flow_tools.md#deactivate-flow) — Return an active flow to validated state and unpin it.
- [`pin_flow`](flow_tools.md#pin-flow) — Pin an active flow into GIMP's Repeatable Flows menu.
- [`unpin_flow`](flow_tools.md#unpin-flow) — Remove a flow's direct GIMP menu entry.
- [`run_flow`](flow_tools.md#run-flow) — Execute a validated or active flow through the shared operation registry.
- [`dry_run_macro`](flow_tools.md#dry-run-macro) — Validate a typed multi-step macro without mutating GIMP state.
- [`run_macro_transaction`](flow_tools.md#run-macro-transaction) — Execute a typed multi-step macro as one fail-safe transaction.

### gimp.dev Integration

- [`gimp_dev_status`](gimp_dev_tools.md#gimp-dev-status) — Return local ``gimp.dev`` integration availability.
- [`gimp_dev_plugin_catalog`](gimp_dev_tools.md#gimp-dev-plugin-catalog) — Return the pure ``gimp.dev`` plug-in procedure catalog.

### History

- [`create_checkpoint`](history_tools.md#create-checkpoint) — Create a controlled checkpoint record for the active image.
- [`get_operation_log`](history_tools.md#get-operation-log) — Return recent MCP operation-log entries.
- [`undo`](history_tools.md#undo) — Undo the last operation(s).
- [`redo`](history_tools.md#redo) — Redo previously undone operation(s).
- [`begin_undo_group`](history_tools.md#begin-undo-group) — Start an undo group — all subsequent operations will be grouped
- [`end_undo_group`](history_tools.md#end-undo-group) — End the current undo group.

### Image Management

- [`create_image`](image_tools.md#create-image) — Create a new blank image in GIMP.
- [`add_guide`](image_tools.md#add-guide) — Add a horizontal or vertical guide to the active image.
- [`delete_guide`](image_tools.md#delete-guide) — Delete a guide from the active image by guide ID.
- [`list_guides`](image_tools.md#list-guides) — List guides on the active image with ID, orientation, and position.
- [`set_image_grid`](image_tools.md#set-image-grid) — Configure grid spacing, offset, and visual style on the active image.
- [`color_management_profile`](image_tools.md#color-management-profile) — Inspect or explicitly request guarded image color-profile operations.
- [`list_images`](image_tools.md#list-images) — List all currently open images in GIMP.
- [`get_image_info`](image_tools.md#get-image-info) — Get detailed metadata about the active image (no bitmap data).
- [`export_with_manifest`](image_tools.md#export-with-manifest) — Export an image and write a JSON provenance sidecar manifest.
- [`export_image`](image_tools.md#export-image) — Export the active image to a file.
- [`flatten_image`](image_tools.md#flatten-image) — Flatten all layers into a single layer.
- [`duplicate_image`](image_tools.md#duplicate-image) — Duplicate the entire active image (all layers, channels, paths).
- [`import_as_layer_with_metadata`](image_tools.md#import-as-layer-with-metadata) — Import an external image as a layer with provenance metadata.
- [`batch_export_variants`](image_tools.md#batch-export-variants) — Export multiple bounded variants from the active image.
- [`manage_guides_and_grid`](image_tools.md#manage-guides-and-grid) — Create, list, move, remove guides, or set document grid settings.

### Inspection

- [`create_contact_sheet`](inspect_tools.md#create-contact-sheet) — Render contact-sheet metadata for visible or selected layers.
- [`observe_region`](inspect_tools.md#observe-region) — Return a bounded visual observation and metadata for a rectangular region.
- [`get_image_bitmap`](inspect_tools.md#get-image-bitmap) — Get the current image as a viewable bitmap (PNG).
- [`explain_current_context`](inspect_tools.md#explain-current-context) — Explain the current canvas state as an LLM-oriented context packet.
- [`session_capabilities`](inspect_tools.md#session-capabilities) — Report GIMP runtime capabilities and safety-relevant environment state.
- [`compare_snapshots`](inspect_tools.md#compare-snapshots) — Compare two supplied snapshot, thumbnail, or region payloads.
- [`observe_document_state`](inspect_tools.md#observe-document-state) — Return a compact snapshot of the active GIMP document state.
- [`get_image_metadata`](inspect_tools.md#get-image-metadata) — Get detailed metadata about the active image without bitmap data.
- [`assert_image_state`](inspect_tools.md#assert-image-state) — Evaluate typed postconditions against supplied or active document state.
- [`get_layer_tree_detailed`](inspect_tools.md#get-layer-tree-detailed) — Return detailed layer, group, visibility, lock, and bounds metadata.
- [`measure_geometry`](inspect_tools.md#measure-geometry) — Measure bounds, distance, overlap, alignment, and spacing for targets.
- [`get_context_state`](inspect_tools.md#get-context-state) — Get current GIMP context state (colors, brush, opacity, settings).
- [`generate_layer_report`](inspect_tools.md#generate-layer-report) — Generate a read-only structured report of layers and export-relevant warnings.
- [`get_gimp_info`](inspect_tools.md#get-gimp-info) — Get GIMP environment info (version, paths, capabilities).
- [`prepare_export_checklist`](inspect_tools.md#prepare-export-checklist) — Prepare a read-only export readiness checklist for common image formats.
- [`content_bounds`](inspect_tools.md#content-bounds) — Inspect non-transparent content bounds for a layer without mutation.
- [`text_layer_introspection`](inspect_tools.md#text-layer-introspection) — Read text-layer metadata without rasterizing or mutating the layer.

### Layer Operations

- [`create_layer`](layer_tools.md#create-layer) — Create a new layer in the active image.
- [`list_layers`](layer_tools.md#list-layers) — List all layers in the active image with their properties.
- [`set_active_layer`](layer_tools.md#set-active-layer) — Set which layer is active (the one drawing tools operate on).
- [`delete_layer`](layer_tools.md#delete-layer) — Delete a layer from the active image.
- [`set_layer_opacity`](layer_tools.md#set-layer-opacity) — Set a layer's opacity.
- [`set_layer_visibility`](layer_tools.md#set-layer-visibility) — Show or hide a layer.
- [`set_layer_mode`](layer_tools.md#set-layer-mode) — Set a layer's blend mode (normal, multiply, screen, overlay, etc.).
- [`set_layer_blend_mode`](layer_tools.md#set-layer-blend-mode) — Alias for set_layer_mode with discoverable blend-mode naming.
- [`duplicate_layer`](layer_tools.md#duplicate-layer) — Duplicate a layer.
- [`merge_visible_layers`](layer_tools.md#merge-visible-layers) — Merge all visible layers into one.
- [`new_layer_from_visible`](layer_tools.md#new-layer-from-visible) — Create a new layer from the current visible composite without merging originals.
- [`merge_down`](layer_tools.md#merge-down) — Merge a layer down into the layer below it.
- [`copy_layer_alpha_to_mask`](layer_tools.md#copy-layer-alpha-to-mask) — Copy a source layer's alpha silhouette into the target layer mask.
- [`selection_to_layer_mask`](layer_tools.md#selection-to-layer-mask) — Create or replace a layer mask from the current selection.
- [`create_mask_from_color`](layer_tools.md#create-mask-from-color) — Create a layer mask from an explicit color or sampled color selection.
- [`add_layer_mask`](layer_tools.md#add-layer-mask) — Add a layer mask to a layer.
- [`get_layer_mask_info`](layer_tools.md#get-layer-mask-info) — Get layer mask status for a layer.
- [`set_layer_mask_state`](layer_tools.md#set-layer-mask-state) — Set layer mask editing/display/apply flags.
- [`remove_layer_mask`](layer_tools.md#remove-layer-mask) — Remove a layer mask, optionally applying it first.
- [`create_layer_group`](layer_tools.md#create-layer-group) — Create a group layer in the active image.
- [`move_layer_to_group`](layer_tools.md#move-layer-to-group) — Move a layer or group under a target layer group.
- [`list_channels`](layer_tools.md#list-channels) — List custom channels in the active image.
- [`save_selection_to_channel`](layer_tools.md#save-selection-to-channel) — Save the current selection mask as a named custom channel.
- [`channel_to_selection`](layer_tools.md#channel-to-selection) — Convert a custom channel into the current selection.
- [`create_visual_annotation_layer`](layer_tools.md#create-visual-annotation-layer) — Create an MCP-tagged temporary visual annotation layer.
- [`remove_visual_annotations`](layer_tools.md#remove-visual-annotations) — Remove MCP-managed annotation layers only.
- [`layer_version_stamp`](layer_tools.md#layer-version-stamp) — Attach namespaced MCP provenance metadata to a layer.
- [`add_alpha_channel`](layer_tools.md#add-alpha-channel) — Add an alpha (transparency) channel to a layer.
- [`edit_channels`](layer_tools.md#edit-channels) — Create, inspect, duplicate, rename, or convert channels/selections.
- [`manage_channels`](layer_tools.md#manage-channels) — Manage saved channels through a consolidated action tool.

### Vector Paths

- [`create_path`](path_tools.md#create-path) — Create a vector path from a flat point list.
- [`list_paths`](path_tools.md#list-paths) — List vector paths in the active image.
- [`path_to_selection`](path_tools.md#path-to-selection) — Convert a vector path to the current selection.
- [`stroke_path`](path_tools.md#stroke-path) — Stroke a vector path onto a layer using the current or supplied context.
- [`remove_path`](path_tools.md#remove-path) — Remove a vector path from the active image.
- [`edit_paths`](path_tools.md#edit-paths) — Inspect, create, transform, stroke, fill, or convert paths.
- [`create_and_edit_paths`](path_tools.md#create-and-edit-paths) — Create, list, rename, or update vector paths from typed point data.
- [`stroke_or_fill_path`](path_tools.md#stroke-or-fill-path) — Stroke or fill a vector path with supplied paint settings.

### PDB and Escape Hatch

- [`search_pdb`](pdb_tools.md#search-pdb) — Search GIMP's Procedure Database for available operations.
- [`execute_pdb_call`](pdb_tools.md#execute-pdb-call) — Validate and optionally execute an allowlisted typed PDB procedure call.
- [`execute_python`](pdb_tools.md#execute-python) — Execute raw Python code in GIMP's PyGObject console.
- [`pdb_introspect_typed`](pdb_tools.md#pdb-introspect-typed) — Return typed PDB procedure metadata for safer wrapper generation.
- [`safe_python_eval`](pdb_tools.md#safe-python-eval) — Run restricted diagnostic Python only when explicitly debug-enabled.

### Selections

- [`select_rectangle`](selection_tools.md#select-rectangle) — Create a rectangular selection.
- [`select_ellipse`](selection_tools.md#select-ellipse) — Create an elliptical selection.
- [`select_polygon`](selection_tools.md#select-polygon) — Create a polygon (freeform) selection.
- [`select_all`](selection_tools.md#select-all) — Select the entire image.
- [`select_none`](selection_tools.md#select-none) — Clear all selections.
- [`select_invert`](selection_tools.md#select-invert) — Invert the current selection (select everything NOT currently selected).
- [`select_by_color`](selection_tools.md#select-by-color) — Select all pixels similar in color to the sampled point.
- [`select_layer_alpha`](selection_tools.md#select-layer-alpha) — Select a layer's alpha channel using GIMP's image.select_item API.
- [`fuzzy_select`](selection_tools.md#fuzzy-select) — Select the connected fuzzy/magic-wand region touching a sampled point.
- [`select_color`](selection_tools.md#select-color) — Globally select pixels matching an explicit color value.
- [`feather_selection`](selection_tools.md#feather-selection) — Feather the current selection by a radius in pixels.
- [`border_selection`](selection_tools.md#border-selection) — Replace the current selection with its border.
- [`stroke_selection`](selection_tools.md#stroke-selection) — Stroke the current selection onto a layer.
- [`bucket_fill`](selection_tools.md#bucket-fill) — Bucket-fill a contiguous region from a seed point.
- [`get_selection_info`](selection_tools.md#get-selection-info) — Get information about the current selection (bounds, whether it exists).
- [`select_grow`](selection_tools.md#select-grow) — Grow the current selection by a number of pixels.
- [`select_shrink`](selection_tools.md#select-shrink) — Shrink the current selection by a number of pixels.

### Target Resolution

- [`find_similar_regions`](target_tools.md#find-similar-regions) — Find simple deterministic pixel regions matching color/alpha criteria.
- [`resolve_target`](target_tools.md#resolve-target) — Resolve a user or agent target reference into concrete GIMP object IDs.
- [`validate_targets`](target_tools.md#validate-targets) — Validate that proposed targets still exist and support required actions.

### Transforms

- [`align_and_distribute_layers`](transform_tools.md#align-and-distribute-layers) — Align or distribute layers relative to the canvas with verification bounds.
- [`scale_image`](transform_tools.md#scale-image) — Scale the entire image (all layers) to new dimensions.
- [`scale_layer`](transform_tools.md#scale-layer) — Scale a single layer to new dimensions.
- [`rotate_image`](transform_tools.md#rotate-image) — Rotate the entire image by 90, 180, or 270 degrees.
- [`rotate_layer`](transform_tools.md#rotate-layer) — Rotate a layer by an arbitrary angle.
- [`perspective_layer`](transform_tools.md#perspective-layer) — Perspective-transform a layer by remapping its four bounding-box corners.
- [`shear_layer`](transform_tools.md#shear-layer) — Shear a layer horizontally or vertically by a pixel magnitude.
- [`flip_image`](transform_tools.md#flip-image) — Flip the entire image.
- [`flip_layer`](transform_tools.md#flip-layer) — Flip a single layer.
- [`crop_to_selection`](transform_tools.md#crop-to-selection) — Crop the image to the current selection bounds.
- [`smart_crop_or_resize`](transform_tools.md#smart-crop-or-resize) — Safely crop, pad, or resize with explicit anchors and dry-run support.
- [`crop_image`](transform_tools.md#crop-image) — Crop the image to a specific rectangle.
- [`autocrop_image`](transform_tools.md#autocrop-image) — Automatically crop the image to remove border whitespace/transparency.
- [`resize_canvas`](transform_tools.md#resize-canvas) — Resize the image canvas without scaling content.
- [`offset_layer`](transform_tools.md#offset-layer) — Move a layer by an offset (reposition within the canvas).
