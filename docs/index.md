# GIMP MCP Pro

GIMP MCP Pro exposes typed Model Context Protocol tools for operating GIMP from an AI assistant while keeping GIMP-specific execution inside a plug-in process.

!!! success "GIMP 3.2.4 compatibility verified"
    `compat.results.yml` records a 24/24 isolated clean-profile Xvfb run with the 183-tool registry and `claim_allowed: true`. Re-run the contract whenever the plug-in protocol or GIMP-facing generated code changes.

## Documentation map

- [Tool Reference](tools/index.md): generated from the actual MCP tool handler docstrings.
- [Docstring Style](docstring-style.md): Google-style policy used by MkDocs and the MCP tool audit.
- [Compatibility Runbook](gimp-3.2.4-compat.md): clean-profile GIMP 3.2.4 verification workflow.
- [Native Backend Helpers](native-backend.md): architecture and usage of shared generated-code helpers.
- [Python API](api/index.md): mkdocstrings-rendered top-level package API.

## Current generated tool count

```yaml
tools: 186
source: src/gimp_mcp_pro/tools
```
