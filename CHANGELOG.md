# Changelog

## 0.3.0 (2026-07-17)

### Async high-level operations

- Added the session-scoped `list_checkpoints`, `restore_checkpoint`, and
  `discard_checkpoint` workflow tools, bringing the registry to 186 fully async
  MCP tools.
- Made checkpoint restoration deliberately non-destructive: saved state opens
  as a new GIMP document instead of replacing the active image.
- Added path-redacted checkpoint listings and controlled temporary-file cleanup.

### Fixes and implementation gaps

- Fixed `create_checkpoint(include_xcf_copy=true)` so it writes a real XCF with
  `Gimp.file_save`; the previous implementation duplicated and deleted an image
  without persisting the checkpoint.
- Unified checkpoint IDs across the MCP response, session index, generated GIMP
  code, and XCF filename.
- Removed the hard-coded `/tmp` assumption and now use the host temporary
  directory consistently on both sides of the bridge.
- Ensured temporary duplicate image references are released after saving.

### Testing and compatibility

- Added focused lifecycle tests covering create, list, restore, discard, path
  redaction, metadata-only checkpoints, and duplicate-image cleanup.
- Extended the invocation and generated-code matrices to cover the complete
  186-tool async registry.
- Added a clean-profile Xvfb GIMP 3.2.4 E2E flow for checkpoint creation, XCF
  save, reopening as a new document, and deletion.
- Recorded a verified 24/24 compatibility run with zero failures and
  `claim_allowed: true`.

### Documentation and release

- Regenerated the complete tool reference and docstring audit for 186 tools.
- Updated README, compatibility contracts, roadmap/risk review counts, and live
  compatibility evidence.
- Built and validated the strict MkDocs site, source distribution, and wheel.

## 0.2.0 (2026-07-17)

### Checkpoint lifecycle

- Added async `list_checkpoints`, `restore_checkpoint`, and `discard_checkpoint` workflow tools.
- `create_checkpoint(include_xcf_copy=true)` now writes a real temporary XCF using GIMP's file API.
- Restores are deliberately non-destructive: a checkpoint is opened as a new document rather than replacing the active image.
- Fixed checkpoint IDs so the MCP response, in-memory index, and generated XCF refer to the same checkpoint.

### Release quality

- Updated the public tool count to 186 and the package version to 0.2.0.

## 0.1.0 (2026-02-12)

Initial release — 67 typed MCP tools for GIMP 3.0+.

### Tools
- **Image Management** (6): create, list, info, export (PNG/JPEG), flatten, duplicate
- **Layer Operations** (9): create, list, activate, delete, opacity, visibility, duplicate, merge, alpha
- **Drawing** (9): foreground/background color, fill, line, brush stroke, rectangle, ellipse, polygon, text
- **Selections** (8): rectangle, ellipse, polygon, all, none, invert, grow, shrink
- **Transforms** (11): scale image/layer, rotate image/layer, flip image/layer, crop, crop-to-selection, autocrop, resize canvas, offset layer
- **Color Adjustments** (13): brightness/contrast, hue/saturation, levels, curves, desaturate, invert, threshold, posterize, color-to-alpha, auto white balance, get/swap/sample colors
- **Filters** (8): gaussian blur, unsharp mask, pixelize, edge detect, emboss, noise, median, drop shadow
- **Inspection** (4): bitmap capture, metadata, context state, GIMP info
- **History** (3): undo groups (begin/end), edit clear
- **Advanced** (2): PDB search, execute Python

### Architecture
- Length-prefixed TCP framing for reliable communication
- Persistent connections with automatic reconnection
- Pydantic model validation
- Two-process design (MCP server ↔ GIMP plugin)

### GIMP 3.0 Compatibility
- DrawableFilter API for all filters (avoids GEGL graph crashes)
- Correct Gegl.Color RGBA extraction (.red/.green/.blue/.alpha)
- Font object resolution with alias mapping (Sans → Sans-serif)
- Unit.pixel() for text layer creation
- ResultTuple handling for Selection.bounds()
- PDB procedure-based export (file-png-export, file-jpeg-export)
