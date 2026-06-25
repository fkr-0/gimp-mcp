# GIMP MCP Pro

**Production-grade Model Context Protocol server for GIMP 3.0+**

> 171 typed tools • reliable communication • AI-friendly workflows

GIMP MCP Pro lets AI assistants (Claude, etc.) control GIMP through well-structured, typed MCP tools — creating images, managing layers, drawing shapes, applying filters, adjusting colors, and more.

## Features

- **171 typed MCP tools** across 15 tool modules — image management, layers, selections, vector paths, drawing/text, transforms, colors, filters, inspection/observation, target resolution, history, PDB access, repeatable flows, gimp.dev discovery, and agent workflow helpers
- **Reliable communication** — length-prefixed socket framing (no more JSON boundary guessing)
- **Persistent connections** — one TCP connection, kept alive, with automatic reconnection
- **Fresh GIMP 3.2.4 clean-profile smoke recorded** — `compat.results.yml` currently records 18 passing live checks and 0 failures for the 86-tool registry, while the public compatibility claim remains gated until the full matrix sets `claim_allowed: true`
- **Undo groups** — multi-step AI workflows as a single undo step
- **Pydantic validation** — inputs validated before reaching GIMP
- **AI guidance prompts** — best practices and iterative workflow documentation
- **Visual verification** — `get_image_bitmap` lets AI see what it's drawing
- **PDB discovery** — search GIMP's thousands of procedures
- **Escape hatch** — `execute_python` for anything without a dedicated tool

## Compatibility status

```yaml
gimp_3_2_4:
  status: static-contract-pass-live-claim-blocked
  contract: compat.yml
  latest_live_results: compat.results.yml
  static_registered_tools: 169
  live_results_status: partial-failed-smoke
  clean_profile_required: true
  xvfb_supported: true
  claim_allowed: false
```

This branch keeps the public compatibility claim deliberately conservative. Static contract validation, generated documentation, and offline tool registry tests now track 169 public MCP tools. The release claim is still not enabled because `compat.results.yml` remains partial/non-claiming with `claim_allowed: false`; run the full clean-profile GIMP 3.2.4 live matrix before publishing verified support. See `docs/gimp-3.2.4-compat.md` for the runbook.

For practical agent prompts and step-by-step editing patterns, see `docs/agent-workflows.md`.

## Architecture

```
AI Assistant  ←→  MCP Server (gimp-mcp-pro)  ←→  GIMP Plugin
   (Claude)         stdio/SSE                      TCP socket
                    Typed tools                    PyGObject
                    Pydantic models                Native handlers
```

Two processes: the MCP server runs outside GIMP and communicates with a plugin running inside GIMP's Python process via TCP with length-prefixed framing.

The MCP server registers all 171 tools as async coroutine handlers and uses the asyncio-native `AsyncGimpBridge` for tool execution. The synchronous `GimpBridge` remains available for CLI diagnostics, the REPL, and legacy callers. See `docs/async-tool-architecture.md` for the async contract and regression checks.

## Project tooling

This fork uses **uv** as the only Python dependency and command runner.

```bash
uv sync --extra dev
uv run python scripts/project.py list
uv run python scripts/project.py check
```

Common commands:

```bash
uv run pytest                 # full test suite with coverage
uv run pytest --no-cov        # fast local test loop
uv run ruff check .           # lint
uv run ruff format .          # format
uv run mypy                   # type-check package
uv run gimp-mcp-pro config --json
uv run gimp-mcp-pro doctor
uv run pytest --no-cov tests/test_async_tool_registry.py
```

Runtime configuration is loaded with `pydantic-settings` from environment variables and a local `.env` file. Copy `.env.example` to `.env` for local overrides. New variable names use the `GIMP_MCP_PRO_` prefix; legacy `GIMP_MCP_` names are still accepted where possible.

Useful CLI commands:

```bash
gimp-mcp-pro serve            # run the MCP server
gimp-mcp-pro config --json    # inspect resolved settings
gimp-mcp-pro doctor --connect # verify socket connectivity to the GIMP plugin
gimp-mcp-pro repl             # interactive bridge REPL for a live plugin
gimp-mcp-pro flow list        # list declarative repeatable flows
```

Repeatable Flows can be proposed and validated through MCP, run through the CLI, and pinned under **Filters → Repeatable Flows**. See [docs/repeatable-flows.md](repeatable-flows.md).

