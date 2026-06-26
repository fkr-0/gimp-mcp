"""Tests for async read-only inspection tools."""

from __future__ import annotations

import inspect
import json

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
        "content_bounds",
        "text_layer_introspection",
        "generate_layer_report",
        "prepare_export_checklist",
        "explain_current_context",
        "measure_geometry",
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


class RecordingBitmapBridge(AsyncFakeBridge):
    def __init__(self) -> None:
        self.bitmap_calls: list[dict[str, object]] = []

    async def async_get_image_bitmap(self, max_width=None, max_height=None, region=None):
        self.bitmap_calls.append(
            {"max_width": max_width, "max_height": max_height, "region": region}
        )
        return await super().async_get_image_bitmap(max_width, max_height, region)


def _registered_tools_with_bridge(bridge: AsyncFakeBridge) -> dict[str, object]:
    mcp = CaptureMCP()
    register_inspect_tools(mcp, bridge)
    return mcp.tools


@pytest.mark.asyncio
async def test_get_image_bitmap_rejects_unbounded_dimensions_before_bridge_call() -> None:
    bridge = RecordingBitmapBridge()
    tool = _registered_tools_with_bridge(bridge)["get_image_bitmap"]

    result = await tool(max_width=8192, max_height=8192)

    assert result["success"] is False
    assert "between 1 and 4096" in result["error"]
    assert bridge.bitmap_calls == []


@pytest.mark.asyncio
async def test_get_image_bitmap_rejects_unbounded_region_before_bridge_call() -> None:
    bridge = RecordingBitmapBridge()
    tool = _registered_tools_with_bridge(bridge)["get_image_bitmap"]

    result = await tool(region_x=0, region_y=0, region_width=10000, region_height=10000)

    assert result["success"] is False
    assert "region_width" in result["error"]
    assert bridge.bitmap_calls == []


class InspectContractBridge(RecordingBitmapBridge):
    def __init__(self) -> None:
        super().__init__()
        self.execute_calls: list[list[str]] = []

    async def async_execute_python(self, code_lines, timeout=None):
        del timeout
        self.execute_calls.append(code_lines)
        source = "\n".join(code_lines)
        if "__gimp_mcp_contact_sheet__" in source:
            return {
                "status": "success",
                "results": [
                    json.dumps(
                        {
                            "contact_sheet_png": None,
                            "tile_index": [
                                {
                                    "id": 1,
                                    "name": "Layer 1",
                                    "visible": True,
                                    "width": 64,
                                    "height": 32,
                                    "label": "1: Layer 1",
                                }
                            ],
                            "tile_count": 1,
                            "columns": 1,
                            "rows": 1,
                            "max_tile_size": 128,
                            "label_tiles": True,
                            "include_hidden_layers": False,
                            "warnings": ["metadata only"],
                        }
                    )
                ],
            }
        return {
            "status": "success",
            "results": [
                json.dumps(
                    {
                        "region_bounds": {"x": 1, "y": 2, "width": 3, "height": 4},
                        "sampled_colors": [
                            {"x": 1, "y": 2, "color": {"r": 0.1, "g": 0.2, "b": 0.3, "a": 1.0}}
                        ],
                        "histogram": None,
                    }
                )
            ],
        }


@pytest.mark.asyncio
async def test_create_contact_sheet_contract_is_bounded_and_schema_stable() -> None:
    bridge = InspectContractBridge()
    tool = _registered_tools_with_bridge(bridge)["create_contact_sheet"]

    result = await tool(max_tile_size=128, label_tiles=True)

    assert result["success"] is True
    data = result["data"]
    assert set(data) >= {
        "contact_sheet_png",
        "tile_index",
        "tile_count",
        "columns",
        "rows",
        "max_tile_size",
        "label_tiles",
        "include_hidden_layers",
        "warnings",
    }
    assert data["contact_sheet_png"] is None
    assert data["tile_count"] == len(data["tile_index"])
    assert data["max_tile_size"] <= 1024
    assert data["columns"] * data["rows"] >= data["tile_count"]
    tile = data["tile_index"][0]
    assert set(tile) >= {"id", "name", "visible", "width", "height", "label"}
    assert "__gimp_mcp_contact_sheet__" in "\n".join(bridge.execute_calls[-1])


@pytest.mark.asyncio
async def test_create_contact_sheet_rejects_unbounded_tile_size_before_bridge_call() -> None:
    bridge = InspectContractBridge()
    tool = _registered_tools_with_bridge(bridge)["create_contact_sheet"]

    result = await tool(max_tile_size=4096)

    assert result["success"] is False
    assert "between 16 and 1024" in result["error"]
    assert bridge.execute_calls == []


@pytest.mark.asyncio
async def test_observe_region_contract_contains_bounded_bitmap_and_sample_schema() -> None:
    bridge = InspectContractBridge()
    tool = _registered_tools_with_bridge(bridge)["observe_region"]

    result = await tool(x=1, y=2, width=3, height=4, max_size=256, include_histogram=True)

    assert result["success"] is True
    data = result["data"]
    assert set(data) >= {
        "crop_png",
        "format",
        "encoding",
        "width",
        "height",
        "original_width",
        "original_height",
        "region_bounds",
        "sampled_colors",
        "histogram",
    }
    assert data["format"] == "png"
    assert data["encoding"] == "base64"
    assert data["width"] <= 256
    assert data["height"] <= 256
    assert data["region_bounds"] == {"x": 1, "y": 2, "width": 3, "height": 4}
    sample = data["sampled_colors"][0]
    assert set(sample) >= {"x", "y", "color"}
    assert bridge.bitmap_calls[-1]["max_width"] == 256
    assert bridge.bitmap_calls[-1]["max_height"] == 256
