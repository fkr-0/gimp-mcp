"""Focused tests for FEAT-005 sample_pixels."""

from __future__ import annotations

from typing import Any

import pytest

from gimp_mcp_pro.tools.color_tools import register_color_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_sample_pixels_samples_explicit_points_with_composite_pick_color() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["sample_pixels"](
        points=[{"x": 1, "y": 2}, {"x": 3, "y": 4}],
        sample_merged=True,
        sample_average=True,
        average_radius=2.5,
    )

    assert result["success"] is True
    assert result["operation"] == "sample_pixels"
    assert result["data"]["points_requested"] == 2
    generated = "\n".join(bridge.calls[-1][1])
    assert "sample_points = [{'x': 1.0, 'y': 2.0}, {'x': 3.0, 'y': 4.0}]" in generated
    assert "image.pick_color(drawables, x, y, True, True, 2.5)" in generated
    assert "samples.append({'x': x, 'y': y, 'rgba': color_to_dict(color), 'hex': color_to_hex(color)})" in generated


@pytest.mark.asyncio
async def test_sample_pixels_expands_grid_and_targets_layer_index() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["sample_pixels"](
        grid={"x": 0, "y": 0, "width": 10, "height": 6, "columns": 3, "rows": 2},
        layer_index=0,
    )

    assert result["success"] is True
    assert result["data"]["points_requested"] == 6
    generated = "\n".join(bridge.calls[-1][1])
    assert "layers = image.get_layers()" in generated
    assert "drawable = layers[0]" in generated
    assert "for row in range(2):" in generated
    assert "for col in range(3):" in generated
    assert "sample_points.append({'x': px, 'y': py})" in generated
    assert "drawable.get_pixel(int(round(x)), int(round(y)))" in generated


@pytest.mark.asyncio
async def test_sample_pixels_rejects_empty_sampling_request() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_color_tools(mcp, bridge)

    result = await mcp.tools["sample_pixels"]()

    assert result["success"] is False
    assert "points or grid" in result["error"]
    assert bridge.calls == []