## Quick Start

### 1. Install the MCP server

```bash
pip install gimp-mcp-pro
```

Or install from source:

```bash
git clone https://github.com/yourname/gimp-mcp-pro.git
cd gimp-mcp-pro
pip install -e .
```

### 2. Install the GIMP plugin

The setup script handles this automatically:

```bash
./setup.sh
```

Or manually copy the plugin:

```bash
# Linux
PLUG_DIR="$HOME/.config/GIMP/3.0/plug-ins/gimp_mcp_plugin"
mkdir -p "$PLUG_DIR"
cp gimp_plugin/gimp_mcp_plugin.py "$PLUG_DIR/gimp_mcp_plugin.py"
chmod +x "$PLUG_DIR/gimp_mcp_plugin.py"

# macOS
PLUG_DIR="$HOME/Library/Application Support/GIMP/3.0/plug-ins/gimp_mcp_plugin"
mkdir -p "$PLUG_DIR"
cp gimp_plugin/gimp_mcp_plugin.py "$PLUG_DIR/gimp_mcp_plugin.py"
chmod +x "$PLUG_DIR/gimp_mcp_plugin.py"
```

### 3. Start the plugin in GIMP

Open GIMP → **Tools** → **Start MCP Pro Server**

You should see "MCP Pro: Listening on localhost:9877" in the GIMP console.

