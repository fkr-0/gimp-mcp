"""Focused tests for FEAT-014 compare_snapshots and FEAT-015 assert_image_state."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_compare_snapshots_reports_region_sample_changes_and_ignores_transparency() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    before = {
        "sampled_colors": [
            {"x": 1, "y": 1, "rgba": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}},
            {"x": 5, "y": 5, "rgba": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}},
            {"x": 2, "y": 2, "rgba": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 0.0}},
        ]
    }
    after = {
        "sampled_colors": [
            {"x": 1, "y": 1, "rgba": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}},
            {"x": 5, "y": 5, "rgba": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}},
            {"x": 2, "y": 2, "rgba": {"r": 0.9, "g": 0.9, "b": 0.9, "a": 0.0}},
        ]
    }

    result = await mcp.tools["compare_snapshots"](
        before=before,
        after=after,
        region={"x": 0, "y": 0, "width": 3, "height": 3},
        ignore_transparent=True,
    )

    assert result["success"] is True
    assert result["operation"] == "compare_snapshots"
    assert result["data"]["changed_pixels"] == 1
    assert result["data"]["bounding_box"] == {"x": 1, "y": 1, "width": 1, "height": 1}
    assert result["data"]["ignored_transparent_samples"] == 1
    assert result["data"]["mean_delta"] > 0.0
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_compare_snapshots_reports_structural_changes_when_samples_are_absent() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["compare_snapshots"](
        before={"dimensions": {"width": 64, "height": 32}, "is_dirty": False},
        after={"dimensions": {"width": 128, "height": 32}, "is_dirty": True},
    )

    assert result["success"] is True
    assert result["data"]["changed_fields"] == ["dimensions.width", "is_dirty"]
    assert result["data"]["changed_pixels"] == 0
    assert result["data"]["bounding_box"] is None


@pytest.mark.asyncio
async def test_assert_image_state_evaluates_typed_assertions_against_supplied_state() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)
    state = {
        "dimensions": {"width": 64, "height": 32},
        "layer_tree": [
            {"name": "Ink", "visible": True},
            {"name": "Sketch", "visible": False},
        ],
        "selections": {"non_empty": True},
    }

    result = await mcp.tools["assert_image_state"](
        state=state,
        assertions=[
            {"type": "layer_exists", "name": "Ink"},
            {"type": "layer_visible", "name": "Ink", "visible": True},
            {"type": "dimensions_equal", "width": 64, "height": 32},
            {"type": "selection_non_empty", "expected": True},
            {
                "type": "color_close",
                "actual": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1.0},
                "expected": {"r": 0.51, "g": 0.5, "b": 0.49, "a": 1.0},
                "tolerance": 0.02,
            },
        ],
    )

    assert result["success"] is True
    assert result["data"]["passed"] is True
    assert [item["passed"] for item in result["data"]["results"]] == [True, True, True, True, True]
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_assert_image_state_returns_structured_failures_without_throwing() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["assert_image_state"](
        state={"dimensions": {"width": 64, "height": 32}, "layer_tree": []},
        assertions=[
            {"type": "layer_exists", "name": "Missing"},
            {"type": "dimensions_equal", "width": 128, "height": 32},
            {"type": "selection_non_empty", "expected": True},
        ],
    )

    assert result["success"] is True
    assert result["data"]["passed"] is False
    assert [item["passed"] for item in result["data"]["results"]] == [False, False, False]
    assert "Missing" in result["data"]["results"][0]["message"]
    assert "64x32" in result["data"]["results"][1]["message"]
    assert "non-empty" in result["data"]["results"][2]["message"]
