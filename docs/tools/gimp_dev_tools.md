# gimp.dev Integration

Source module: `src/gimp_mcp_pro/tools/gimp_dev_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`gimp_dev_status`](#gimp-dev-status) | Return local ``gimp.dev`` integration availability. | 0 |
| [`gimp_dev_plugin_catalog`](#gimp-dev-plugin-catalog) | Return the pure ``gimp.dev`` plug-in procedure catalog. | 2 |

## `gimp_dev_status` {#gimp-dev-status}

Source: `src/gimp_mcp_pro/tools/gimp_dev_tools.py:30`

```python
async def gimp_dev_status() -> ToolResult
```

**Docstring**

Return local ``gimp.dev`` integration availability.

Returns:
    Operation result containing root, command, allowlist, and availability
    information. This tool never starts GIMP and never mutates the user's
    GIMP profile.

## `gimp_dev_plugin_catalog` {#gimp-dev-plugin-catalog}

Source: `src/gimp_mcp_pro/tools/gimp_dev_tools.py:46`

```python
async def gimp_dev_plugin_catalog(include_raw_catalog: bool = False, validate: bool = True) -> ToolResult
```

**Parameters**

- `include_raw_catalog`
- `validate`

**Docstring**

Return the pure ``gimp.dev`` plug-in procedure catalog.

Args:
    include_raw_catalog: Include the raw catalog JSON from ``gimp-dev``.
        Defaults to false to keep the MCP response compact.
    validate: Ask ``gimp-dev`` to validate the catalog when supported.

Returns:
    Operation result with compact procedure summary and optional raw
    catalog payload. This tool does not start GIMP.