### 4. Configure Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gimp": {
      "command": "gimp-mcp-pro"
    }
  }
}
```

Restart Claude Desktop.

### 5. Start editing!

Ask Claude: *"Create an 800x600 image with a red circle in the center and the text 'Hello World' below it"*

## Tool Reference

### Image Management (171 tools)
| Tool | Description |
|------|-------------|
| `create_image` | Create a new blank image |
| `list_images` | List all open images |
| `get_image_info` | Get active image metadata |
| `export_image` | Export as PNG, JPEG, TIFF, BMP, WebP |
| `flatten_image` | Flatten all layers into one |
| `duplicate_image` | Duplicate entire image |

### Layer Operations (171 tools)
| Tool | Description |
|------|-------------|
| `create_layer` | Create a new layer |
| `list_layers` | List all layers with properties |
| `set_active_layer` | Switch working layer |
| `delete_layer` | Delete a layer |
| `set_layer_opacity` | Change layer opacity (0-100) |
| `set_layer_visibility` | Show or hide a layer |
| `duplicate_layer` | Duplicate a layer |
| `merge_visible_layers` | Merge all visible layers |
| `add_alpha_channel` | Add transparency support to a layer |

### Drawing (171 tools)
| Tool | Description |
|------|-------------|
| `set_foreground_color` | Set drawing color |
| `set_background_color` | Set background color |
| `fill_selection` | Fill current selection with color |
| `draw_line` | Draw a straight line |
| `draw_brush_stroke` | Pencil or brush stroke along points |
| `draw_rectangle` | Rectangle (filled or outline) |
| `draw_ellipse` | Ellipse/circle (filled or outline) |
| `draw_polygon` | Polygon (filled or outline) |
| `add_text` | Add a text layer with font/size/color |
| `edit_clear` | Clear the current selection area to transparency |

### Selections (171 tools)
| Tool | Description |
|------|-------------|
| `select_rectangle` | Rectangular selection |
| `select_ellipse` | Elliptical/circular selection |
| `select_polygon` | Freeform polygon selection |
| `select_all` | Select entire image |
| `select_none` | Clear all selections |
| `select_invert` | Invert current selection |
| `select_grow` | Expand selection by pixels |
| `select_shrink` | Shrink selection by pixels |

### Transforms (171 tools)
| Tool | Description |
|------|-------------|
| `scale_image` | Scale entire image |
| `scale_layer` | Scale a single layer |
| `rotate_image` | Rotate image 90°/180°/270° |
| `rotate_layer` | Rotate layer by arbitrary angle |
| `flip_image` | Flip image horizontal/vertical |
| `flip_layer` | Flip layer horizontal/vertical |
| `crop_image` | Crop to specific rectangle |
| `crop_to_selection` | Crop to selection bounds |
| `autocrop_image` | Auto-trim unused canvas |
| `resize_canvas` | Resize canvas without scaling content |
| `offset_layer` | Move layer position on canvas |

### Color Adjustments (171 tools)
| Tool | Description |
|------|-------------|
| `adjust_brightness_contrast` | Brightness and contrast |
| `adjust_hue_saturation` | Hue, saturation, and lightness |
| `adjust_levels` | Input/output levels with gamma |
| `adjust_curves` | Custom tone curves |
| `desaturate` | Convert to grayscale (multiple methods) |
| `invert_colors` | Negative/invert effect |
| `apply_threshold` | Convert to pure black and white |
| `posterize` | Reduce color levels |
| `color_to_alpha` | Make a color transparent |
| `auto_white_balance` | Automatic levels stretch |
| `get_colors` | Get current foreground/background colors |
| `swap_colors` | Swap foreground and background |
| `sample_color` | Pick color from pixel |

### Filters & Effects (171 tools)
| Tool | Description |
|------|-------------|
| `apply_gaussian_blur` | Gaussian blur |
| `apply_unsharp_mask` | Sharpen with unsharp mask |
| `apply_pixelize` | Pixelization/mosaic effect |
| `apply_edge_detect` | Edge detection (Sobel, Prewitt, Laplace) |
| `apply_emboss` | Emboss/relief effect |
| `apply_noise` | Add random noise/grain |
| `apply_median` | Median denoise filter |
| `apply_drop_shadow` | Drop shadow effect |

### Inspection (171 tools)
| Tool | Description |
|------|-------------|
| `get_image_bitmap` | Get image as viewable PNG (for AI verification) |
| `get_image_metadata` | Fast metadata without pixel data |
| `get_context_state` | Current colors, brush, opacity settings |
| `get_gimp_info` | GIMP version, environment, capabilities |

### History (171 tools)
| Tool | Description |
|------|-------------|
| `undo` | Undo previous operation(s) where GIMP exposes the operation |
| `redo` | Redo previously undone operation(s) where GIMP exposes the operation |
| `begin_undo_group` | Group operations as a single undo step |
| `end_undo_group` | End current undo group |

### Advanced (171 tools)
| Tool | Description |
|------|-------------|
| `search_pdb` | Search GIMP's procedure database |
| `execute_python` | Run raw Python in GIMP's console |

## Known Limitations

- **Undo/Redo**: Undo/redo behavior must be confirmed during live GIMP 3.2.4 compatibility verification. Undo *groups* work for grouping AI operations when supported by the active image context.
- **Drop Shadow**: Uses Script-Fu internally; may cause connection issues on some setups.
- **Font Names**: GIMP 3.0 uses names like `Sans-serif`, `Serif`, `Monospace`. The `add_text` tool maps common aliases automatically.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GIMP_MCP_HOST` | `localhost` | GIMP plugin socket host |
| `GIMP_MCP_PORT` | `9877` | GIMP plugin socket port |
| `GIMP_MCP_TIMEOUT` | `30` | Default command timeout (seconds) |
| `GIMP_MCP_LOG_LEVEL` | `INFO` | Logging level |
| `GIMP_MCP_DEBUG` | `false` | Enable debug mode |

## Technical Notes

### Filter Implementation
All filters use `Gimp.DrawableFilter` which safely wraps GEGL operations within GIMP's plugin context. Direct GEGL graph construction (`Gegl.Node()`) crashes in GIMP 3.0 plugin context — this is a known limitation that GIMP MCP Pro works around.

### Color Handling
Colors are accepted as names (`"red"`), hex (`"#FF0000"`), or CSS rgb (`"rgb(255,0,0)"`) across all tools. Internally, colors use Gegl.Color objects with the GIMP 3.0 API.

### Connection Protocol
The MCP server communicates with the GIMP plugin over TCP using 4-byte big-endian length-prefixed JSON messages. This eliminates the fragile JSON boundary detection used by earlier implementations.

## Development

```bash
git clone https://github.com/yourname/gimp-mcp-pro.git
cd gimp-mcp-pro
pip install -e ".[dev]"
pytest
```

## Credits

Built on insights from:
- [maorcc/gimp-mcp](https://github.com/maorcc/gimp-mcp) — proven GIMP plugin architecture, AI guidance prompts
- [slliws/gimp-mcp-server](https://github.com/slliws/gimp-mcp-server) — typed tool module structure
- [libreearth/gimp-mcp](https://github.com/libreearth/gimp-mcp) — original proof-of-concept

## License

MIT
