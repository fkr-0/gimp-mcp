"""Focused TDD coverage for edit-safety feature tools."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.filter_tools import register_filter_tools
from gimp_mcp_pro.tools.transform_tools import register_transform_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_commit_filter_preview_commit_wraps_transaction_and_promotes_preview() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["commit_filter_preview"](
        preview_id="Preview: gegl:gaussian-blur",
        action="commit",
        committed_name="Committed blur",
    )

    assert result["success"] is True
    assert result["operation"] == "commit_filter_preview"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_commit_filter_preview__" in generated
    assert "preview_id = 'Preview: gegl:gaussian-blur'" in generated
    assert "action = 'commit'" in generated
    assert "image.undo_group_start()" in generated
    assert "image.undo_group_end()" in generated
    assert "preview_layer.set_name('Committed blur')" in generated
    assert "committed" in generated
    assert "image.remove_layer(preview_layer)" not in generated


@pytest.mark.asyncio
async def test_commit_filter_preview_discard_removes_temporary_layer() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["commit_filter_preview"](
        preview_id="Preview: gegl:gaussian-blur",
        action="discard",
    )

    assert result["success"] is True
    assert result["operation"] == "commit_filter_preview"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_commit_filter_preview__" in generated
    assert "action = 'discard'" in generated
    assert "image.remove_layer(preview_layer)" in generated
    assert "discarded" in generated


@pytest.mark.asyncio
async def test_commit_filter_preview_rejects_unknown_action_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["commit_filter_preview"](
        preview_id="Preview: gegl:gaussian-blur",
        action="maybe",
    )

    assert result["success"] is False
    assert "action" in result["error"].lower()
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_smart_crop_or_resize_dry_run_reports_clip_without_mutation() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["smart_crop_or_resize"](
        mode="crop",
        target_size={"width": 320, "height": 200},
        anchor="center",
        preserve_layers=True,
        dry_run=True,
    )

    assert result["success"] is True
    assert result["operation"] == "smart_crop_or_resize"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_smart_crop_or_resize__" in generated
    assert "mode = 'crop'" in generated
    assert "target_width = 320" in generated
    assert "target_height = 200" in generated
    assert "anchor = 'center'" in generated
    assert "dry_run = True" in generated
    assert "would_clip" in generated
    assert "old_dimensions" in generated
    assert "new_dimensions" in generated
    assert "if not dry_run:" in generated
    assert "image.resize(target_width, target_height" in generated


@pytest.mark.asyncio
async def test_smart_crop_or_resize_pad_sets_background_and_preserves_layers() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["smart_crop_or_resize"](
        mode="pad",
        target_size={"width": 1024, "height": 768},
        anchor="bottom_right",
        preserve_layers=True,
        background="#ffffff",
        dry_run=False,
    )

    assert result["success"] is True
    assert result["operation"] == "smart_crop_or_resize"
    generated = "\n".join(bridge.calls[-1][1])
    assert "mode = 'pad'" in generated
    assert "target_width = 1024" in generated
    assert "target_height = 768" in generated
    assert "anchor = 'bottom_right'" in generated
    assert "Gimp.context_set_background(Gegl.Color.new('#ffffff'))" in generated
    assert "image.resize(target_width, target_height" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_smart_crop_or_resize_rejects_invalid_mode_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_transform_tools(mcp, bridge)

    result = await mcp.tools["smart_crop_or_resize"](
        mode="warp",
        target_size={"width": 1, "height": 1},
    )

    assert result["success"] is False
    assert "mode" in result["error"].lower()
    assert bridge.calls == []
