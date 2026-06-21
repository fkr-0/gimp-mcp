"""Tests for the GIMP 3.2.4 compatibility contract tooling."""

from __future__ import annotations

from pathlib import Path

import scripts.compat as compat


def test_compat_contract_matches_source_tool_registry() -> None:
    contract = compat.load_contract()

    failures = compat.validate_contract(contract)

    assert failures == []


def test_source_tool_registry_current_total() -> None:
    registry = compat.extract_source_tool_registry()
    names = compat.flatten_registry(registry)

    assert len(names) == 75
    assert "create_image" in names
    assert "apply_drop_shadow" in names
    assert "sample_color" in names


def test_results_template_is_non_claiming() -> None:
    contract = compat.load_contract()
    template = compat.build_results_template(contract)

    assert template["schema"] == "gimp-mcp.compat.results.v1"
    assert template["summary"]["status"] == "unverified"
    assert template["summary"]["claim_allowed"] is False
    assert len(template["checks"]) == len(contract["static_checks"]) + len(
        contract["live_smoke_scenarios"]
    )


def test_claim_gate_fails_until_live_results_exist(tmp_path: Path) -> None:
    contract = compat.load_contract()

    failures = compat.audit_claim_gate(contract)

    assert failures
    assert any("compat.results.yml" in failure for failure in failures)
