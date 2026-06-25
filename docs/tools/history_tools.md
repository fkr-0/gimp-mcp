# History

Source module: `src/gimp_mcp_pro/tools/history_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`create_checkpoint`](#create-checkpoint) | Create a controlled checkpoint record for the active image. | 2 |
| [`get_operation_log`](#get-operation-log) | Return recent MCP operation-log entries. | 3 |
| [`undo`](#undo) | Undo the last operation(s). | 1 |
| [`redo`](#redo) | Redo previously undone operation(s). | 1 |
| [`begin_undo_group`](#begin-undo-group) | Start an undo group — all subsequent operations will be grouped | 1 |
| [`end_undo_group`](#end-undo-group) | End the current undo group. | 0 |

## `create_checkpoint` {#create-checkpoint}

Source: `src/gimp_mcp_pro/tools/history_tools.py:51`

```python
async def create_checkpoint(label: str = 'checkpoint', include_xcf_copy: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `label` | Human-readable checkpoint label. |
| `include_xcf_copy` | Include controlled temporary XCF-copy metadata. |

## Returns

Operation result with checkpoint ID and metadata. Contract: Checkpoints are generated under a controlled temporary directory and do not overwrite user files. Local paths are redacted from operation logs.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a controlled checkpoint record for the active image.

Args:
    label: Human-readable checkpoint label.
    include_xcf_copy: Include controlled temporary XCF-copy metadata.

Returns:
    Operation result with checkpoint ID and metadata.

Contract:
    Checkpoints are generated under a controlled temporary directory and
    do not overwrite user files. Local paths are redacted from operation logs.

## `get_operation_log` {#get-operation-log}

Source: `src/gimp_mcp_pro/tools/history_tools.py:112`

```python
async def get_operation_log(limit: int = 20, include_snapshots: bool = False, redact_paths: bool = True) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `limit` | Maximum number of recent entries to return. |
| `include_snapshots` | Include snapshot payloads when available. |
| `redact_paths` | Redact local filesystem paths from returned entries. |

## Returns

Operation result with recent operations and retention metadata. Contract: Raw image payloads and local paths are omitted unless explicitly requested.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Return recent MCP operation-log entries.

Args:
    limit: Maximum number of recent entries to return.
    include_snapshots: Include snapshot payloads when available.
    redact_paths: Redact local filesystem paths from returned entries.

Returns:
    Operation result with recent operations and retention metadata.

Contract:
    Raw image payloads and local paths are omitted unless explicitly requested.

## `undo` {#undo}

Source: `src/gimp_mcp_pro/tools/history_tools.py:152`

```python
async def undo(steps: int = 1) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `steps` | Number of undo steps (default 1) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Undo the last operation(s).

Args:
    steps: Number of undo steps (default 1)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `redo` {#redo}

Source: `src/gimp_mcp_pro/tools/history_tools.py:195`

```python
async def redo(steps: int = 1) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `steps` | Number of redo steps (default 1) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Redo previously undone operation(s).

Args:
    steps: Number of redo steps (default 1)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `begin_undo_group` {#begin-undo-group}

Source: `src/gimp_mcp_pro/tools/history_tools.py:238`

```python
async def begin_undo_group(name: str = 'AI Operation') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `name` | Name for the undo group (shown in GIMP's undo history) |

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Start an undo group — all subsequent operations will be grouped
as a single undo step.

Notes:
    Use this tool before multi-step workflows. This lets the user
    undo the entire AI operation with a single Ctrl+Z.

Warnings:
    Important: Always call end_undo_group when done.

Args:
    name: Name for the undo group (shown in GIMP's undo history)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `end_undo_group` {#end-undo-group}

Source: `src/gimp_mcp_pro/tools/history_tools.py:272`

```python
async def end_undo_group() -> ToolResult
```

## Returns

Operation result dictionary with status, message, and tool-specific data or error details.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

End the current undo group.

Must be called after begin_undo_group. All operations between
begin and end will be treated as one undo step.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
