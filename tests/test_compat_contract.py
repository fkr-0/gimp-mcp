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

    assert len(names) == 137
    assert "create_image" in names
    assert "apply_drop_shadow" in names
    assert "sample_color" in names


def _live_scenario(contract: dict[str, object], check_id: str) -> dict[str, object]:
    scenarios = contract.get("live_smoke_scenarios", [])
    assert isinstance(scenarios, list)
    for scenario in scenarios:
        assert isinstance(scenario, dict)
        if scenario.get("id") == check_id:
            return scenario
    raise AssertionError(f"missing live smoke scenario {check_id}")


def test_mask_path_selection_contracts_declare_e2e_tool_sets() -> None:
    contract = compat.load_contract()

    layer_contract = _live_scenario(contract, "C-040-layer-contract")
    selection_contract = _live_scenario(contract, "C-050-selection-drawing-contract")
    path_contract = _live_scenario(contract, "C-055-path-contract")

    assert set(layer_contract["tools"]) >= {
        "add_layer_mask",
        "get_layer_mask_info",
        "set_layer_mask_state",
        "remove_layer_mask",
    }
    assert set(selection_contract["tools"]) >= {
        "select_by_color",
        "feather_selection",
        "border_selection",
        "stroke_selection",
        "bucket_fill",
        "get_selection_info",
    }
    assert set(path_contract["tools"]) >= {
        "create_path",
        "list_paths",
        "path_to_selection",
        "stroke_path",
        "remove_path",
    }

    joined_assertions = "\n".join(
        str(assertion)
        for scenario in (layer_contract, selection_contract, path_contract)
        for assertion in scenario.get("assertions", [])
    )
    assert "mask" in joined_assertions
    assert "selection" in joined_assertions
    assert "path" in joined_assertions


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
