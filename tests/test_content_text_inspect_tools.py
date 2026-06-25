"""Focused TDD coverage for content-bounds and text-layer inspection features."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_content_bounds_generates_read_only_layer_bounds_scan() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["content_bounds"](
        target="active_layer",
        threshold=0.05,
        include_sample_points=True,
    )

    assert result["success"] is True
    assert result["operation"] == "content_bounds"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_content_bounds__" in generated
    assert "threshold = 0.05" in generated
    assert "include_sample_points = True" in generated
    assert "drawable.get_pixel(x, y)" in generated
    assert "alpha > threshold" in generated
    assert "content_bounds" in generated
    assert "fully_transparent" in generated


@pytest.mark.asyncio
async def test_text_layer_introspection_uses_textlayer_api_without_mutation() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["text_layer_introspection"](
        layer_name="Headline",
        include_font_details=True,
    )

    assert result["success"] is True
    assert result["operation"] == "text_layer_introspection"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_text_layer_introspection__" in generated
    assert "image.get_layer_by_name('Headline')" in generated
    assert "Gimp.TextLayer.get_by_id(layer.get_id())" in generated
    assert "text_layer.get_text()" in generated
    assert "text_layer.get_font()" in generated
    assert "text_layer.get_font_size()" in generated
    assert "text_layer.set_" not in generated


@pytest.mark.asyncio
async def test_content_bounds_rejects_invalid_threshold_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["content_bounds"](threshold=1.5)

    assert result["success"] is False
    assert "threshold" in result["error"]
    assert bridge.calls == []
