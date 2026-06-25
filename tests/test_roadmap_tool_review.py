"""Review guardrails for temporary roadmap tool wrappers."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import yaml

from scripts import compat

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_SOURCE = ROOT / "src" / "gimp_mcp_pro" / "tools" / "roadmap_tools.py"
FEATURES = ROOT / "features.yml"
TASKS = ROOT / "tasks.issues.yml"

ROADMAP_TOOL_TARGETS = {
    "edit_channels": "src/gimp_mcp_pro/tools/layer_tools.py",
    "manage_channels": "src/gimp_mcp_pro/tools/layer_tools.py",
    "edit_paths": "src/gimp_mcp_pro/tools/path_tools.py",
    "create_and_edit_paths": "src/gimp_mcp_pro/tools/path_tools.py",
    "stroke_or_fill_path": "src/gimp_mcp_pro/tools/path_tools.py",
    "palette_create_or_update": "src/gimp_mcp_pro/tools/color_tools.py",
    "import_as_layer_with_metadata": "src/gimp_mcp_pro/tools/image_tools.py",
    "batch_export_variants": "src/gimp_mcp_pro/tools/image_tools.py",
    "pdb_introspect_typed": "src/gimp_mcp_pro/tools/pdb_tools.py",
    "execute_pdb_call": "src/gimp_mcp_pro/tools/pdb_tools.py",
    "safe_python_eval": "src/gimp_mcp_pro/tools/pdb_tools.py",
    "manage_guides_and_grid": "src/gimp_mcp_pro/tools/image_tools.py",
    "preview_gegl_operation": "src/gimp_mcp_pro/tools/filter_tools.py",
    "apply_gegl_operation": "src/gimp_mcp_pro/tools/filter_tools.py",
}


def _roadmap_tool_names() -> list[str]:
    tree = ast.parse(ROADMAP_SOURCE.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and any(
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Attribute)
            and dec.func.attr == "tool"
            for dec in node.decorator_list
        ):
            names.append(node.name)
    return sorted(names)


def _feature_by_tool() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(FEATURES.read_text())
    return {
        str(feature.get("implemented_tool") or feature.get("name")): feature
        for feature in data["features"]
    }


def test_roadmap_tools_have_been_promoted_to_category_modules() -> None:
    """Finalized roadmap work must no longer register temporary roadmap wrappers."""
    assert _roadmap_tool_names() == []

    for tool_name, target_file in ROADMAP_TOOL_TARGETS.items():
        target_source = (ROOT / target_file).read_text()
        assert f"async def {tool_name}(" in target_source
        assert f"__gimp_mcp_{tool_name}__" in target_source


def test_features_yml_marks_promoted_roadmap_tools_finalized() -> None:
    """Promoted roadmap tools are no longer kept in the open backlog."""
    features = _feature_by_tool()
    for tool_name, target_file in ROADMAP_TOOL_TARGETS.items():
        feature = features[tool_name]
        assert feature["status"] == "implemented_this_pass"
        assert feature["target_file"] == target_file
        assert feature["verification"]

    tasks = yaml.safe_load(TASKS.read_text())
    issue = next(item for item in tasks["issues"] if item["id"] == "GIMP-MCP-005")
    assert issue["status"] == "implemented"
    assert issue["remaining_open_features"] == []


def test_implemented_roadmap_issue_has_no_stale_partial_or_duplicate_completion_entries() -> None:
    """Finished roadmap tools must not remain as partial or duplicate task entries."""
    tasks = yaml.safe_load(TASKS.read_text())
    issue = next(item for item in tasks["issues"] if item["id"] == "GIMP-MCP-005")

    assert issue["status"] == "implemented"
    assert issue["remaining_open_features"] == []
    completed = issue.get("completed_this_pass", [])
    feature_ids = [entry["feature_id"] for entry in completed]
    assert len(feature_ids) == len(set(feature_ids))
    assert all("status" not in entry for entry in completed)

    roadmap = yaml.safe_load(FEATURES.read_text())
    implemented_this_pass = {
        (feature["id"], feature["name"])
        for feature in roadmap["features"]
        if feature["status"] == "implemented_this_pass"
    }
    completed_pairs = {(entry["feature_id"], entry["tool"]) for entry in completed}
    assert completed_pairs == implemented_this_pass

    registry = compat.extract_source_tool_registry()
    assert issue["registry_total"] == sum(len(names) for names in registry.values())


def test_promoted_tools_are_not_tracked_by_missing_roadmap_fixtures() -> None:
    """Finished and native-tested tools should not live in missing-roadmap fixtures."""
    stale_paths = [
        ROOT / "tests" / "roadmap_tool_cases.py",
        ROOT / "tests" / "test_missing_roadmap_tools.py",
    ]
    for path in stale_paths:
        assert not path.exists()
