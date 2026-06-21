"""Static verification for easy GIMP 3.2.4 compatibility hardening."""

from __future__ import annotations

import ast
from pathlib import Path

import scripts.compat as compat

from gimp_mcp_pro.models.common import py_literal
from gimp_mcp_pro.tools.layer_tools import _layer_lookup_code
from gimp_mcp_pro.tools.transform_tools import _layer_target

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_py_literal_round_trips_user_controlled_strings() -> None:
    value = "Layer 'quoted'\nname"

    literal = py_literal(value)

    assert ast.literal_eval(literal) == value


def test_layer_lookup_code_uses_safe_python_literals() -> None:
    name = "Layer 'quoted'"

    code = _layer_lookup_code(name, None) + _layer_target(name, None)
    source = "\n".join(code)

    assert ast.parse(source)
    assert "get_layer_by_name" in source
    assert ast.literal_eval(py_literal(name)) == name


def test_plugin_get_gimp_info_reports_324_probe_fields() -> None:
    source = (PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py").read_text()

    assert '"gimp"' in source
    assert "Gimp.version()" in source
    assert "resources_loaded" in source
    assert "reports_version" in source


def test_compat_tool_extractor_counts_async_defs() -> None:
    names = compat.flatten_registry(compat.extract_source_tool_registry())

    assert len(names) == 75
    assert "get_gimp_info" in names
    assert "get_image_bitmap" in names
