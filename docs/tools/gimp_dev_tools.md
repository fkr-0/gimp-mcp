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

## Returns

Operation result containing root, command, allowlist, and availability information. This tool never starts GIMP and never mutates the user's GIMP profile.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

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

## Parameters

| Parameter | Description |
|---|---|
| `include_raw_catalog` | Include the raw catalog JSON from ``gimp-dev``. Defaults to false to keep the MCP response compact. |
| `validate` | Ask ``gimp-dev`` to validate the catalog when supported. |

## Returns

Operation result with compact procedure summary and optional raw catalog payload. This tool does not start GIMP.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Return the pure ``gimp.dev`` plug-in procedure catalog.

Args:
    include_raw_catalog: Include the raw catalog JSON from ``gimp-dev``.
        Defaults to false to keep the MCP response compact.
    validate: Ask ``gimp-dev`` to validate the catalog when supported.

Returns:
    Operation result with compact procedure summary and optional raw
    catalog payload. This tool does not start GIMP.
