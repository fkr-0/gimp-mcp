# Future MCP Tool Roadmap

This planning page tracks candidate MCP tools that are **not** part of the verified runtime registry yet. The verified GIMP 3.2.4 compatibility contract remains `compat.yml` with 86 implemented tools. Future candidates live in `features.yml` until they have implementation, unit tests, live Xvfb coverage, and documentation.

## Why this roadmap exists

The current tool surface is broad enough for image, layer, selection, drawing, transform, color, filter, inspection, history, and PDB operations. The next wave should make agent operation safer and more precise rather than simply adding more one-off wrappers.

The main direction is:

- observe document state before editing;
- resolve targets by stable IDs instead of ambiguous names;
- wrap destructive edits in transactions;
- verify visual deltas after edits;
- expose assets and resources with bounded, structured metadata;
- keep generic scripting paths inspectable and reversible.

## Candidate count

`features.yml` currently tracks **57** candidate tools/features grouped into seven categories:

- `observe`
- `target`
- `transaction`
- `edit`
- `verify`
- `asset`
- `script`

The most recent additions are `FEAT-046` through `FEAT-057`, which cover layer masks, channels, guides/grid, paths, text-layer metadata/editing, resource catalogs, active paint resources, generic allow-listed GEGL operations, GEGL previews, and color-management profile support.

## Implementation waves

The first wave should stay focused on safety and observability:

- `observe_document_state`
- `get_layer_tree_detailed`
- `observe_region`
- `resolve_target`
- `validate_targets`
- `begin_edit_transaction`
- `end_edit_transaction`
- `rollback_transaction`
- `session_capabilities`

Later waves can add higher-level editing and asset workflows after the transaction and verification primitives are reliable.

## Runtime evidence that informed new candidates

A clean-profile GIMP 3.2.4 runtime probe under Xvfb confirmed `Gimp.DrawableFilter.operation_get_available()` exposes many GEGL operations beyond the current bespoke filter wrappers. Examples observed locally include:

- `gegl:brightness-contrast`
- `gimp:curves`
- `gimp:desaturate`
- `gegl:color-to-alpha`
- `gegl:noise-hsv`
- `gegl:median-blur`
- `gegl:cubism`
- `gegl:displace`

That makes an allow-listed `apply_gegl_operation` candidate useful, but it should not bypass validation. The implementation must check operation availability, accepted properties, target type, bounded preview output, and undo/rollback behavior.

## Promotion rule

A candidate can move from `features.yml` into the verified MCP registry only when it has:

1. typed input and output models;
2. fast fake-bridge unit coverage;
3. structured bridge-error coverage;
4. clean-profile Xvfb live coverage;
5. docs generated into the tool reference;
6. `compat.yml` registry and scenario updates.

Until then, `compat.yml` and `tools.yml` should treat it as planning metadata, not a public compatibility claim.
