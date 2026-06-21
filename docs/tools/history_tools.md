# History

Source module: `src/gimp_mcp_pro/tools/history_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`undo`](#undo) | Undo the last operation(s). | 1 |
| [`redo`](#redo) | Redo previously undone operation(s). | 1 |
| [`begin_undo_group`](#begin-undo-group) | Start an undo group — all subsequent operations will be grouped | 1 |
| [`end_undo_group`](#end-undo-group) | End the current undo group. | 0 |

## `undo` {#undo}

Source: `src/gimp_mcp_pro/tools/history_tools.py:18`

```python
async def undo(steps: int = 1) -> ToolResult
```

**Parameters**

- `steps`

**Docstring**

Undo the last operation(s).

Args:
    steps: Number of undo steps (default 1)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `redo` {#redo}

Source: `src/gimp_mcp_pro/tools/history_tools.py:61`

```python
async def redo(steps: int = 1) -> ToolResult
```

**Parameters**

- `steps`

**Docstring**

Redo previously undone operation(s).

Args:
    steps: Number of redo steps (default 1)

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.

## `begin_undo_group` {#begin-undo-group}

Source: `src/gimp_mcp_pro/tools/history_tools.py:104`

```python
async def begin_undo_group(name: str = 'AI Operation') -> ToolResult
```

**Parameters**

- `name`

**Docstring**

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

Source: `src/gimp_mcp_pro/tools/history_tools.py:138`

```python
async def end_undo_group() -> ToolResult
```

**Docstring**

End the current undo group.

Must be called after begin_undo_group. All operations between
begin and end will be treated as one undo step.

Returns:
    Operation result dictionary with status, message, and tool-specific data or error details.
