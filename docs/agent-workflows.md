# Agent workflows and prompt cookbook

This guide shows how to use GIMP MCP Pro as an agent-facing editing surface. The safest pattern is: inspect the session, resolve targets, validate targets, group the edit, perform the mutation, observe the result, and either commit or roll back.

## Core operating loop

1. Call `session_capabilities` to learn the active GIMP version, plug-in version, available procedures, export support, and safety mode.
2. Call `observe_document_state` to get the active image, selection, layer IDs, active layer, dimensions, and context.
3. Call `get_layer_tree_detailed` when a task touches layers, masks, groups, opacity, visibility, or text.
4. Call `resolve_target` for human references such as "the logo layer", "background", "top text", or "layer 3".
5. Call `validate_targets` immediately before a destructive edit. Require at least `visible` and `editable`; require `raster` for pixel operations.
6. Start `begin_edit_transaction` for multi-step edits. Use the transaction ID in your notes.
7. Apply edits with the focused tool family: selections, drawing, transforms, colors, filters, layers, history, or PDB.
8. Call `observe_region` or `get_image_bitmap` to inspect the result visually.
9. Use `end_edit_transaction` if the result matches the intent, or `rollback_transaction` if it does not.
10. Export only after a final observation pass.

## Example prompt: remove or soften a background

```text
Use the active image in GIMP. First inspect the document and layer tree. Resolve the subject and background layers. If there is only one layer, duplicate it before destructive work. Select the background conservatively, refine the selection by growing or shrinking only when needed, clear or color-to-alpha the background, and inspect the subject edge at high zoom using observe_region. Use an edit transaction and roll back if the foreground edge is damaged. Export a PNG with transparency when finished.
```

Recommended tool flow:

- `session_capabilities`
- `observe_document_state`
- `get_layer_tree_detailed`
- `resolve_target` with `query="background"`
- `validate_targets` with `required_capabilities=["visible", "editable", "raster"]`
- `begin_edit_transaction`
- `duplicate_layer`, `select_rectangle` / `select_polygon` / `color_to_alpha` / `edit_clear`
- `observe_region` around critical edges
- `end_edit_transaction` or `rollback_transaction`
- `export_image`

## Example prompt: create a small sprite sheet

```text
Create a 4 by 4 sprite sheet on the active or new image. Use transparent background, consistent cell size, and separate layers for sketch, ink, shadow, color, and highlights. Draw a simple walking character with readable silhouettes. After every row, observe the whole image and one representative cell. Keep all generated layers named clearly.
```

Recommended tool flow:

- `create_image` for a new canvas, or `observe_document_state` for an existing one
- `create_layer` for `grid`, `sketch`, `ink`, `base_color`, `shadow`, `highlight`
- `draw_line`, `draw_rectangle`, `draw_ellipse`, `draw_polygon`, `fill_selection`
- `duplicate_layer` for repeated animation structure
- `observe_region` for one sprite cell
- `get_image_bitmap` before export
- `export_image`

Practical tips:

- Ask the agent to maintain a strict layer naming scheme like `sprite-00-ink`.
- Use `resize_canvas` only before drawing begins.
- Use `begin_edit_transaction` per row rather than for the entire sprite sheet, so rollback is cheap.

## Example prompt: create a drawing from a reference image

```text
Turn the active image into a clean drawing guide. Preserve the original layer. Create a new layer stack for grayscale study, line emphasis, simplified color blocks, and annotation marks. Use non-destructive duplicates where possible. Inspect the output at full image scale and in two important regions before exporting.
```

Recommended tool flow:

- `observe_document_state`
- `get_layer_tree_detailed`
- `duplicate_image` or `duplicate_layer`
- `desaturate`
- `adjust_levels`
- `apply_threshold`
- `apply_edge_detect`
- `create_layer` for annotations
- `draw_line`, `draw_polygon`, `add_text`
- `get_image_bitmap`
- `export_image`

## Example prompt: decompose an image into color and line layers

```text
Analyze the active image as material for a painter. Build a layer stack that separates dark linework, major color families, highlights, and shadow masses. Use posterization and thresholding to simplify the source. Name every generated layer after its role and color family. Do not overwrite the original layer. Verify the result by observing the full image and several representative regions.
```

Recommended tool flow:

- `session_capabilities`
- `observe_document_state`
- `duplicate_layer` for protected source copies
- `posterize` to reduce color families
- `adjust_curves` or `adjust_levels` to isolate value ranges
- `apply_threshold` for line or dark mass extraction
- `select_rectangle` / `select_polygon` for manual region isolation
- `fill_selection` on named layers for simplified color fields
- `observe_region` for important areas
- `get_image_bitmap` for final review

## Example prompt: controlled retouching with rollback

```text
Retouch only the selected area. Before changing anything, inspect the active document, validate that the selected layer is visible and editable, and begin an edit transaction. Make the smallest possible changes, observe the selected region, and roll back if the edit changes outside the selection or damages detail.
```

Recommended tool flow:

- `observe_document_state`
- `resolve_target` for the intended layer
- `validate_targets` with `visible`, `editable`, `raster`
- `begin_edit_transaction`
- selected edit tools such as `apply_median`, `apply_gaussian_blur`, `adjust_brightness_contrast`, or `draw_brush_stroke`
- `observe_region`
- `end_edit_transaction` or `rollback_transaction`

## Prompt contract for autonomous agents

A reliable agent prompt should state:

- the desired visual result;
- whether destructive edits are allowed;
- the maximum number of edit attempts;
- when to call observation tools;
- whether rollback is required on mismatch;
- the export format and path;
- layer naming expectations.

Reusable prompt skeleton:

```text
Use GIMP MCP Pro on the active document. Do not assume layer names or image dimensions. First call session_capabilities, observe_document_state, and get_layer_tree_detailed. Resolve and validate all targets before editing. Use begin_edit_transaction for each coherent edit phase. After each phase, inspect with observe_region or get_image_bitmap. Commit only when the observation matches the goal; otherwise roll back and try a simpler edit. Keep a short log of tools used and export the final image as requested.
```
