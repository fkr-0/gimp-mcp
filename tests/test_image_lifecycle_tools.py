"""Lifecycle and leak-safety tests for image category generated code."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.image_tools import register_image_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_export_image_releases_pdb_config_and_file_refs() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["export_image"](
        file_path="/tmp/gimp-mcp-export.png",
        format="png",
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_image_export_lifecycle__" in generated
    assert "file_obj = None" in generated
    assert "export_proc = None" in generated
    assert "config = None" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "export_proc.run(config)" in generated
    assert "del config" in generated
    assert "del export_proc" in generated
    assert "del file_obj" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_export_with_manifest_releases_export_config_and_sidecar_refs() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["export_with_manifest"](
        format="png",
        destination="/tmp/gimp-mcp-export.png",
        include_sidecar=True,
    )

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_export_with_manifest_lifecycle__" in generated
    assert "file_obj = None" in generated
    assert "export_proc = None" in generated
    assert "config = None" in generated
    assert "manifest_fh = None" in generated
    assert "try:" in generated
    assert "finally:" in generated
    assert "manifest_fh.close()" in generated
    assert "del manifest_fh" in generated
    assert "del config" in generated
    assert "del export_proc" in generated
    assert "del file_obj" in generated
    assert "gc.collect()" in generated


@pytest.mark.asyncio
async def test_duplicate_image_releases_display_reference_without_deleting_duplicate() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["duplicate_image"]()

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_duplicate_image_lifecycle__" in generated
    assert "new_image = None" in generated
    assert "display = None" in generated
    assert "display = Gimp.Display.new(new_image)" in generated
    assert "del display" in generated
    assert "gc.collect()" in generated
    assert "delete(new_image)" not in generated


@pytest.mark.asyncio
async def test_export_image_rejects_parent_traversal_destination_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["export_image"]("/tmp/../etc/passwd", format="png")

    assert result["success"] is False
    assert "unsafe" in result["error"].lower()
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_export_with_manifest_rejects_parent_traversal_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["export_with_manifest"](
        format="png",
        destination="/tmp/../etc/passwd",
    )

    assert result["success"] is False
    assert "unsafe" in result["error"].lower()
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_batch_export_variants_rejects_parent_traversal_base_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["batch_export_variants"](
        variants=[{"format": "png", "width": 64, "height": 64}],
        base_path="/tmp/../etc/gimp-mcp",
    )

    assert result["success"] is False
    assert "unsafe" in result["error"].lower()
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_import_as_layer_rejects_parent_traversal_source_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["import_as_layer_with_metadata"]("/tmp/../etc/passwd")

    assert result["success"] is False
    assert "unsafe" in result["error"].lower()
    assert bridge.calls == []
