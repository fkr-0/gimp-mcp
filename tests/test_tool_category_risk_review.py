"""Schema and coverage guard for tool-category risk review."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts import compat

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "tool-category-risk-review.yml"


def _load_review() -> dict[str, Any]:
    data = yaml.safe_load(REVIEW.read_text())
    assert isinstance(data, dict)
    return data


def test_tool_category_risk_review_covers_every_source_category() -> None:
    """The review artifact must cover every module that registers MCP tools."""
    data = _load_review()
    registry = compat.extract_source_tool_registry()

    assert data["schema_version"] == 1
    assert data["project"] == "gimp-mcp"
    assert data["review_type"] == "tool-category-risk-review"
    assert data["source_registry_total"] == sum(len(names) for names in registry.values())

    reviewed_categories = {category["module"] for category in data["categories"]}
    assert reviewed_categories == set(registry)

    for category in data["categories"]:
        module = category["module"]
        reviewed_tools = {tool["name"] for tool in category["tools"]}
        assert reviewed_tools == set(registry[module])
        assert category["memory_risk"] in {"low", "medium", "high"}
        assert category["file_risk"] in {"low", "medium", "high"}
        assert isinstance(category["findings"], list)
        assert isinstance(category["recommended_next_tests"], list)
        for tool in category["tools"]:
            assert tool["test_coverage"] in {"direct", "matrix-only", "none-found"}
            assert tool["memory_risk"] in {"low", "medium", "high"}
            assert tool["file_risk"] in {"low", "medium", "high"}


def test_tool_category_risk_review_tracks_high_priority_followups() -> None:
    """Risk review should expose actionable followups, not just an inventory."""
    data = _load_review()
    actions = data["high_priority_followups"]

    assert actions
    assert all(action["status"] in {"open", "in_progress", "done"} for action in actions)
    assert any("memory" in action["title"].lower() for action in actions)
    assert any("file" in action["title"].lower() for action in actions)
    assert any("test" in action["title"].lower() for action in actions)


def test_high_priority_followups_are_closed_with_verification_evidence() -> None:
    """Executed high-priority review items must carry evidence before being closed."""
    data = _load_review()
    by_id = {action["id"]: action for action in data["high_priority_followups"]}

    for risk_id in {"RISK-001", "RISK-002", "RISK-003"}:
        action = by_id[risk_id]
        assert action["status"] == "done"
        assert action["completion_evidence"]
        assert action["verification"]
