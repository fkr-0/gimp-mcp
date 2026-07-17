# History

Source module: `src/gimp_mcp_pro/tools/history_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`create_checkpoint`](#create-checkpoint) | Create a controlled checkpoint record for the active image. | 2 |
| [`list_checkpoints`](#list-checkpoints) | List checkpoints created during this MCP server session. | 0 |
| [`restore_checkpoint`](#restore-checkpoint) | Open an XCF-backed checkpoint as a new GIMP document. | 1 |
| [`discard_checkpoint`](#discard-checkpoint) | Delete a controlled XCF checkpoint and remove it from this session's index. | 1 |
| [`get_operation_log`](#get-operation-log) | Return recent MCP operation-log entries. | 3 |
| [`undo`](#undo) | Undo the last operation(s). | 1 |
| [`redo`](#redo) | Redo previously undone operation(s). | 1 |
| [`begin_undo_group`](#begin-undo-group) | Start an undo group — all subsequent operations will be grouped | 1 |
| [`end_undo_group`](#end-undo-group) | End the current undo group. | 2 |

## `create_checkpoint` {#create-checkpoint}

Source: `src/gimp_mcp_pro/tools/history_tools.py:55`

```python
async def create_checkpoint(label: str = 'checkpoint', include_xcf_copy: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `label` | Human-readable checkpoint label. |
| `include_xcf_copy` | Save a controlled temporary XCF copy that can be restored later. |

## Returns

Operation result with checkpoint ID and metadata. Contract: Checkpoints are generated under a controlled temporary directory and do not overwrite user files. XCF-backed checkpoints can only be restored into a new document, never silently over the active image. Local paths are redacted from operation logs and tool responses.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Create a controlled checkpoint record for the active image.

Args:
    label: Human-readable checkpoint label.
    include_xcf_copy: Save a controlled temporary XCF copy that can be restored later.

Returns:
    Operation result with checkpoint ID and metadata.

Contract:
    Checkpoints are generated under a controlled temporary directory and
    do not overwrite user files. XCF-backed checkpoints can only be
    restored into a new document, never silently over the active image.
    Local paths are redacted from operation logs and tool responses.

## `list_checkpoints` {#list-checkpoints}

Source: `src/gimp_mcp_pro/tools/history_tools.py:160`

```python
async def list_checkpoints() -> ToolResult
```

## Returns

Operation result with current checkpoint metadata and retention scope.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List checkpoints created during this MCP server session.

Returns a compact, path-redacted index. An XCF-backed checkpoint can be
opened with ``restore_checkpoint``; metadata-only checkpoints are useful
as audit markers but cannot restore pixels.

Returns:
    Operation result with current checkpoint metadata and retention scope.

## `restore_checkpoint` {#restore-checkpoint}

Source: `src/gimp_mcp_pro/tools/history_tools.py:191`

```python
async def restore_checkpoint(checkpoint_id: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `checkpoint_id` | ID returned by ``create_checkpoint`` with ``include_xcf_copy=true``. |

## Returns

Operation result with the opened image ID and redacted checkpoint metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Open an XCF-backed checkpoint as a new GIMP document.

This is deliberately non-destructive: it never replaces the active
document. Compare the newly opened checkpoint with the current image,
then copy or export the material you want to keep.

Args:
    checkpoint_id: ID returned by ``create_checkpoint`` with ``include_xcf_copy=true``.

Returns:
    Operation result with the opened image ID and redacted checkpoint metadata.

## `discard_checkpoint` {#discard-checkpoint}

Source: `src/gimp_mcp_pro/tools/history_tools.py:247`

```python
async def discard_checkpoint(checkpoint_id: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `checkpoint_id` | ID returned by ``create_checkpoint``. |

## Returns

Operation result with deletion status and no local path disclosure.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Delete a controlled XCF checkpoint and remove it from this session's index.

Args:
    checkpoint_id: ID returned by ``create_checkpoint``.

Returns:
    Operation result with deletion status and no local path disclosure.

## `get_operation_log` {#get-operation-log}

Source: `src/gimp_mcp_pro/tools/history_tools.py:284`

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

Source: `src/gimp_mcp_pro/tools/history_tools.py:324`

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

Source: `src/gimp_mcp_pro/tools/history_tools.py:367`

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

Source: `src/gimp_mcp_pro/tools/history_tools.py:410`

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

Source: `src/gimp_mcp_pro/tools/history_tools.py:446`

```python
async def end_undo_group(group_id: str | None = None, close_all: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `group_id` | Optional tracked undo-group ID returned by begin_undo_group. |
| `close_all` | Close all tracked open undo groups in reverse start order. |

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

Args:
    group_id: Optional tracked undo-group ID returned by begin_undo_group.
    close_all: Close all tracked open undo groups in reverse start order.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
