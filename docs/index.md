# GIMP MCP Pro

GIMP MCP Pro exposes typed Model Context Protocol tools for operating GIMP from an AI assistant while keeping GIMP-specific execution inside a plug-in process.

!!! warning "GIMP 3.2.4 compatibility status"
    The branch-level compatibility claim is still gated by `compat.yml` and live evidence in `compat.results.yml`. Static documentation and tests do not by themselves prove GIMP 3.2.4 compatibility.

## Documentation map

- [Tool Reference](tools/index.md): generated from the actual MCP tool handler docstrings.
- [Compatibility Runbook](gimp-3.2.4-compat.md): clean-profile GIMP 3.2.4 verification workflow.
- [Python API](api/index.md): mkdocstrings-rendered top-level package API.

## Current generated tool count

```yaml
tools: 75
source: src/gimp_mcp_pro/tools
```
