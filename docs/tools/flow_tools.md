# Repeatable Flows and Macros

Source module: `src/gimp_mcp_pro/tools/flow_tools.py`

| Tool | Summary | Parameters |
|---|---|---:|
| [`propose_flow`](#propose-flow) | Save an agent-authored flow proposal as an inactive draft. | 1 |
| [`list_flows`](#list-flows) | List user-local flows, optionally filtered by lifecycle state. | 1 |
| [`get_flow`](#get-flow) | Return one complete flow definition. | 1 |
| [`validate_flow`](#validate-flow) | Statically validate operation names and arguments, then mark valid drafts. | 1 |
| [`activate_flow`](#activate-flow) | Explicitly activate a validated flow. | 2 |
| [`deactivate_flow`](#deactivate-flow) | Return an active flow to validated state and unpin it. | 1 |
| [`pin_flow`](#pin-flow) | Pin an active flow into GIMP's Repeatable Flows menu. | 1 |
| [`unpin_flow`](#unpin-flow) | Remove a flow's direct GIMP menu entry. | 1 |
| [`run_flow`](#run-flow) | Execute a validated or active flow through the shared operation registry. | 4 |
| [`dry_run_macro`](#dry-run-macro) | Validate a typed multi-step macro without mutating GIMP state. | 1 |
| [`run_macro_transaction`](#run-macro-transaction) | Execute a typed multi-step macro as one fail-safe transaction. | 4 |

## `propose_flow` {#propose-flow}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:175`

```python
async def propose_flow(definition: dict[str, Any]) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `definition` | Flow definition payload to validate and save as an inactive draft. |

## Returns

Operation result dictionary with the stored draft flow or validation errors.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Save an agent-authored flow proposal as an inactive draft.

Args:
    definition: Flow definition payload to validate and save as an inactive draft.

Returns:
    Operation result dictionary with the stored draft flow or validation errors.

## `list_flows` {#list-flows}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:200`

```python
async def list_flows(state: str | None = None) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `state` | Optional lifecycle state filter such as draft, validated, or active. |

## Returns

Operation result dictionary with flow summaries and total count.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

List user-local flows, optionally filtered by lifecycle state.

Args:
    state: Optional lifecycle state filter such as draft, validated, or active.

Returns:
    Operation result dictionary with flow summaries and total count.

## `get_flow` {#get-flow}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:225`

```python
async def get_flow(flow_id: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `flow_id` | Identifier of the flow to return. |

## Returns

Operation result dictionary with the complete flow definition or an error.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Return one complete flow definition.

Args:
    flow_id: Identifier of the flow to return.

Returns:
    Operation result dictionary with the complete flow definition or an error.

## `validate_flow` {#validate-flow}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:243`

```python
async def validate_flow(flow_id: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `flow_id` | Identifier of the flow to validate. |

## Returns

Operation result dictionary with validation status, errors, and updated flow metadata.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Statically validate operation names and arguments, then mark valid drafts.

Args:
    flow_id: Identifier of the flow to validate.

Returns:
    Operation result dictionary with validation status, errors, and updated flow metadata.

## `activate_flow` {#activate-flow}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:272`

```python
async def activate_flow(flow_id: str, confirm_unsafe: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `flow_id` | Identifier of the validated flow to activate. |
| `confirm_unsafe` | True confirms activation of flows with unsafe capabilities. |

## Returns

Operation result dictionary with the activated flow or safety/validation errors.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Explicitly activate a validated flow.

Args:
    flow_id: Identifier of the validated flow to activate.
    confirm_unsafe: True confirms activation of flows with unsafe capabilities.

Returns:
    Operation result dictionary with the activated flow or safety/validation errors.

## `deactivate_flow` {#deactivate-flow}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:299`

```python
async def deactivate_flow(flow_id: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `flow_id` | Identifier of the active flow to deactivate. |

## Returns

Operation result dictionary with the deactivated flow or an error.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Return an active flow to validated state and unpin it.

Args:
    flow_id: Identifier of the active flow to deactivate.

Returns:
    Operation result dictionary with the deactivated flow or an error.

## `pin_flow` {#pin-flow}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:318`

```python
async def pin_flow(flow_id: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `flow_id` | Identifier of the active flow to pin. |

## Returns

Operation result dictionary with the pinned flow or an error.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Pin an active flow into GIMP's Repeatable Flows menu.

Args:
    flow_id: Identifier of the active flow to pin.

Returns:
    Operation result dictionary with the pinned flow or an error.

## `unpin_flow` {#unpin-flow}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:336`

```python
async def unpin_flow(flow_id: str) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `flow_id` | Identifier of the flow to unpin. |

## Returns

Operation result dictionary with the unpinned flow or an error.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Remove a flow's direct GIMP menu entry.

Args:
    flow_id: Identifier of the flow to unpin.

Returns:
    Operation result dictionary with the unpinned flow or an error.

## `run_flow` {#run-flow}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:354`

```python
async def run_flow(flow_id: str, parameters: dict[str, Any] | None = None, confirm_unsafe: bool = False, checkpoint_decision: str = 'commit') -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `flow_id` | Identifier of the validated or active flow to execute. |
| `parameters` | Optional runtime parameter values for the flow. |
| `confirm_unsafe` | True confirms execution of flows with unsafe capabilities. |
| `checkpoint_decision` | Transaction checkpoint decision, usually commit or rollback. |

## Returns

Operation result dictionary with the flow run payload or execution error.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Execute a validated or active flow through the shared operation registry.

Args:
    flow_id: Identifier of the validated or active flow to execute.
    parameters: Optional runtime parameter values for the flow.
    confirm_unsafe: True confirms execution of flows with unsafe capabilities.
    checkpoint_decision: Transaction checkpoint decision, usually commit or rollback.

Returns:
    Operation result dictionary with the flow run payload or execution error.

## `dry_run_macro` {#dry-run-macro}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:394`

```python
async def dry_run_macro(steps: list[dict[str, Any]]) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `steps` | Ordered MCP tool steps with tool names and argument dictionaries. |

## Returns

Operation result dictionary with validity, predicted changes, resolved targets, and failures.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Validate a typed multi-step macro without mutating GIMP state.

Args:
    steps: Ordered MCP tool steps with tool names and argument dictionaries.

Returns:
    Operation result dictionary with validity, predicted changes, resolved targets, and failures.

## `run_macro_transaction` {#run-macro-transaction}

Source: `src/gimp_mcp_pro/tools/flow_tools.py:431`

```python
async def run_macro_transaction(steps: list[dict[str, Any]], transaction_label: str = 'MCP Macro Transaction', rollback_on_failure: bool = True, capture_before_after: bool = False) -> ToolResult
```

## Parameters

| Parameter | Description |
|---|---|
| `steps` | Ordered MCP tool steps with tool names and argument dictionaries. |
| `transaction_label` | Human-readable label for the undo/transaction phase. |
| `rollback_on_failure` | Must remain true so macro execution is atomic. |
| `capture_before_after` | Capture document observations before and after execution when available. |

## Returns

Operation result dictionary with transaction id, step results, rollback status, and evidence.

## Contract

- Return shape: `ToolResult` / `OperationResult` with structured status, message, data, and error fields.
- Compatibility contract: `compat.yml` tracks this public MCP registry surface.
- Generated-code smoke: `tests/test_tool_generated_code_paths.py` exercises fast handler success paths.
- Invocation matrix: `tests/test_tool_invocation_matrix.py` keeps public arguments covered.

## Docstring

Execute a typed multi-step macro as one fail-safe transaction.

Args:
    steps: Ordered MCP tool steps with tool names and argument dictionaries.
    transaction_label: Human-readable label for the undo/transaction phase.
    rollback_on_failure: Must remain true so macro execution is atomic.
    capture_before_after: Capture document observations before and after execution when available.

Returns:
    Operation result dictionary with transaction id, step results, rollback status, and evidence.
