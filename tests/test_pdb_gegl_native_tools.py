"""Native placement tests for formerly unimplemented roadmap tools."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.filter_tools import register_filter_tools
from gimp_mcp_pro.tools.pdb_tools import register_pdb_tools
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
async def test_execute_pdb_call_lives_in_pdb_tools_with_allowlist_and_dry_run() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_pdb_tools(mcp, bridge)

    result = await mcp.tools["execute_pdb_call"](
        procedure="gimp-image-get-width",
        arguments={"image": "$active_image"},
        dry_run=True,
    )

    assert result["success"] is True
    assert result["operation"] == "execute_pdb_call"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_execute_pdb_call__" in generated
    assert "procedure = 'gimp-image-get-width'" in generated
    assert "allowed_procedures" in generated
    assert "pdb.lookup_procedure(procedure)" in generated
    assert "proc.create_config()" in generated
    assert "if not dry_run:" in generated
    assert "argument_schema_errors" in generated


@pytest.mark.asyncio
async def test_execute_pdb_call_rejects_denied_procedure_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_pdb_tools(mcp, bridge)

    result = await mcp.tools["execute_pdb_call"](
        procedure="gimp-file-save",
        arguments={},
        dry_run=True,
    )

    assert result["success"] is False
    assert "allowlist" in result["error"].lower()
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_apply_gegl_operation_lives_in_filter_tools_with_schema_and_lifecycle() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["apply_gegl_operation"](
        target={"layer_index": 0},
        operation="gegl:gaussian-blur",
        properties={"std-dev-x": 3.0, "std-dev-y": 4.0},
        dry_run=False,
    )

    assert result["success"] is True
    assert result["operation"] == "apply_gegl_operation"
    generated = "\n".join(bridge.calls[-1][1])
    assert "# __gimp_mcp_apply_gegl_operation__" in generated
    assert "operation_name = 'gegl:gaussian-blur'" in generated
    assert "allowed_properties" in generated
    assert "# __gimp_mcp_filter_lifecycle__" in generated
    assert "cfg.set_property('std-dev-x', 3.0)" in generated
    assert "cfg.set_property('std-dev-y', 4.0)" in generated
    assert "changed_bounds" in generated


@pytest.mark.asyncio
async def test_apply_gegl_operation_rejects_unknown_property_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_filter_tools(mcp, bridge)

    result = await mcp.tools["apply_gegl_operation"](
        target={"layer_index": 0},
        operation="gegl:gaussian-blur",
        properties={"made-up": 1.0},
    )

    assert result["success"] is False
    assert "property" in result["error"].lower()
    assert bridge.calls == []
