"""Physical split checks for native backend operation generators."""

from __future__ import annotations

import ast
from pathlib import Path

from gimp_mcp_pro.tools import native_backend

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src" / "gimp_mcp_pro" / "tools"

EXPECTED_MODULE_OPERATIONS = {
    "native_channels.py": {"edit_channels", "manage_channels"},
    "native_paths.py": {"edit_paths", "create_and_edit_paths", "stroke_or_fill_path"},
    "native_exports.py": {"import_as_layer_with_metadata", "batch_export_variants"},
    "native_pdb.py": {"pdb_introspect_typed", "execute_pdb_call"},
    "native_gegl.py": {"preview_gegl_operation", "apply_gegl_operation"},
    "native_misc.py": {"palette_create_or_update", "safe_python_eval", "manage_guides_and_grid"},
}


def test_native_backend_registry_is_composed_from_split_modules() -> None:
    registry_keys = set(native_backend.NATIVE_OPERATIONS)
    assert registry_keys == set().union(*EXPECTED_MODULE_OPERATIONS.values())
    for module_name, operations in EXPECTED_MODULE_OPERATIONS.items():
        module_path = TOOLS / module_name
        assert module_path.exists(), f"missing split module: {module_name}"
        module_source = module_path.read_text()
        assert "def operations() -> dict[str, NativeOperation]:" in module_source
        for operation in operations:
            assert operation in native_backend.NATIVE_OPERATIONS
            assert repr(operation) in module_source or f'"{operation}"' in module_source


def test_native_backend_module_no_longer_contains_operation_generators() -> None:
    source = (TOOLS / "native_backend.py").read_text()
    tree = ast.parse(source)
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert not {name for name in function_names if name.startswith("_op_")}
    assert "def operations() -> dict[str, NativeOperation]:" not in source
    for module_name in EXPECTED_MODULE_OPERATIONS:
        assert f"from gimp_mcp_pro.tools import {module_name[:-3]}" in source


def test_split_modules_keep_native_backend_core_small() -> None:
    source = (TOOLS / "native_backend.py").read_text()
    assert len(source.splitlines()) < 260
    assert "class CodeBuilder" in source
    assert "def generated_context_helpers" in source
    assert "def build_json_code" in source
