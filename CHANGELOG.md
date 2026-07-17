# Changelog

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
