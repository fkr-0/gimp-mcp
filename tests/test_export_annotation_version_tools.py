"""Focused TDD coverage for export, annotation, and version-stamp roadmap candidates."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.image_tools import register_image_tools
from gimp_mcp_pro.tools.layer_tools import register_layer_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_export_with_manifest_generates_export_and_sidecar_manifest() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_image_tools(mcp, bridge)

    result = await mcp.tools["export_with_manifest"](
        format="png",
        destination="/tmp/gimp-mcp-export.png",
        include_sidecar=True,
        export_settings={"compression": 9},
    )

    assert result["success"] is True
    assert result["operation"] == "export_with_manifest"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_export_with_manifest__" in generated
    assert "format_name = 'png'" in generated
    assert "destination = '/tmp/gimp-mcp-export.png'" in generated
    assert "file-png-export" in generated
    assert "manifest" in generated
    assert "manifest_path" in generated
    assert "json.dump(manifest" in generated


@pytest.mark.asyncio
async def test_visual_annotation_layer_generates_mcp_tagged_temporary_layer() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["create_visual_annotation_layer"](
        annotations=[{"type": "box", "x": 1, "y": 2, "width": 30, "height": 40, "label": "target"}],
        layer_name="MCP Annotations",
        temporary=True,
    )

    assert result["success"] is True
    assert result["operation"] == "create_visual_annotation_layer"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_create_visual_annotation_layer__" in generated
    assert "annotations = [{'type': 'box'" in generated
    assert "layer_name = 'MCP Annotations'" in generated
    assert "Gimp.Layer.new" in generated
    assert "gimp-mcp-annotation" in generated
    assert "annotation_layer_id" in generated


@pytest.mark.asyncio
async def test_remove_visual_annotations_requires_scope_and_removes_mcp_layers_only() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    rejected = await mcp.tools["remove_visual_annotations"]()
    assert rejected["success"] is False
    assert bridge.calls == []

    result = await mcp.tools["remove_visual_annotations"](
        annotation_layer_ids=[42],
        remove_all_mcp_annotations=False,
    )

    assert result["success"] is True
    assert result["operation"] == "remove_visual_annotations"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_remove_visual_annotations__" in generated
    assert "annotation_layer_ids = [42]" in generated
    assert "image.remove_layer(layer)" in generated
    assert "removed_layer_ids" in generated
    assert "gimp-mcp-annotation" in generated


@pytest.mark.asyncio
async def test_layer_version_stamp_attaches_namespaced_metadata() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_layer_tools(mcp, bridge)

    result = await mcp.tools["layer_version_stamp"](
        target={"layer_name": "Layer 1"},
        metadata={"operation": "test", "revision": 2},
        merge=True,
    )

    assert result["success"] is True
    assert result["operation"] == "layer_version_stamp"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_version_stamp__" in generated
    assert "target = {'layer_name': 'Layer 1'}" in generated
    assert "metadata_namespace = 'gimp-mcp-pro'" in generated
    assert "existing_metadata" in generated
    assert "Gimp.Parasite.new" in generated
    assert "attach_parasite" in generated
