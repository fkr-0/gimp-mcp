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

    assert len(names) == 86
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


def test_claim_gate_audit_returns_failure_list_for_current_evidence(tmp_path: Path) -> None:
    contract = compat.load_contract()

    failures = compat.audit_claim_gate(contract)

    assert isinstance(failures, list)


def test_results_template_validates_against_contract() -> None:
    contract = compat.load_contract()
    template = compat.build_results_template(contract)

    failures = compat.validate_results_payload(contract, template, require_all_checks=True)

    assert failures == []


def test_partial_live_smoke_result_validates_but_does_not_complete_matrix() -> None:
    contract = compat.load_contract()
    result = compat.build_results_template(contract)
    result["run_id"] = "partial-test"
    result["checks"] = [
        {
            "id": "C-020-transport",
            "kind": "live_smoke",
            "status": "pass",
            "evidence": {"socket": "ok"},
        }
    ]
    result["summary"] = {
        "status": "partial",
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "waived": 0,
        "claim_allowed": False,
        "notes": ["partial schema test"],
    }

    partial_failures = compat.validate_results_payload(contract, result)
    complete_failures = compat.validate_results_payload(contract, result, require_all_checks=True)

    assert partial_failures == []
    assert any("results missing declared checks" in failure for failure in complete_failures)


def test_results_validator_rejects_unknown_ids_statuses_and_bad_waivers() -> None:
    contract = compat.load_contract()
    result = compat.build_results_template(contract)
    result["checks"] = [
        {"id": "C-DOES-NOT-EXIST", "status": "pass", "evidence": {}},
        {"id": "C-020-transport", "status": "maybe", "evidence": {}},
        {"id": "C-001-env-introspection", "status": "waived", "evidence": {}},
    ]

    failures = compat.validate_results_payload(contract, result)

    assert any("not declared" in failure for failure in failures)
    assert any("invalid status" in failure for failure in failures)
    assert any("must include waiver mapping" in failure for failure in failures)


def test_results_file_command_accepts_template(tmp_path: Path) -> None:
    contract = compat.load_contract()
    output = tmp_path / "compat.results.yml"
    compat.write_yaml(output, compat.build_results_template(contract), force=True)

    status = compat.main(["validate-results", str(output), "--require-all-checks"])

    assert status == 0
