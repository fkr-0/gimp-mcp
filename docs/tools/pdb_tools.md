# PDB and Escape Hatch

Source module: `src/gimp_mcp_pro/tools/pdb_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`search_pdb`](#search-pdb) | Search GIMP's Procedure Database for available operations. | 2 |
| [`execute_python`](#execute-python) | Execute raw Python code in GIMP's PyGObject console. | 2 |

## `search_pdb` {#search-pdb}

Source: `src/gimp_mcp_pro/tools/pdb_tools.py:24`

```python
async def search_pdb(query: str, max_results: int = 20) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `query` | Search term (e.g., "blur", "sharpen", "file-png", "color") |
| `max_results` | Maximum results to return (default 20) |

## Returns

List of matching procedure names.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Search GIMP's Procedure Database for available operations.

GIMP has thousands of procedures (filters, file operations, etc.).
Use this to discover what's available.

Args:
    query: Search term (e.g., "blur", "sharpen", "file-png", "color")
    max_results: Maximum results to return (default 20)

Returns:
    List of matching procedure names.

## `execute_python` {#execute-python}

Source: `src/gimp_mcp_pro/tools/pdb_tools.py:80`

```python
async def execute_python(code: list[str], timeout_seconds: float = 30.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `code` | List of Python code strings to execute sequentially. |
| `timeout_seconds` | Timeout for execution (default 30, use longer for heavy operations like filters) |
| `Example` | ["x = 5", "print(x + 1)"] |

## Returns

Result with stdout output from each line.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Execute raw Python code in GIMP's PyGObject console.

This is the ESCAPE HATCH for operations that don't have a dedicated
typed tool. Use typed tools whenever possible — they have better
error handling and validation.

The code runs in GIMP's persistent Python context:
- Imports persist between calls
- Variables persist between calls
- Gimp and Gegl modules are pre-imported

Warnings:
    Important: Always call Gimp.displays_flush() after drawing operations.
    Always call Gimp.Selection.none(image) after selection-based operations.

Args:
    code: List of Python code strings to execute sequentially.
          Example: ["x = 5", "print(x + 1)"]
    timeout_seconds: Timeout for execution (default 30, use longer for
                    heavy operations like filters)

Returns:
    Result with stdout output from each line.
