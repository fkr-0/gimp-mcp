# Repeatable Flows Design

## Goal

Turn successful agent-authored GIMP workflows into reviewable, declarative, reusable commands. Active flows can run from MCP clients or directly from GIMP under `Filters > Repeatable Flows`, without requiring an active Codex or Claude session.

## User Experience

GIMP uses a hybrid interface:

- Pinned flows appear directly under `Filters > Repeatable Flows`.
- `Browse All Flows` opens a searchable catalog with status and capability tags.
- `Manage Flows` supports validation, activation, pinning, trust, and removal.
- Parameterless flows run after confirmation.
- Parameterized flows open a generated dialog.
- The default final checkpoint presents before/after previews and `Commit`, `Rollback`, and `Keep Open` actions.

## Architecture

### Automatic GIMP Extension

A no-argument persistent GIMP procedure starts automatically with GIMP. It starts the existing framed TCP bridge, loads active flow metadata, and registers temporary procedures for pinned flows plus `Browse All Flows` and `Manage Flows`.

The extension generates parameter dialogs from flow schemas. Confirmed runs launch the local runner asynchronously so the GIMP main loop remains responsive.

### Shared Local Runner

The package adds:

```text
gimp-mcp-pro flow run <flow-id> --params-json <json>
```

The runner loads and validates the flow, connects to the GIMP bridge, resolves live bindings, and executes the same typed operation layer used by MCP tools. It does not require an active agent client.

Tool implementation must be exposed through a reusable operation registry so MCP registration and local flow execution do not duplicate behavior.

### MCP Management Surface

The MCP server exposes:

- `propose_flow`
- `list_flows`
- `get_flow`
- `validate_flow`
- `activate_flow`
- `deactivate_flow`
- `pin_flow`
- `unpin_flow`
- `run_flow`

Agents may create drafts but never silently activate, trust, or pin them.

Recording manual or mixed human-agent sessions is explicitly deferred.

## Storage And Schema

User flows live at:

```text
~/.config/gimp-mcp-pro/flows/<flow-id>.flow.json
```

JSON keeps the files portable and readable by GIMP's system Python without adding a YAML dependency.

Each flow contains:

- `schema_version`
- stable `id`, title, description, and author metadata
- `draft`, `validated`, or `active` lifecycle state
- parameter schema
- linear typed MCP steps
- optional simple `when` conditions
- transaction phase definitions
- review checkpoint policy
- inferred capability tags
- UI metadata for category, ordering, and pinning
- content hash used for trust decisions

V1 does not provide loops or a general expression language.

## Parameters And Bindings

Primitive parameter types are text, integer, number, boolean, color, and fixed choice.

Semantic parameter types include:

- open image
- layer
- channel
- path
- brush
- font
- palette
- gradient
- installed filter or PDB procedure
- export format
- rectangle, point, dimensions, opacity, and angle

Resource choices populate from the live GIMP session when the dialog opens. The selection stores a stable runtime ID where GIMP provides one and a human-readable name as fallback. Bindings are validated again immediately before execution.

Steps reference parameters using `${parameter_name}`. V1 conditions may only compare declared boolean or fixed-choice parameters.

## Execution

The default review policy is `final`. Supported policies are:

- `none`: commit after successful execution
- `final`: pause before final commit
- `phased`: pause at named transaction boundaries

Flows execute inside one undo transaction by default. Advanced flows may declare multiple transaction phases. Failure rolls back the active phase and stops execution.

Each run produces a structured log containing resolved bindings, step inputs, durations, results, checkpoint decisions, rollback status, and errors.

## Safety

Typed MCP tools are preferred but not mandatory. `execute_python` and arbitrary PDB operations remain valid step types and automatically add visible `arbitrary-code` or `pdb` capability tags.

Unsafe flows require confirmation before activation and before each run unless trusted. Trust binds to the flow content hash; any edit invalidates it. Filesystem-writing flows display resolved destinations before execution.

## Validation

Static validation checks schema version, tool existence, argument names and types, parameter references, condition syntax, transaction structure, checkpoint structure, and capability tags.

Runtime validation checks GIMP connectivity, session capabilities, semantic resource bindings, target editability, and output destinations.

Activation requires successful static validation. A test run is recommended but not required for safe typed flows; arbitrary-code flows require a successful test run before activation.

## Testing

Coverage includes:

- schema parsing and migration rejection
- parameter substitution and semantic binding
- condition evaluation
- capability inference and trust invalidation
- lifecycle transitions
- transaction commit and rollback
- final and phased checkpoints
- operation-registry parity between MCP and local runner
- CLI execution against a fake bridge
- generated GIMP procedures and dialogs
- automatic extension lifecycle
- focused live GIMP tests for a safe pinned flow

## Out Of Scope

- automatic recording of agent or human actions
- loops and arbitrary expression evaluation
- remote flow marketplaces
- silent activation or trust by agents
- duplicating MCP tool implementations inside the GIMP plugin
