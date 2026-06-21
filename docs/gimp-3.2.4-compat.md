# GIMP 3.2.4 Compatibility Verification Runbook

This document is the human-facing runbook for `compat.yml`. The YAML contract is normative; this file explains how to operate it.

## Status

```yaml
status: unverified
claim_allowed: false
contract: compat.yml
results_file_required_before_claim: compat.results.yml
```

Do not publish a verified GIMP 3.2.4 support claim until `compat.results.yml` records a passing clean-profile run or explicit waivers with linked follow-up issues.

## Static contract checks

```bash
uv run python scripts/compat.py validate
uv run python scripts/compat.py list-tools --grouped
uv run python scripts/compat.py audit
uv run python scripts/compat.py validate-results compat.results.yml
```

Expected right now:

```yaml
compat_validate: should_pass
compat_audit: expected_to_fail_until:
  - README tool count is reconciled with the source-derived registry
  - stale GIMP 3.0.8 wording is removed or moved into a historical note
  - compat.results.yml exists with live GIMP 3.2.4 evidence
```

## Result template

```bash
uv run python scripts/compat.py init-results --output compat.results.template.yml --force
cp compat.results.template.yml compat.results.yml
```

Only fill `compat.results.yml` with real values after a run. The template is intentionally non-claiming.


## Optional capability result shape

GIMP 3.2.4 installations can differ in optional PDB and Script-Fu procedures.
This does not invalidate transport compatibility when the bridge and core API are
working. Optional tools must return a structured failure instead of relying only
on human wording:

```yaml
success: false
operation: apply_drop_shadow
error: Drop shadow procedure not found
data:
  error_code: optional_capability_unavailable
  optional_capability: true
  capability: Script-Fu drop shadow
  procedure: script-fu-drop-shadow
  recommendation: Compose the shadow with typed layer and blur tools.
```

The live smoke runner accepts this machine-readable shape for known optional
capabilities such as `script-fu-drop-shadow`, `gimp-image-undo`, and
`gimp-image-redo`. Unexpected tool failures still fail the check.

## Result schema validation

`validate-results` checks whether an evidence file is structurally usable. It does not grant the public compatibility claim by itself.

```bash
uv run python scripts/compat.py validate-results compat.results.yml
uv run python scripts/compat.py validate-results compat.results.yml --require-all-checks
```

```yaml
validate_results:
  purpose: verify schema, required environment fields, check IDs, statuses, and waiver shape
  accepts_partial_live_smoke: true
  claim_gate: false
require_all_checks:
  purpose: ensure every static and live check declared in compat.yml has a result entry
  useful_for: final verification pass or CI-style completeness checks
status_values:
  - pass
  - fail
  - skip
  - waived
waived_checks_require:
  - reason
  - linked_issue
  - user_visible_caveat
```

Keep partial live-smoke files as `summary.status: partial` and `summary.claim_allowed: false`. A structurally valid partial result is useful debugging evidence, not a release claim.

## Clean-profile live run

1. Create or choose a clean GIMP profile.
2. Install the plug-in using one canonical layout from `compat.yml`.
3. Start GIMP 3.2.4.
4. Open `Tools -> Start MCP Pro Server`.
5. In this repository, run:

```bash
uv run python tests/live_gimp_324_smoke.py --output compat.results.yml
```

Optionally record the installed plug-in hash:

```bash
uv run python tests/live_gimp_324_smoke.py \
  --plugin-path "$HOME/.config/GIMP/3.0/plug-ins/gimp_mcp_plugin/gimp_mcp_plugin.py" \
  --output compat.results.yml
```

## What the current live smoke covers

```yaml
covered:
  - bridge transport connection
  - length-prefixed request/response path
  - GIMP/PDB introspection probes
  - plug-in procedure presence probe
  - image creation via PyGObject
  - layer creation via PyGObject
  - metadata retrieval
  - bitmap PNG extraction
  - structured error behavior for invalid commands
not_yet_complete:
  - full per-MCP-tool invocation matrix
  - all filter/color/transform pixel-delta assertions
  - README claim update
```

## Tool count reconciliation

The source-derived registry currently contains 75 `@mcp.tool` entries. README must not continue to advertise 67 tools once this branch publishes the new compatibility story.

```bash
uv run python scripts/compat.py list-tools --grouped
```

## Acceptance gate

```yaml
accept_when:
  - compat.yml validates
  - compat.results.yml records live GIMP 3.2.4 evidence
  - required smoke scenarios pass or have linked waivers
  - README compatibility table reflects actual status
  - setup instructions use a plug-in install layout proven by the live run
reject_when:
  - support is claimed from pytest alone
  - support is claimed from import success alone
  - dirty local GIMP profile is the only evidence
  - stale GIMP 3.0.8 current-release wording remains
```
