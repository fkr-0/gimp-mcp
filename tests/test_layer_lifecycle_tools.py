"""Lifecycle and leak-safety tests for layer category generated code."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.layer_tools import register_layer_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_create_visual_annotation_layer_cleans_up_partial_layer_on_failure() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["create_visual_annotation_layer"](
        annotations=[{"type": "box", "x": 1, "y": 2, "width": 10, "height": 12}],
        layer_name="MCP temporary annotations",
        temporary=True,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_annotation_lifecycle__" in generated
    assert "layer = None" in generated
    assert "parasite = None" in generated
    assert "try:" in generated
    assert "except Exception:" in generated
    assert "image.remove_layer(layer)" in generated
    assert "raise" in generated
    assert "del parasite" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_layer_version_stamp_replaces_existing_parasite_and_releases_refs() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["layer_version_stamp"](
        target={"layer_name": "Paint"},
        metadata={"operation": "paint"},
        merge=True,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_version_lifecycle__" in generated
    assert "old_parasite = None" in generated
    assert "parasite = None" in generated
    assert "layer.detach_parasite(metadata_namespace)" in generated
    assert "layer.attach_parasite(parasite)" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "del old_parasite" in generated
    assert "del parasite" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_set_layer_mode_has_focused_generated_code_coverage() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["set_layer_mode"](blend_mode="multiply", layer_name="Paint")

    assert result["success"] is True
    assert result["operation"] == "set_layer_mode"
    generated = "\n".join(bridge.calls[-1][1])
    assert "target = image.get_layer_by_name('Paint')" in generated
    assert "target.set_mode(Gimp.LayerMode.MULTIPLY)" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_set_layer_mode_rejects_unknown_mode_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["set_layer_mode"](blend_mode="surely-not-a-mode")

    assert result["success"] is False
    assert "unknown blend mode" in result["error"].lower()
    assert bridge.calls == []
