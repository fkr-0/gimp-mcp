#!/usr/bin/env python3
"""Compatibility contract helpers for GIMP 3.2.4 verification.

The contract lives in compat.yml.  This helper intentionally separates three
levels of work:

* list-tools: derive the runtime MCP tool registry from source decorators.
* validate: check that compat.yml is internally consistent with the source tree.
* audit: check claim-gate conditions that are expected to fail until a live
  GIMP 3.2.4 verification run has produced compat.results.yml.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised only in broken dev envs
    raise SystemExit(
        "PyYAML is required for compatibility contract tooling. Run: uv sync --extra dev"
    ) from exc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPAT_PATH = PROJECT_ROOT / "compat.yml"
README_PATH = PROJECT_ROOT / "README.md"
TOOLS_DIR = PROJECT_ROOT / "src" / "gimp_mcp_pro" / "tools"
RESULTS_TEMPLATE_PATH = PROJECT_ROOT / "compat.results.template.yml"
LOGICAL_TOOL_MODULES = {
    "inspect_context_backend": "inspect_tools",
    "inspect_geometry_backend": "inspect_tools",
    "inspect_snapshot_backend": "inspect_tools",
    "inspect_bitmap_backend": "inspect_tools",
}

ToolRegistry = dict[str, list[str]]
CheckStatus = Literal["pass", "fail", "skip", "waived"]
SummaryStatus = Literal["unverified", "partial", "failed", "verified"]


class CheckResult(TypedDict, total=False):
    """One static/live compatibility check result."""

    id: str
    kind: str
    status: CheckStatus
    evidence: Any
    waiver: dict[str, str]


class EnvironmentResult(TypedDict, total=False):
    """Environment evidence captured for a compatibility run."""

    os: str
    desktop_session: str
    gimp_executable: str
    gimp_version: str
    gimp_verbose_version: str
    python_version_inside_gimp: str
    pygobject_version_inside_gimp: str
    libgimp_api_version: str
    libgimp_library_version: str
    gegl_version: str
    plugin_install_path: str
    plugin_sha256: str
    mcp_server_revision: str
    mcp_server_command: str


class SummaryResult(TypedDict, total=False):
    """Summary counters and claim state for a compatibility run."""

    status: SummaryStatus
    passed: int
    failed: int
    skipped: int
    waived: int
    claim_allowed: bool
    notes: list[str]


class CompatibilityResult(TypedDict, total=False):
    """compat.results.yml payload shape."""

    schema: str
    project: str
    contract: str
    run_id: str
    run_started_at: str
    run_finished_at: str | None
    tester: str
    environment: EnvironmentResult
    checks: list[CheckResult]
    summary: SummaryResult


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from disk."""
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level")
    return data


def load_contract(path: Path = COMPAT_PATH) -> dict[str, Any]:
    """Load compat.yml."""
    return load_yaml(path)


def flatten_registry(registry: Mapping[str, Iterable[str]]) -> list[str]:
    """Flatten a category -> names mapping while preserving category order."""
    names: list[str] = []
    for values in registry.values():
        names.extend(values)
    return names


def expected_tool_registry(contract: Mapping[str, Any]) -> ToolRegistry:
    """Return the tool registry declared in compat.yml."""
    tool_contract = contract.get("mcp_tool_contract", {})
    registry = tool_contract.get("registry", {})
    if not isinstance(registry, dict):
        raise ValueError("mcp_tool_contract.registry must be a mapping")
    return {str(category): list(names) for category, names in registry.items()}


