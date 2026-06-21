# Target Resolution

Source module: `src/gimp_mcp_pro/tools/target_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`resolve_target`](#resolve-target) | Resolve a user or agent target reference into concrete GIMP object IDs. | 3 |
| [`validate_targets`](#validate-targets) | Validate that proposed targets still exist and support required actions. | 2 |

## `resolve_target` {#resolve-target}

Source: `src/gimp_mcp_pro/tools/target_tools.py:171`

```python
async def resolve_target(query: str, target_types: list[str] | None = None, require_unique: bool = False) -> ToolResult
```

**Parameters**

- `query`
- `target_types`
- `require_unique`

**Docstring**

Resolve a user or agent target reference into concrete GIMP object IDs.

Notes:
    This read-only tool prevents silent guesses. It searches images, layers,
    channels, and paths by name, stable ID, type, visibility hints, and index
    text, then reports ambiguity when no single target can be selected safely.

Args:
    query: Natural-language or structured target reference such as a name or ID.
    target_types: Optional target kinds to search: image, layer, channel, path.
    require_unique: Fail the tool call if the query does not resolve to one target.

Returns:
    Operation result with matches, selected target when unique, and ambiguity metadata.

## `validate_targets` {#validate-targets}

Source: `src/gimp_mcp_pro/tools/target_tools.py:219`

```python
async def validate_targets(targets: list[Any], required_capabilities: list[str] | None = None) -> ToolResult
```

**Parameters**

- `targets`
- `required_capabilities`

**Docstring**

Validate that proposed targets still exist and support required actions.

Notes:
    Use this immediately before mutation. It detects missing, ambiguous,
    hidden, locked, non-layer, or otherwise unsupported targets and returns
    actionable failures instead of allowing stale plans to continue.

Args:
    targets: Target references as IDs, names, or dictionaries with kind/id/name.
    required_capabilities: Capabilities such as visible, editable, raster, or alpha.

Returns:
    Operation result with validity, validated targets, failures, and warnings.
