# Agent Editing Workflows

This page shows practical ways to use GIMP MCP Pro with an agent. The examples assume that GIMP 3.2.4 is running with the MCP plug-in bridge and that the MCP client can call the tools listed in the generated tool reference.

## General operating loop

Use the same loop for almost every image-editing task:

1. Observe the document with `session_capabilities`, `observe_document_state`, `get_layer_tree_detailed`, and `get_image_bitmap`.
2. Resolve and validate targets with `resolve_target` and `validate_targets` before mutation.
3. Start an edit transaction with `begin_edit_transaction` for multi-step work.
4. Make a small batch of changes.
5. Inspect the result with `observe_region`, `sample_color`, or `get_image_bitmap`.
6. Commit with `end_edit_transaction`, or call `rollback_transaction` if the visual result is wrong.

A useful agent prompt is:

> First inspect the current GIMP document and layer tree. Do not edit anything until you have identified the active image, active layer, visible layers, and whether the target layer is editable. After every three to five operations, call `get_image_bitmap` or `observe_region` and explain what changed.

## Workflow: create a clean layered drawing

Goal: create a simple icon, poster, or abstract drawing with separate editable layers.

Recommended tools:

- `create_image`
- `create_layer`
- `set_active_layer`
- `draw_polygon`, `draw_rectangle`, `draw_ellipse`, `draw_line`
- `fill_selection`, `select_none`
- `set_layer_opacity`, `set_layer_visibility`
- `get_image_bitmap`

Prompt template:

> Create a 1024×1024 RGB image with a transparent-safe layered structure. Use one background layer, one geometric shape layer, one accent line layer, and one text or label layer. Use undo transactions. After each phase, inspect the bitmap and keep layer names descriptive.

Good agent behavior:

- Create all major layers first.
- Use selections plus fill for clean solid shapes.
- Avoid painting everything onto the active layer.
- Keep corrections on the layer that owns the problematic shape.
- Export only after a final visual check.

## Workflow: sprite sheet planning with gimp.dev

The optional `gimp.dev` integration currently exposes read-only status and plug-in catalog discovery through:

- `gimp_dev_status`
- `gimp_dev_plugin_catalog`

These tools do not install plug-ins, start GIMP, or mutate a profile. They let an agent inspect whether local gimp.dev sprite procedures are available as future capability providers.

Prompt template:

> Check whether `gimp.dev` is available. Load the gimp.dev plug-in catalog and tell me which sprite tools are pure planning helpers, which ones write files, and which ones would require a live GIMP transaction before use.

Recommended next implementation path:

1. Use `gimp_dev_plugin_catalog` to discover sprite procedures.
2. Prefer pure planners such as sprite sheet, onion skin, and clip-plan commands before live mutation.
3. Treat background removal and PNG export as transaction-wrapped live operations once typed PDB procedure calls are implemented.

## Workflow: remove or soften a background

There are two levels of background-removal work.

For simple flat-color backgrounds, use current MCP tools:

1. Observe with `get_image_bitmap` and `sample_color` near the background.
2. Select or isolate the background using threshold/color tools where appropriate.
3. Use `color_to_alpha`, `apply_threshold`, or layer/selection operations.
4. Validate the edge region with `observe_region`.
5. Keep the original layer hidden but preserved.

Prompt template:

> Remove the flat background from the active layer, but preserve the original layer. First sample representative background pixels, then create a duplicate working layer, apply a reversible edit sequence, and inspect the object edges before committing.

For gimp.dev sprite background removal, do not call it blindly. The catalog marks it as a live mutating procedure. It should be exposed later only through a typed adapter that validates arguments, validates the target layer, and wraps the operation in an edit transaction.

## Workflow: decompose an image into color or line-study layers

This is useful for painting studies, posterization, and line-art extraction.

Recommended tools:

- `duplicate_image` or `duplicate_layer`
- `posterize`
- `desaturate`
- `apply_threshold`
- `apply_edge_detect`
- `adjust_levels`
- `get_colors`
- `sample_color`
- `create_layer`
- `set_layer_opacity`

Prompt template:

> Build a non-destructive study file from the current image. Duplicate the image or active layer. Create separate layers for dominant color blocks, high-contrast line detection, and a simplified grayscale value map. Use `posterize`, `desaturate`, `threshold`, and `edge_detect`. After each derived layer, inspect the bitmap and summarize what the layer is useful for.

Recommended layer structure:

- `original-reference`: hidden or locked reference layer.
- `posterized-color-map`: reduced palette version.
- `value-study`: grayscale contrast version.
- `line-detection`: edge or threshold linework.
- `notes`: optional labels or text annotations.

## Workflow: sophisticated line detection before manual drawing

For line detection and drawing assistance, the agent should work in phases rather than applying one destructive filter:

1. Duplicate the source layer.
2. Desaturate the duplicate.
3. Adjust levels to increase contrast.
4. Apply edge detection or threshold.
5. Inspect the result at full image and region level.
6. Reduce opacity and place it above or below the original as a guide layer.

Prompt template:

> Create a line-detection guide layer from the active image. Preserve the original. Try a grayscale + levels + edge-detect pipeline, inspect the result, then tune threshold/opacity until it can serve as a drawing guide. Do not flatten the image.

## Workflow: safe export

Export should be the last step, not part of exploratory editing.

Recommended tools:

- `get_image_info`
- `list_layers`
- `merge_visible_layers` only when explicitly requested
- `export_image`

Prompt template:

> Before exporting, inspect the image dimensions, visible layers, and active layer. Confirm the export format and path. Do not merge or flatten unless I explicitly ask. Export a PNG and report the final path and dimensions.

## Common mistakes to prevent in prompts

Tell the agent explicitly:

- Do not use raw `execute_python` unless a typed MCP tool cannot do the job.
- Do not edit before observing the document state.
- Do not assume layer names or indexes; resolve and validate them.
- Do not flatten or merge as a cleanup step unless requested.
- Do not run profile-mutating gimp.dev commands from MCP.
- Do not use live optional plug-ins unless the capability probe proves they exist.
