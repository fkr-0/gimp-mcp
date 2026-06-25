"""Focused TDD coverage for context explanation and geometry measurement."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_explain_current_context_generates_machine_readable_summary() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["explain_current_context"](
        detail_level="high",
        include_recommendations=True,
    )

    assert result["success"] is True
    assert result["operation"] == "explain_current_context"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_explain_current_context__" in generated
    assert "detail_level = 'high'" in generated
    assert "include_recommendations = True" in generated
    assert "facts" in generated
    assert "warnings" in generated
    assert "recommendations" in generated
    assert "summary" in generated
    assert "layer.get_visible()" in generated
    assert "Gimp.Selection.bounds(image)" in generated


@pytest.mark.asyncio
async def test_explain_current_context_rejects_invalid_detail_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["explain_current_context"](detail_level="maximal")

    assert result["success"] is False
    assert "detail_level" in result["error"]
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_measure_geometry_generates_layer_distance_overlap_and_alignment_metrics() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["measure_geometry"](
        targets=[{"layer_name": "A"}, {"layer_name": "B"}],
        measurements=["bounds", "distance", "overlap", "alignment", "spacing"],
    )

    assert result["success"] is True
    assert result["operation"] == "measure_geometry"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_measure_geometry__" in generated
    assert "measurements = ['bounds', 'distance', 'overlap', 'alignment', 'spacing']" in generated
    assert "image.get_layer_by_name('A')" in generated
    assert "image.get_layer_by_name('B')" in generated
    assert "canvas_relative" in generated
    assert "target_relative" in generated
    assert "distance" in generated
    assert "overlap" in generated
    assert "alignment" in generated
    assert "spacing" in generated


@pytest.mark.asyncio
async def test_measure_geometry_rejects_unknown_measurement_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["measure_geometry"](
        targets=[{"layer_name": "A"}],
        measurements=["bounds", "banana"],
    )

    assert result["success"] is False
    assert "measurement" in result["error"].lower()
    assert bridge.calls == []
