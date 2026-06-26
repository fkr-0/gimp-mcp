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


def test_plugin_menu_run_uses_gimp_persistent_lifecycle() -> None:
    source = (PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py").read_text()

    assert "procedure.persistent_ready()" in source
    assert "self.persistent_enable()" in source
    assert "GLib.MainLoop()" in source


def test_server_procedure_does_not_register_invalid_image_menu_path() -> None:
    source = (PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py").read_text()

    assert 'procedure.add_menu_path("<Image>/Filters/Development/GIMP MCP Pro")' not in source
    assert "plug-in-mcp-pro-server" in source
    assert "Gimp.Procedure.new(self, name, Gimp.PDBProcType.PERSISTENT, self.run, None)" in source


def test_plugin_marshals_requests_to_gimp_thread() -> None:
    source = (PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py").read_text()

    assert "def _dispatch_on_gimp_thread" in source
    assert "GLib.idle_add" in source
    assert "queue.Queue" in source
    assert "response = self._dispatch_on_gimp_thread(request)" in source


def test_plugin_discovers_and_registers_repeatable_flows() -> None:
    source = (PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py").read_text()

    assert "plug-in-mcp-pro-autostart" in source
    assert "_load_pinned_flows" in source
    assert "<Image>/Filters/Repeatable Flows/" in source
    assert "Browse All Flows" in source
    assert "Manage Flows" in source
    assert "add_boolean_argument" in source
    assert "add_int_argument" in source
    assert "add_double_argument" in source
    assert "add_string_argument" in source
    assert "Gtk.SearchEntry" in source
    assert "Gtk.ComboBoxText" in source
    assert "_update_flow_lifecycle" in source
    assert "_save_flow_json" in source
    assert "_show_final_review" in source
    assert '"Rollback"' in source
    assert "image.undo()" in source


def test_plugin_launches_flow_runner_without_shell() -> None:
    source = (PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py").read_text()

    assert "def _runner_argv" in source
    assert "subprocess.Popen(" in source
    assert '"--params-json"' in source
    assert "shell=True" not in source


def test_compat_tool_extractor_counts_async_defs() -> None:
    names = compat.flatten_registry(compat.extract_source_tool_registry())

    assert len(names) == 176
    assert "get_gimp_info" in names
    assert "get_image_bitmap" in names
