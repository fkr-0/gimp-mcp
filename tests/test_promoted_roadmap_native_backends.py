"""Native-backend checks for roadmap tools promoted into category modules."""

from __future__ import annotations

import pytest

from tests.promoted_tool_cases import PROMOTED_TOOL_CASES
from tests.test_tool_generated_code_paths import ScriptedBridge, registered_tools

NATIVE_EXPECTATIONS = {
    "edit_channels": ["image.get_channels()", "__gimp_mcp_edit_channels__"],
    "manage_channels": ["image.get_channels()", "__gimp_mcp_manage_channels__"],
    "edit_paths": ["image.get_paths()", "__gimp_mcp_edit_paths__"],
    "create_and_edit_paths": ["Gimp.Path.new", "stroke_new_from_points", "image.insert_path"],
    "stroke_or_fill_path": ["image.get_paths()", "edit_stroke_item"],
    "palette_create_or_update": ["Gimp.context_get_palette", "Gimp.Palette"],
    "import_as_layer_with_metadata": [
        "Gio.File.new_for_path",
        "file_load_layer",
        "attach_parasite",
    ],
    "batch_export_variants": ["lookup_procedure", "create_config", "export_proc.run"],
    "pdb_introspect_typed": ["query_procedures", "lookup_procedure", "create_config"],
    "execute_pdb_call": ["ALLOWED_PDB_PROCEDURES", "lookup_procedure", "create_config"],
    "safe_python_eval": ["ast.parse", "SAFE_EVAL_BUILTINS", "redirect_stdout"],
    "manage_guides_and_grid": ["image.find_next_guide", "image.add_hguide", "image.add_vguide"],
    "preview_gegl_operation": ["Gimp.DrawableFilter.new", "image.duplicate()", "get_image_bitmap"],
    "apply_gegl_operation": ["Gimp.DrawableFilter.new", "merge_filter", "ALLOWED_GEGL_OPERATIONS"],
}


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(NATIVE_EXPECTATIONS))
async def test_promoted_roadmap_tool_generates_native_backend_code(tool_name: str) -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)
    case = PROMOTED_TOOL_CASES[tool_name]

    result = await tools[tool_name](**case["kwargs"])

    assert result["success"] is True
    generated = "\n".join(bridge.calls[-1][1])
    for expected in NATIVE_EXPECTATIONS[tool_name]:
        assert expected in generated


@pytest.mark.asyncio
async def test_safe_python_eval_is_disabled_by_default_before_bridge_call() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["safe_python_eval"]("1 + 1")

    assert result["success"] is False
    assert "disabled" in result["error"].lower()
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_batch_export_variants_rejects_unsupported_format_before_bridge_call() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["batch_export_variants"](
        variants=[{"format": "exe", "width": 64, "height": 64}],
        base_path="/tmp/gimp-mcp-variant",
    )

    assert result["success"] is False
    assert "unsupported" in result["error"].lower()
    assert bridge.calls == []
