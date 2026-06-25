"""Validation tests for the future MCP tool roadmap."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "features.yml"
EXPECTED_CATEGORIES = {"observe", "target", "transaction", "edit", "verify", "asset", "script"}
EXPECTED_GROUPS = ("first_wave", "second_wave", "later_wave")


def load_roadmap() -> dict[str, Any]:
    """Load the YAML roadmap as a dictionary."""
    data = yaml.safe_load(ROADMAP.read_text())
    assert isinstance(data, dict)
    return data


def test_features_roadmap_has_valid_top_level_shape() -> None:
    """The roadmap is a versioned planning artifact for the 3.2.4 branch."""
    data = load_roadmap()

    assert data["schema_version"] == 1
    assert data["branch"] == "3.2.4"
    assert data["status"] == "active-reconciled-2026-06-23"
    assert data["principles"]
    assert data["priority_legend"]
    assert data["open_design_questions"]

    categories = data["categories"]
    assert {category["id"] for category in categories} == EXPECTED_CATEGORIES
    assert all(category["title"] and category["why"] for category in categories)


def test_features_have_stable_ids_and_required_fields() -> None:
    """Each future feature has a stable ID, priority, shape, and acceptance criteria."""
    data = load_roadmap()
    features = data["features"]
    category_ids = {category["id"] for category in data["categories"]}

    assert len(features) == 57
    assert [feature["id"] for feature in features] == [
        f"FEAT-{index:03d}" for index in range(1, len(features) + 1)
    ]

    for feature in features:
        assert feature["category"] in category_ids
        assert feature["priority"] in {"P0", "P1", "P2", "P3"}
        assert re.fullmatch(r"[a-z][a-z0-9_]*", feature["name"])
        assert feature["summary"]
        assert feature["agent_value"]
        assert feature["acceptance"]

        shape = feature["proposed_tool_shape"]
        assert "input" in shape
        assert "output" in shape


def test_implementation_groups_cover_every_feature_once() -> None:
    """Wave groupings are complete, non-overlapping, and reference known features."""
    data = load_roadmap()
    features = data["features"]
    feature_ids = {feature["id"] for feature in features}
    groups = data["implementation_groups"]

    grouped_ids: list[str] = []
    for group_name in EXPECTED_GROUPS:
        group = groups[group_name]
        assert group["rationale"]
        assert group["feature_ids"]
        grouped_ids.extend(group["feature_ids"])

    assert set(grouped_ids) == feature_ids
    assert len(grouped_ids) == len(set(grouped_ids))


def test_first_wave_prioritizes_agent_safety_and_observation() -> None:
    """The first implementation wave stays centered on safe autonomous operation."""
    data = load_roadmap()
    first_wave = set(data["implementation_groups"]["first_wave"]["feature_ids"])

    assert {
        "FEAT-001",  # observe_document_state
        "FEAT-002",  # get_layer_tree_detailed
        "FEAT-003",  # observe_region
        "FEAT-007",  # resolve_target
        "FEAT-008",  # validate_targets
        "FEAT-010",  # begin_edit_transaction
        "FEAT-011",  # end_edit_transaction
        "FEAT-012",  # rollback_transaction
        "FEAT-045",  # session_capabilities
    } <= first_wave

    priorities = {feature["id"]: feature["priority"] for feature in data["features"]}
    assert {priorities[feature_id] for feature_id in first_wave} == {"P0"}


def test_roadmap_records_safe_live_testing_policy() -> None:
    """Future tools must stay tied to clean-profile spawned/Xvfb verification."""
    data = load_roadmap()
    joined_principles = "\n".join(data["principles"])

    assert "clean-profile spawned smoke tests under Xvfb" in joined_principles
    assert "localhost-only bridge" in joined_principles


def test_selected_first_wave_features_are_marked_implemented() -> None:
    """The reconciled first-wave features are tagged implemented."""
    data = load_roadmap()
    selected = {
        "FEAT-001",
        "FEAT-002",
        "FEAT-007",
        "FEAT-008",
        "FEAT-010",
        "FEAT-011",
        "FEAT-012",
        "FEAT-045",
    }
    statuses = {feature["id"]: feature.get("status") for feature in data["features"]}

    assert {statuses[feature_id] for feature_id in selected} == {"implemented"}


def test_current_feature_backlog_excludes_verified_tool_features() -> None:
    """The active task backlog must not list features already covered by registered tools."""
    roadmap = load_roadmap()
    feature_by_id = {feature["id"]: feature for feature in roadmap["features"]}
    implemented_this_pass = {
        "FEAT-040": "generate_layer_report",
        "FEAT-041": "prepare_export_checklist",
        "FEAT-043": "content_bounds",
        "FEAT-051": "text_layer_introspection",
    }

    for feature_id, tool_name in implemented_this_pass.items():
        feature = feature_by_id[feature_id]
        assert feature.get("status") == "implemented_this_pass"
        assert feature.get("implemented_tool") == tool_name
        assert feature.get("verification")

    issues = yaml.safe_load((ROOT / "tasks.issues.yml").read_text())
    feature_issue = next(issue for issue in issues["issues"] if issue["id"] == "GIMP-MCP-005")
    remaining = set(feature_issue.get("remaining_open_features", []))
    assert remaining.isdisjoint(implemented_this_pass)
