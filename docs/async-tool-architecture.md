# Async Tool Architecture

This branch treats async as the default MCP tool contract.

## Goals

```yaml
primary_goal: every MCP tool handler is an async coroutine
transport_goal: MCP server uses asyncio-native transport for tool execution
compat_goal: keep the existing synchronous GimpBridge API available for CLI and legacy callers
verification_goal: prevent regressions with static and registration-time tests
```

## Layers

```text
FastMCP tool handler
  async def tool(...)
    ↓ awaits
AsyncToolBridge protocol
    ↓ implemented by
AsyncGimpBridge       # asyncio-native transport used by the MCP server
GimpBridge adapters   # sync socket transport plus async_* compatibility wrappers
    ↓ framed JSON TCP
GIMP plug-in socket
```

## Tool registration contract

Tool modules depend on two small protocols from `gimp_mcp_pro.tools.types`:

```python
class MCPToolRegistrar(Protocol):
    def tool(self, *args: Any, **kwargs: Any) -> ToolDecorator: ...

class AsyncToolBridge(Protocol):
    async def async_execute_python(...): ...
    async def async_get_image_bitmap(...): ...
    async def async_get_image_metadata(...): ...
    async def async_get_context_state(...): ...
    async def async_get_gimp_info(...): ...
```

Tool modules should not type themselves against concrete FastMCP or bridge classes. This keeps registration usable with test doubles, `GimpBridge`, and `AsyncGimpBridge`.

## Server behavior

The MCP server constructs `AsyncGimpBridge` in `create_server()`. This gives tool execution an asyncio-native socket path.

The CLI still uses `GimpBridge` for `doctor`, `repl`, and direct synchronous callers. `GimpBridge` keeps `async_*` adapter methods so it still satisfies `AsyncToolBridge` where useful.

## Regression checks

```bash
uv run pytest --no-cov tests/test_async_tool_registry.py
```

This verifies:

```yaml
checks:
  - all @mcp.tool handlers in src/gimp_mcp_pro/tools are async def
  - all registered tool callables are coroutine functions
  - tool modules do not call sync bridge methods directly
  - create_server uses AsyncGimpBridge for MCP execution
```

The full quality gate also runs these tests:

```bash
uv run python scripts/project.py check
```

## Conversion rule for new tools

Use this pattern:

```python
@mcp.tool()
async def new_tool(...) -> dict[str, Any]:
    try:
        result = await bridge.async_execute_python(code)
        return OperationResult.ok(...).model_dump()
    except GimpCommandError as exc:
        return OperationResult.fail(operation="new_tool", error=str(exc)).model_dump()
```

Avoid this pattern in MCP tool handlers:

```python
bridge.execute_python(code)        # blocks the MCP event loop
bridge.get_image_metadata()        # sync convenience wrapper
bridge.send_command(...)           # sync transport path
```

## Current status

```yaml
mcp_tool_handlers: 75
async_handlers: 75
sync_handlers: 0
server_transport: AsyncGimpBridge
remaining_live_dependency: actual GIMP 3.2.4 clean-profile smoke run
```
