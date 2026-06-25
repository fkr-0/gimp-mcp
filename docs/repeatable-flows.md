# Repeatable Flows

Repeatable Flows turn a reviewed sequence of typed GIMP MCP operations into a reusable command. Flow files are stored as JSON under `~/.config/gimp-mcp-pro/flows/` and can be proposed by agents without being silently activated.

## Lifecycle

1. `propose_flow` validates the schema and saves a draft.
2. `validate_flow` checks tool names and argument names against the runtime registry.
3. `activate_flow` explicitly enables a validated flow.
4. `pin_flow` exposes an active flow under **Filters → Repeatable Flows** after GIMP refreshes its plug-in procedures.
5. `run_flow` or `gimp-mcp-pro flow run` executes it inside undo transactions.

The GIMP submenu also provides **Browse All Flows** and **Manage Flows**. The browser searches IDs, titles, and descriptions and shows lifecycle/capability details. Management can activate or deactivate validated flows and toggle pinning; draft validation remains an MCP/CLI operation because it requires the full typed operation registry.

Unsafe operations are allowed but tagged. `execute_python` adds `arbitrary-code`; PDB operations add `pdb`; exports add `filesystem-write`. Unsafe flows require explicit confirmation unless their exact content hash is trusted.

## Example

```json
{
  "schema_version": 1,
  "id": "prepare-product-image",
  "title": "Prepare Product Image",
  "state": "draft",
  "parameters": [
    {"name": "width", "type": "integer", "default": 1600, "minimum": 1},
    {"name": "sharpen", "type": "boolean", "default": true}
  ],
  "phases": [
    {
      "id": "resize",
      "steps": [
        {"tool": "scale_image", "arguments": {"width": "${width}", "height": 900}},
        {"tool": "apply_unsharp_mask", "arguments": {}, "when": "${sharpen}"}
      ]
    }
  ],
  "review_policy": "final",
  "ui": {"pinned": false, "category": "Repeatable Flows", "order": 100}
}
```

## CLI

```bash
gimp-mcp-pro flow list
gimp-mcp-pro flow show prepare-product-image
gimp-mcp-pro flow validate prepare-product-image
gimp-mcp-pro flow run prepare-product-image \
  --params-json '{"width": 1200, "sharpen": true}'
```

The GIMP plug-in reads `~/.config/gimp-mcp-pro/runner.json` to locate the runner. Its shape is an argv array, never a shell command:

```json
{
  "argv": ["uv", "--directory", "/path/to/gimp-mcp", "run", "gimp-mcp-pro"]
}
```

## Parameters

Primitive dialog types are text, integer, number, boolean, color, and fixed choice. Semantic types include images, layers, channels, paths, brushes, fonts, palettes, gradients, filters, procedures, and export formats. The current GIMP procedure UI represents semantic values as live-resolved string or ID fields and validates them again when the operation executes.

## Transactions And Review

Each phase starts an edit transaction. Successful phases commit; a failed step rolls back its active phase and returns a structured log. Review policies are `none`, `final`, and `phased`. The runner records the declared review decision in its output so GIMP and MCP clients can present an explicit commit or rollback choice.

Pinned flows with `review_policy: "final"` capture before/after previews. After the asynchronous runner exits successfully, GIMP presents **Commit**, **Rollback**, and **Keep Open**. Rollback applies one grouped undo per declared flow phase.
