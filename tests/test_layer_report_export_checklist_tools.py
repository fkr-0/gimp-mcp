"""Focused TDD coverage for layer-report and export-checklist features."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_generate_layer_report_flags_common_layer_and_export_warnings() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["generate_layer_report"](
        include_previews=False,
        include_warnings=True,
        include_markdown=True,
    )

    assert result["success"] is True
    assert result["operation"] == "generate_layer_report"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_layer_report__" in generated
    assert "include_warnings = True" in generated
    assert "include_markdown = True" in generated
    assert "layer.get_visible()" in generated
    assert "layer.get_width()" in generated
    assert "layer.get_height()" in generated
    assert "Gimp.TextLayer.get_by_id(layer.get_id())" in generated
    assert "hidden_layer" in generated
    assert "empty_layer" in generated
    assert "out_of_canvas" in generated
    assert "missing_font" in generated
    assert "unsupported_export_state" in generated


@pytest.mark.asyncio
async def test_prepare_export_checklist_reports_format_limits_without_exporting() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["prepare_export_checklist"](
        formats=["png", "jpeg", "xcf"],
        require_alpha=True,
        require_layers_preserved=True,
    )

    assert result["success"] is True
    assert result["operation"] == "prepare_export_checklist"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_export_checklist__" in generated
    assert "formats = ['png', 'jpeg', 'xcf']" in generated
    assert "require_alpha = True" in generated
    assert "require_layers_preserved = True" in generated
    assert "format_limitations" in generated
    assert "alpha_loss" in generated
    assert "layers_will_flatten" in generated
    assert "recommended_settings" in generated
    assert "file-png-export" in generated
    assert "file-jpeg-export" in generated
    assert "Gimp.file_save" not in generated
    assert "export_image" not in generated


@pytest.mark.asyncio
async def test_prepare_export_checklist_rejects_unsupported_format_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_inspect_tools(mcp, bridge)

    result = await mcp.tools["prepare_export_checklist"](
        formats=["png", "exe"],
    )

    assert result["success"] is False
    assert "unsupported" in result["error"].lower()
    assert bridge.calls == []
