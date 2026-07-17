# Agent Tools

Source module: `src/gimp_mcp_pro/tools/agent_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`begin_edit_transaction`](#begin-edit-transaction) | Begin a reversible edit transaction backed by a GIMP undo group. | 2 |
| [`end_edit_transaction`](#end-edit-transaction) | End a tracked or best-effort GIMP undo transaction. | 2 |
| [`rollback_transaction`](#rollback-transaction) | Rollback a transaction using GIMP undo where available. | 3 |

## `begin_edit_transaction` {#begin-edit-transaction}

Source: `src/gimp_mcp_pro/tools/agent_tools.py:151`

```python
async def begin_edit_transaction(label: str = 'AI edit transaction', capture_before_state: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `label` | Human-readable transaction label for logs and result metadata. |
| `capture_before_state` | Include active image metadata in the result. |

## Returns

Operation result with transaction ID, undo-group state, and optional before-state metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Begin a reversible edit transaction backed by a GIMP undo group.

The returned transaction ID can be passed to ``end_edit_transaction`` or
``rollback_transaction``. The transaction is also useful audit metadata
for an LLM agent planning multi-step edits.

Args:
    label: Human-readable transaction label for logs and result metadata.
    capture_before_state: Include active image metadata in the result.

Returns:
    Operation result with transaction ID, undo-group state, and optional before-state metadata.

## `end_edit_transaction` {#end-edit-transaction}

Source: `src/gimp_mcp_pro/tools/agent_tools.py:225`

```python
async def end_edit_transaction(transaction_id: str | None = None, require_known: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `transaction_id` | Optional ID returned by begin_edit_transaction. |
| `require_known` | Fail before touching GIMP when the transaction ID is not tracked. |

## Returns

Operation result with tracking and undo-group closure metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

End a tracked or best-effort GIMP undo transaction.

Args:
    transaction_id: Optional ID returned by begin_edit_transaction.
    require_known: Fail before touching GIMP when the transaction ID is not tracked.

Returns:
    Operation result with tracking and undo-group closure metadata.

## `rollback_transaction` {#rollback-transaction}

Source: `src/gimp_mcp_pro/tools/agent_tools.py:274`

```python
async def rollback_transaction(transaction_id: str | None = None, require_known: bool = False, recover_all: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `transaction_id` | Optional ID returned by begin_edit_transaction. |
| `require_known` | Fail before touching GIMP when the transaction ID is not tracked. |
| `recover_all` | Roll back and clear all tracked open transactions in LIFO order. |

## Returns

Operation result with tracking, undo-group, and rollback metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Rollback a transaction using GIMP undo where available.

Args:
    transaction_id: Optional ID returned by begin_edit_transaction.
    require_known: Fail before touching GIMP when the transaction ID is not tracked.
    recover_all: Roll back and clear all tracked open transactions in LIFO order.

Returns:
    Operation result with tracking, undo-group, and rollback metadata.
