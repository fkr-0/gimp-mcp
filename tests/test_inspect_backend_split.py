"""Architecture tests for the inspect tools backend split."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src" / "gimp_mcp_pro" / "tools"

EXPECTED_MODULES = {
    "inspect_context_backend.py": {
        "register_context_inspect_tools",
        "_context_explanation_code",
        "_document_state_code",
        "_layer_tree_code",
        "_session_capabilities_code",
    },
    "inspect_geometry_backend.py": {
        "register_geometry_inspect_tools",
        "_measure_geometry_code",
        "_layer_report_code",
        "_export_checklist_code",
        "_content_bounds_code",
        "_text_layer_introspection_code",
    },
    "inspect_snapshot_backend.py": {
        "register_snapshot_inspect_tools",
        "_compare_snapshot_data",
        "_assertion_result",
    },
    "inspect_bitmap_backend.py": {
        "register_bitmap_inspect_tools",
        "_region_sample_code",
        "_contact_sheet_code",
    },
}


def test_inspect_backend_split_modules_exist_with_registrars() -> None:
    for module_name, required_symbols in EXPECTED_MODULES.items():
        source_path = TOOLS / module_name
        assert source_path.exists(), f"missing split module: {module_name}"
        source = source_path.read_text()
        tree = ast.parse(source)
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        assert required_symbols <= function_names


def test_inspect_tools_is_a_thin_registrar_after_split() -> None:
    source_path = TOOLS / "inspect_tools.py"
    source = source_path.read_text()
    assert len(source.splitlines()) < 120
    tree = ast.parse(source)
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert function_names == {"register_inspect_tools"}
    assert "register_context_inspect_tools(mcp, bridge)" in source
    assert "register_geometry_inspect_tools(mcp, bridge)" in source
    assert "register_snapshot_inspect_tools(mcp, bridge)" in source
    assert "register_bitmap_inspect_tools(mcp, bridge)" in source
