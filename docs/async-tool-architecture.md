# Async Tool Architecture

This branch treats async as the default MCP tool contract.

## Goals

```yaml
primary_goal: every MCP tool handler is an async coroutine
transport_goal: MCP server uses asyncio-native transport for tool execution
compat_goal: keep the existing synchronous GimpBridge API available for CLI and legacy callers
verification_goal: prevent regressions with static, typing, and registration-time tests
```

## Layers

```text
FastMCP tool handler
  async def tool(...) -> ToolResult
    ↓ awaits
AsyncToolBridge protocol
    ↓ uses shared protocol aliases from gimp_mcp_pro.protocol
AsyncGimpBridge       # asyncio-native transport used by the MCP server
GimpBridge adapters   # sync socket transport plus async_* compatibility wrappers
    ↓ framed JSON TCP
GIMP plug-in socket
```

## Shared protocol types

`gimp_mcp_pro.protocol` owns the JSON boundary types used by tools and bridges:

```python
CommandParams = dict[str, Any]
ToolResult = dict[str, Any]

class PluginResponse(TypedDict, total=False):
    id: int
    status: Literal["success", "error"]
    results: Any
    error: str
    traceback: str

class BitmapRegion(TypedDict):
    origin_x: int
    origin_y: int
    width: int
    height: int
```

Use `PluginResponse` for raw transport responses from the GIMP plug-in. Use `ToolResult` for public MCP tool results returned after converting those responses into `OperationResult` payloads.

## Tool registration contract

Tool modules depend on two small protocols from `gimp_mcp_pro.tools.types`:

```python
class MCPToolRegistrar(Protocol):
    def tool(self, *args: Any, **kwargs: Any) -> ToolDecorator: ...

class AsyncToolBridge(Protocol):
    async def async_send_command(...) -> PluginResponse: ...
    async def async_execute_python(...) -> PluginResponse: ...
    async def async_evaluate_python(...) -> PluginResponse: ...
    async def async_get_image_bitmap(...) -> PluginResponse: ...
    async def async_get_image_metadata(...) -> PluginResponse: ...
    async def async_get_context_state(...) -> PluginResponse: ...
    async def async_get_gimp_info(...) -> PluginResponse: ...
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
  - every @mcp.tool handler is annotated as returning ToolResult
  - all registered tool callables are coroutine functions
  - representative tools await async bridge methods at runtime
  - both GimpBridge and AsyncGimpBridge satisfy the AsyncToolBridge protocol surface
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
from gimp_mcp_pro.tools.types import AsyncToolBridge, MCPToolRegistrar, ToolResult


def register_tools(mcp: MCPToolRegistrar, bridge: AsyncToolBridge) -> None:
    @mcp.tool()
    async def new_tool(...) -> ToolResult:
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
tool_return_annotation: ToolResult
raw_transport_response_annotation: PluginResponse
server_transport: AsyncGimpBridge
remaining_live_dependency: actual GIMP 3.2.4 clean-profile smoke run
```


## Optional 3.2.4 capabilities

Async tools that depend on optional GIMP procedures should not hide the failure
or return only a localized text string. They should return the standard tool
result with `data.error_code: optional_capability_unavailable`, plus the related
PDB procedure and a fallback recommendation. The compatibility runner uses this
metadata to distinguish an accepted optional limitation from an async transport
regression.
