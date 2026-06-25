# PDB and Escape Hatch

Source module: `src/gimp_mcp_pro/tools/pdb_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`search_pdb`](#search-pdb) | Search GIMP's Procedure Database for available operations. | 2 |
| [`execute_pdb_call`](#execute-pdb-call) | Validate and optionally execute an allowlisted typed PDB procedure call. | 5 |
| [`execute_python`](#execute-python) | Execute raw Python code in GIMP's PyGObject console. | 2 |
| [`pdb_introspect_typed`](#pdb-introspect-typed) | Return typed PDB procedure metadata for safer wrapper generation. | 3 |
| [`safe_python_eval`](#safe-python-eval) | Run restricted diagnostic Python only when explicitly debug-enabled. | 4 |

## `search_pdb` {#search-pdb}

Source: `src/gimp_mcp_pro/tools/pdb_tools.py:86`

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

## `execute_pdb_call` {#execute-pdb-call}

Source: `src/gimp_mcp_pro/tools/pdb_tools.py:142`

```python
async def execute_pdb_call(procedure: str, arguments: dict[str, Any] | None = None, allow_deprecated: bool = False, dry_run: bool = True, timeout: float = 30.0) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `procedure` | PDB procedure name. Must be in the local allowlist. |
| `arguments` | Procedure arguments keyed by property name. |
| `allow_deprecated` | Whether deprecated procedures are allowed. |
| `dry_run` | Validate without calling proc.run when true. |
| `timeout` | Bridge timeout in seconds. |

## Returns

Operation result with validation metadata and optional return values.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Validate and optionally execute an allowlisted typed PDB procedure call.

Args:
    procedure: PDB procedure name. Must be in the local allowlist.
    arguments: Procedure arguments keyed by property name.
    allow_deprecated: Whether deprecated procedures are allowed.
    dry_run: Validate without calling proc.run when true.
    timeout: Bridge timeout in seconds.

Returns:
    Operation result with validation metadata and optional return values.

## `execute_python` {#execute-python}

Source: `src/gimp_mcp_pro/tools/pdb_tools.py:197`

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

## `pdb_introspect_typed` {#pdb-introspect-typed}

Source: `src/gimp_mcp_pro/tools/pdb_tools.py:250`

```python
async def pdb_introspect_typed(query: str, include_deprecated: bool = False, max_results: int = 25) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `query` | Procedure-name search string. |
| `include_deprecated` | Include deprecated procedures where detectable. |
| `max_results` | Maximum procedures to return. |

## Returns

Operation result with procedure signatures and deprecation notes.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Return typed PDB procedure metadata for safer wrapper generation.

Args:
    query: Procedure-name search string.
    include_deprecated: Include deprecated procedures where detectable.
    max_results: Maximum procedures to return.

Returns:
    Operation result with procedure signatures and deprecation notes.

## `safe_python_eval` {#safe-python-eval}

Source: `src/gimp_mcp_pro/tools/pdb_tools.py:282`

```python
async def safe_python_eval(code: str, mode: str = 'expression', timeout: float = 1.0, require_debug_enabled: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `code` | Python expression or statement. |
| `mode` | expression or statement. |
| `timeout` | Timeout in seconds. |
| `require_debug_enabled` | Must be true to execute this diagnostic escape hatch. |

## Returns

Operation result with stdout/stderr/result metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Run restricted diagnostic Python only when explicitly debug-enabled.

Args:
    code: Python expression or statement.
    mode: expression or statement.
    timeout: Timeout in seconds.
    require_debug_enabled: Must be true to execute this diagnostic escape hatch.

Returns:
    Operation result with stdout/stderr/result metadata.