def extract_source_tool_registry(tools_dir: Path = TOOLS_DIR) -> ToolRegistry:
    """Extract @mcp.tool-decorated functions from src/gimp_mcp_pro/tools."""
    registry: ToolRegistry = {}
    for path in sorted(tools_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        names: list[str] = []
        for index, line in enumerate(lines):
            if "@mcp.tool" not in line:
                continue
            for candidate in lines[index + 1 : index + 16]:
                match = re.search(
                    r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", candidate
                )
                if match:
                    names.append(match.group(1))
                    break
        if names:
            module = LOGICAL_TOOL_MODULES.get(path.stem, path.stem)
            registry.setdefault(module, []).extend(names)
    return registry


def readme_advertised_tool_counts(readme_path: Path = README_PATH) -> list[int]:
    """Return public tool-count claims found in README.md."""
    if not readme_path.exists():
        return []
    text = readme_path.read_text(encoding="utf-8")
    patterns = [
        r"\b(\d+)\s+typed\s+MCP\s+tools\b",
        r"\b(\d+)\s+typed\s+tools\b",
        r"\b(\d+)\s+tools\b",
    ]
    counts: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            counts.append(int(match.group(1)))
    return counts


def _unique_failures(values: Sequence[str], label: str) -> list[str]:
    seen: set[str] = set()
    failures: list[str] = []
    for value in values:
        if value in seen:
            failures.append(f"duplicate {label}: {value}")
        seen.add(value)
    return failures


def validate_contract(contract: Mapping[str, Any]) -> list[str]:
    """Validate compat.yml against source-derived facts."""
    failures: list[str] = []

    if contract.get("schema") != "gimp-mcp.compat.v1":
        failures.append("schema must be gimp-mcp.compat.v1")
    if contract.get("project") != "gimp-mcp":
        failures.append("project must be gimp-mcp")
    if contract.get("source_issue") != "GIMP-MCP-001":
        failures.append("source_issue must be GIMP-MCP-001")

    expected_registry = expected_tool_registry(contract)
    expected_names = flatten_registry(expected_registry)
    expected_total = contract.get("mcp_tool_contract", {}).get("expected_registry_total")
    if expected_total != len(expected_names):
        failures.append(
            f"mcp_tool_contract.expected_registry_total={expected_total!r} "
            f"but registry lists {len(expected_names)} tools"
        )
    failures.extend(_unique_failures(expected_names, "tool name in compat registry"))

    source_registry = extract_source_tool_registry()
    source_names = flatten_registry(source_registry)
    if set(expected_names) != set(source_names):
        missing = sorted(set(source_names) - set(expected_names))
        stale = sorted(set(expected_names) - set(source_names))
        if missing:
            failures.append(f"compat registry missing source tools: {', '.join(missing)}")
        if stale:
            failures.append(f"compat registry contains stale tools: {', '.join(stale)}")
    if expected_total != len(source_names):
        failures.append(
            f"expected_registry_total={expected_total!r} but source has {len(source_names)} @mcp.tool entries"
        )

    live_ids = [str(item.get("id")) for item in contract.get("live_smoke_scenarios", [])]
    static_ids = [str(item.get("id")) for item in contract.get("static_checks", [])]
    failures.extend(_unique_failures(live_ids, "live smoke scenario id"))
    failures.extend(_unique_failures(static_ids, "static check id"))

    acceptance_items = contract.get("acceptance", {}).get("required_to_close_source_issue", [])
    if not acceptance_items:
        failures.append("acceptance.required_to_close_source_issue must not be empty")

    return failures


def audit_claim_gate(contract: Mapping[str, Any]) -> list[str]:
    """Check conditions that must pass before claiming verified compatibility."""
    failures = validate_contract(contract)
    expected_total = contract.get("mcp_tool_contract", {}).get("expected_registry_total")

    readme_counts = readme_advertised_tool_counts()
    if expected_total not in readme_counts:
        failures.append(
            f"README does not advertise the source-derived tool total {expected_total}; "
            f"found counts={readme_counts or 'none'}"
        )

    if README_PATH.exists() and "GIMP 3.0.8 compatible" in README_PATH.read_text(encoding="utf-8"):
        failures.append("README still contains stale claim: 'GIMP 3.0.8 compatible'")

    results_path = PROJECT_ROOT / str(
        contract.get("contract", {}).get("result_file", "compat.results.yml")
    )
    if not results_path.exists():
        failures.append(f"missing live verification result file: {results_path.name}")
        return failures

    result = load_yaml(results_path)
    for failure in validate_results_payload(contract, result, require_all_checks=True):
        failures.append(f"{results_path.name}: {failure}")

    summary = result.get("summary")
    if not isinstance(summary, Mapping):
        failures.append(f"{results_path.name}: summary must be a mapping")
        return failures

    if summary.get("status") != "verified" or summary.get("claim_allowed") is not True:
        failures.append(
            f"{results_path.name}: result is not a verified, claim-allowed compatibility run"
        )

    failed_ids = [
        str(check.get("id", "unknown"))
        for check in result.get("checks", [])
        if isinstance(check, Mapping) and check.get("status") == "fail"
    ]
    if failed_ids:
        failures.append(f"{results_path.name}: failed checks present: {', '.join(failed_ids)}")

    return failures


def known_check_ids(contract: Mapping[str, Any]) -> set[str]:
    """Return all check IDs declared by compat.yml."""
    ids: set[str] = set()
    for section in ("static_checks", "live_smoke_scenarios"):
        for item in contract.get(section, []):
            if isinstance(item, Mapping) and "id" in item:
                ids.add(str(item["id"]))
    return ids


def _required_values(contract: Mapping[str, Any], path: Sequence[str]) -> list[str]:
    """Read a list of required field names from compat.yml."""
    current: Any = contract
    for key in path:
        if not isinstance(current, Mapping):
            return []
        current = current.get(key, {})
    return [str(value) for value in current] if isinstance(current, list) else []


def validate_results_payload(
    contract: Mapping[str, Any], result: Mapping[str, Any], *, require_all_checks: bool = False
) -> list[str]:
    """Validate compat.results.yml structure against compat.yml.

    This validates evidence shape only.  It does not allow a verified public
    compatibility claim; that remains the job of the audit/claim gate.
    """
    failures: list[str] = []

    required_top = _required_values(
        contract, ("result_schema", "compat.results.yml", "required_top_level_fields")
    )
    required_env = _required_values(
        contract, ("result_schema", "compat.results.yml", "environment_required_fields")
    )
    required_check = _required_values(
        contract, ("result_schema", "compat.results.yml", "check_required_fields")
    )
    allowed_statuses = set(
        _required_values(contract, ("result_schema", "compat.results.yml", "status_values"))
    )
    known_ids = known_check_ids(contract)

    for field in required_top:
        if field not in result:
            failures.append(f"results missing top-level field: {field}")

    if result.get("schema") != "gimp-mcp.compat.results.v1":
        failures.append("results schema must be gimp-mcp.compat.results.v1")
    if result.get("project") != contract.get("project"):
        failures.append("results project must match compat.yml project")
    if result.get("contract") != "compat.yml":
        failures.append("results contract must be compat.yml")

    environment = result.get("environment")
    if not isinstance(environment, Mapping):
        failures.append("results environment must be a mapping")
    else:
        for field in required_env:
            if field not in environment:
                failures.append(f"results environment missing field: {field}")

    checks = result.get("checks")
    seen_ids: set[str] = set()
    if not isinstance(checks, list):
        failures.append("results checks must be a list")
    else:
        for index, check in enumerate(checks):
            if not isinstance(check, Mapping):
                failures.append(f"results check at index {index} must be a mapping")
                continue
            for field in required_check:
                if field not in check:
                    failures.append(f"results check {index} missing field: {field}")
            check_id = str(check.get("id", ""))
            if check_id:
                if check_id in seen_ids:
                    failures.append(f"duplicate results check id: {check_id}")
                seen_ids.add(check_id)
                if check_id not in known_ids:
                    failures.append(f"results check id is not declared in compat.yml: {check_id}")
            status = check.get("status")
            if status not in allowed_statuses:
                failures.append(f"results check {check_id or index} has invalid status: {status!r}")
            if status == "waived":
                waiver = check.get("waiver")
                if not isinstance(waiver, Mapping):
                    failures.append(
                        f"waived results check {check_id or index} must include waiver mapping"
                    )
                else:
                    for field in (
                        contract.get("result_schema", {})
                        .get("compat.results.yml", {})
                        .get("waiver_required_fields", [])
                    ):
                        if field not in waiver:
                            failures.append(
                                f"waived results check {check_id or index} missing waiver field: {field}"
                            )

    if require_all_checks:
        missing_ids = sorted(known_ids - seen_ids)
        if missing_ids:
            failures.append(f"results missing declared checks: {', '.join(missing_ids)}")

    summary = result.get("summary")
    if not isinstance(summary, Mapping):
        failures.append("results summary must be a mapping")
    else:
        claim_allowed = summary.get("claim_allowed")
        if not isinstance(claim_allowed, bool):
            failures.append("results summary.claim_allowed must be boolean")
        if summary.get("status") == "verified" and claim_allowed is not True:
            failures.append("verified results must set summary.claim_allowed=true")

    return failures


def validate_results_file(
    path: Path, contract: Mapping[str, Any], *, require_all_checks: bool = False
) -> list[str]:
    """Load and validate a compat results YAML file."""
    return validate_results_payload(
        contract, load_yaml(path), require_all_checks=require_all_checks
    )


def build_results_template(contract: Mapping[str, Any]) -> CompatibilityResult:
    """Build a non-claiming compat.results.yml template."""
    now = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()
    checks = []
    for check in contract.get("static_checks", []):
        checks.append(
            {
                "id": check["id"],
                "kind": "static",
                "status": "skip",
                "evidence": "not run yet",
            }
        )
    for scenario in contract.get("live_smoke_scenarios", []):
        checks.append(
            {
                "id": scenario["id"],
                "kind": "live_smoke",
                "status": "skip",
                "evidence": "not run yet",
            }
        )

    return {
        "schema": "gimp-mcp.compat.results.v1",
        "project": contract.get("project", "gimp-mcp"),
        "contract": "compat.yml",
        "run_id": "TEMPLATE-replace-with-utc-timestamp-or-ci-run-id",
        "run_started_at": now,
        "run_finished_at": None,
        "tester": "replace-me",
        "environment": {
            "os": "replace-me",
            "desktop_session": "replace-me",
            "gimp_executable": "replace-me",
            "gimp_version": "replace-me",
            "gimp_verbose_version": "replace-me",
            "python_version_inside_gimp": "replace-me",
            "pygobject_version_inside_gimp": "replace-me",
            "libgimp_api_version": "3.0",
            "libgimp_library_version": "3.2.4",
            "gegl_version": "replace-me",
            "plugin_install_path": "replace-me",
            "plugin_sha256": "replace-me",
            "mcp_server_revision": "replace-me",
            "mcp_server_command": "uv run gimp-mcp-pro serve",
        },
        "checks": checks,
        "summary": {
            "status": "unverified",
            "passed": 0,
            "failed": 0,
            "skipped": len(checks),
            "waived": 0,
            "claim_allowed": False,
            "notes": [
                "This is a template, not evidence of live GIMP 3.2.4 compatibility.",
                "Replace status values only after running the corresponding checks.",
            ],
        },
    }


def write_yaml(path: Path, payload: Mapping[str, Any], *, force: bool = False) -> None:
    """Write YAML without accidentally overwriting existing result evidence."""
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to overwrite")
    path.write_text(
        yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def cmd_list_tools(args: argparse.Namespace) -> int:
    """Print source-derived MCP tool registry."""
    registry = extract_source_tool_registry()
    payload: Any = registry if args.grouped else flatten_registry(registry)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.yaml:
        print(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    elif args.grouped:
        for module, names in registry.items():
            print(f"{module}: {len(names)}")
            for name in names:
                print(f"  - {name}")
    else:
        for name in payload:
            print(name)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate compat.yml internal/source consistency."""
    failures = validate_contract(load_contract(args.contract))
    if failures:
        print("compat validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("compat validation ok")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Audit compatibility claim gate."""
    failures = audit_claim_gate(load_contract(args.contract))
    if failures:
        print("compat claim gate is not satisfied:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("compat claim gate ok")
    return 0


def cmd_validate_results(args: argparse.Namespace) -> int:
    """Validate a compat.results.yml file."""
    output = Path(args.results)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    failures = validate_results_file(
        output, load_contract(args.contract), require_all_checks=args.require_all_checks
    )
    if failures:
        print(f"{output.name} validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"{output.name} validation ok")
    return 0


def cmd_init_results(args: argparse.Namespace) -> int:
    """Create a compat results template."""
    contract = load_contract(args.contract)
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    write_yaml(output, build_results_template(contract), force=args.force)
    print(f"wrote {output.relative_to(PROJECT_ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="GIMP 3.2.4 compatibility contract tooling.")
    parser.add_argument("--contract", type=Path, default=COMPAT_PATH, help="Path to compat.yml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_tools = subparsers.add_parser("list-tools", help="List @mcp.tool-decorated functions.")
    list_tools.add_argument("--grouped", action="store_true", help="Group tools by source module.")
    list_tools.add_argument("--json", action="store_true", help="Emit JSON.")
    list_tools.add_argument("--yaml", action="store_true", help="Emit YAML.")
    list_tools.set_defaults(func=cmd_list_tools)

    validate = subparsers.add_parser("validate", help="Validate compat.yml against source facts.")
    validate.set_defaults(func=cmd_validate)

    audit = subparsers.add_parser(
        "audit", help="Check whether the README compatibility claim gate is satisfied."
    )
    audit.set_defaults(func=cmd_audit)

    validate_results = subparsers.add_parser(
        "validate-results", help="Validate a compat.results.yml evidence file."
    )
    validate_results.add_argument("results", nargs="?", default="compat.results.yml")
    validate_results.add_argument(
        "--require-all-checks",
        action="store_true",
        help="Require every static/live check declared in compat.yml to be present.",
    )
    validate_results.set_defaults(func=cmd_validate_results)

    init_results = subparsers.add_parser(
        "init-results", help="Create a compat.results.yml template."
    )
    init_results.add_argument(
        "--output", default=str(RESULTS_TEMPLATE_PATH.relative_to(PROJECT_ROOT))
    )
    init_results.add_argument("--force", action="store_true", help="Overwrite existing output.")
    init_results.set_defaults(func=cmd_init_results)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Script entry point."""
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
