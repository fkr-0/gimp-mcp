"""Tests for async read-only inspection tools."""

from __future__ import annotations

import inspect

import pytest

from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools


class CaptureMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class AsyncFakeBridge:
    async def async_get_image_bitmap(self, max_width=None, max_height=None, region=None):
        return {
            "status": "success",
            "results": {
                "image_data": "iVBORw0KGgo=",
                "width": 8,
                "height": 4,
                "original_width": 8,
                "original_height": 4,
            },
        }

    async def async_get_image_metadata(self):
        return {"status": "success", "results": {"basic": {"width": 8, "height": 4}}}

    async def async_get_context_state(self):
        return {"status": "success", "results": {"foreground_color": "black"}}

    async def async_get_gimp_info(self):
        return {"status": "success", "results": {"gimp": {"version": "3.2.4"}}}


def _registered_tools() -> dict[str, object]:
    mcp = CaptureMCP()
    register_inspect_tools(mcp, AsyncFakeBridge())
    return mcp.tools


def test_inspection_tools_are_async_coroutines() -> None:
    tools = _registered_tools()

    assert set(tools) == {
        "compare_snapshots",
        "assert_image_state",
        "session_capabilities",
        "observe_document_state",
        "get_layer_tree_detailed",
        "observe_region",
        "create_contact_sheet",
        "get_image_bitmap",
        "get_image_metadata",
        "get_context_state",
        "get_gimp_info",
    }
    assert all(inspect.iscoroutinefunction(tool) for tool in tools.values())


@pytest.mark.asyncio
async def test_get_gimp_info_async_tool_returns_version_data() -> None:
    tool = _registered_tools()["get_gimp_info"]

    result = await tool()

    assert result["success"] is True
    assert result["operation"] == "get_gimp_info"
    assert result["data"]["gimp"]["version"] == "3.2.4"


@pytest.mark.asyncio
async def test_get_image_bitmap_async_tool_builds_region_dict() -> None:
    tool = _registered_tools()["get_image_bitmap"]

    result = await tool(region_x=1, region_y=2, region_width=3, region_height=4)

    assert result["success"] is True
    assert result["data"]["format"] == "png"
    assert result["data"]["width"] == 8
