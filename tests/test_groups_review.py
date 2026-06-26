"""Artifact-free guards for tool-group review completion."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.compat import extract_source_tool_registry

ROOT = Path(__file__).resolve().parents[1]

GENERIC_COVERAGE_TESTS = {
    "test_async_tool_registry.py",
    "test_groups_review.py",
    "test_tool_invocation_matrix.py",
}


def _source_tool_pairs() -> list[tuple[str, str]]:
    registry = extract_source_tool_registry()
    pairs: list[tuple[str, str]] = []
    for group_name, tool_names in registry.items():
        if not group_name.endswith("_tools"):
            continue
        pairs.extend((group_name, tool_name) for tool_name in tool_names)
    return sorted(pairs)


def _focused_test_text() -> str:
    test_files = [
        path
        for path in (ROOT / "tests").glob("test_*.py")
        if path.name not in GENERIC_COVERAGE_TESTS
    ]
    return "\n".join(path.read_text() for path in test_files)


def test_groups_yml_artifact_is_retired_after_all_group_issues_have_tests() -> None:
    """The temporary group review report should not outlive the tests that replaced it."""
    assert not (ROOT / "groups.yml").exists()


def test_every_source_registered_tool_has_focused_non_matrix_test_reference() -> None:
    """No source-registered MCP tool may rely only on the generic matrix/registry tests."""
    focused_test_text = _focused_test_text()
    missing: list[str] = []
    pairs = _source_tool_pairs()

    for group_name, tool_name in pairs:
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(tool_name)}(?![A-Za-z0-9_])")
        if not pattern.search(focused_test_text):
            missing.append(f"{group_name}.{tool_name}")

    assert len(pairs) == 183
    assert missing == []


def test_all_tool_groups_remain_represented_by_source_registry() -> None:
    """Guard the expected tool-group surface now that the YAML report is gone."""
    registry = extract_source_tool_registry()
    assert {group_name for group_name in registry if group_name.endswith("_tools")} == {
        "agent_tools",
        "color_tools",
        "drawing_tools",
        "filter_tools",
        "flow_tools",
        "gimp_dev_tools",
        "history_tools",
        "image_tools",
        "inspect_tools",
        "layer_tools",
        "path_tools",
        "pdb_tools",
        "selection_tools",
        "target_tools",
        "transform_tools",
    }
