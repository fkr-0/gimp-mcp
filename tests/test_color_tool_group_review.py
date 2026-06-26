"""Guard the color tool-group review artifact against drifting from source."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import yaml

from scripts import compat

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "tool-group-review-color-tools.yml"


def _load_review() -> dict[str, Any]:
    data = yaml.safe_load(REVIEW.read_text())
    assert isinstance(data, dict)
    return data


def test_color_tool_group_review_covers_source_tools_and_core_risks() -> None:
    registry = compat.extract_source_tool_registry()
    expected_tools = set(registry["color_tools"])
    review = _load_review()

    assert review["schema_version"] == 1
    assert review["tool_group"] == "color_tools"
    assert review["source_path"] == "src/gimp_mcp_pro/tools/color_tools.py"
    assert review["source_tool_count"] == len(expected_tools)
    assert {tool["name"] for tool in review["tools"]} == expected_tools

    finding_ids = {finding["id"] for finding in review["findings"]}
    assert "COLOR-DESIGN-001" in finding_ids
    assert "COLOR-LIFECYCLE-001" in finding_ids
    assert "COLOR-TEST-001" in finding_ids
    assert any(finding["severity"] == "high" for finding in review["findings"])

    for finding in review["findings"]:
        assert finding["evidence"]
        assert finding["recommendation"]


def test_color_tool_group_review_records_verification_commands() -> None:
    review = _load_review()
    commands = {entry["command"] for entry in review["verification"]}

    assert any("tests/test_color" in command for command in commands)
    assert any("scripts/project.py check" in command for command in commands)


def test_color_tools_uses_extracted_backend_helpers() -> None:
    """Design fix: keep color_tools focused on MCP handlers, not generated helper internals."""
    backend = ROOT / "src" / "gimp_mcp_pro" / "tools" / "color_backend.py"
    color_source = ROOT / "src" / "gimp_mcp_pro" / "tools" / "color_tools.py"
    assert backend.exists()

    color_tree = ast.parse(color_source.read_text())
    color_defs = {node.name for node in ast.walk(color_tree) if isinstance(node, ast.FunctionDef)}
    extracted_helpers = {
        "_color_preamble",
        "_color_adjustment_lifecycle",
        "_normalise_sample_points",
        "_sample_pixels_code",
        "_palette_analysis_code",
        "_resource_common_code",
        "_set_paint_context_code",
    }
    assert color_defs.isdisjoint(extracted_helpers)
    assert len(color_source.read_text().splitlines()) < 1250


def test_color_tool_group_review_findings_are_resolved_with_evidence() -> None:
    review = _load_review()
    by_id = {finding["id"]: finding for finding in review["findings"]}

    for finding_id in {
        "COLOR-DESIGN-001",
        "COLOR-LIFECYCLE-001",
        "COLOR-TEST-001",
        "COLOR-IMPLEMENTATION-001",
    }:
        finding = by_id[finding_id]
        assert finding["status"] == "resolved"
        assert finding["completion_evidence"]

    assert review["summary"]["overall_risk"] == "medium"
    assert "src/gimp_mcp_pro/tools/color_backend.py" in review["summary"]["completed_fixes"]
