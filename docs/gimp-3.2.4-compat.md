# GIMP 3.2.4 Compatibility Verification Runbook

This document is the human-facing runbook for `compat.yml`. The YAML contract is normative; this file explains how to operate it.

## Status

```yaml
status: partial-live-smoke-pass
claim_allowed: false
contract: compat.yml
latest_results: compat.results.yml
run_id: live-smoke-1782081764
run_started_at: '2026-06-21T22:42:41+00:00'
run_finished_at: '2026-06-21T22:42:44+00:00'
checks_passed: 18
checks_failed: 0
registered_tools: 86
clean_profile: true
xvfb: true
revision: 951ec6afd5c5766c610c795342a6889fcf7ab9ef
```

A fresh clean-profile GIMP 3.2.4 run under Xvfb passed the smoke record with zero failed checks and confirmed the 86-tool runtime registry. This is useful release evidence, but it is still intentionally non-claiming because the result summary says `claim_allowed: false`. Do not publish a verified GIMP 3.2.4 support claim until the full matrix records `claim_allowed: true` or explicit waivers with linked follow-up issues.

## Static contract checks

```bash
uv run python scripts/compat.py validate
uv run python scripts/compat.py list-tools --grouped
uv run python scripts/compat.py audit
uv run python scripts/compat.py validate-results compat.results.yml
```

Expected right now:

```yaml
compat_validate: pass
validate_results: pass
compat_audit: expected_to_fail_until:
  - compat.results.yml contains a full-matrix result with summary.claim_allowed: true
current_live_record:
  status: partial-live-smoke-pass
  checks_passed: 18
  checks_failed: 0
  registered_tools: 86
```

## Result template

```bash
uv run python scripts/compat.py init-results --output compat.results.template.yml --force
cp compat.results.template.yml compat.results.yml
```

Only fill `compat.results.yml` with real values after a run. The template is intentionally non-claiming.

## Latest clean-profile evidence

```yaml
run_id: live-smoke-1782081764
run_started_at: '2026-06-21T22:42:41+00:00'
run_finished_at: '2026-06-21T22:42:44+00:00'
revision: 951ec6afd5c5766c610c795342a6889fcf7ab9ef
gimp_version: 3.2.4
libgimp_api_version: '3.0'
libgimp_library_version: 3.2.4
spawned_gimp: true
xvfb: true
mcp_port: 55491
checks_passed: 18
checks_failed: 0
registered_tools: 86
claim_allowed: false
```

The current record verifies transport, async transport, plug-in registration, runtime introspection, the 86-tool registry, representative image/layer/selection/drawing/export/transform/color/filter/history/PDB/error scenarios, and documentation-count consistency. It does **not** by itself flip the public compatibility claim because the live runner still marks this as a partial smoke rather than a full `compat.yml` matrix.


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
uv run python tests/live_gimp_324_smoke.py --spawn --xvfb --include-static-checks --output compat.results.yml
```

Optionally record the installed plug-in hash:

```bash
uv run python tests/live_gimp_324_smoke.py \
  --plugin-path "$HOME/.config/GIMP/3.0/plug-ins/gimp_mcp_plugin/gimp_mcp_plugin.py" \
  --output compat.results.yml
```

## What the current compatibility matrix covers

```yaml
covered:
  - clean-profile GIMP 3.2.4 spawn under Xvfb
  - persistent plug-in procedure activation
  - synchronous bridge transport connection
  - asyncio-native AsyncGimpBridge transport connection
  - length-prefixed request/response path
  - GIMP/PDB introspection probes
  - plug-in procedure presence probe
  - 86 registered MCP tools
  - representative image/layer/selection/drawing/export/transform/color/filter/history/PDB/error scenarios
  - bitmap PNG extraction
  - static unit/lint/type/docs claim gate
remaining_manual_depth:
  - exhaustive pixel-delta assertions for every filter/color/transform variant
  - secondary OS/package verification beyond the local Linux clean-profile run
```

## Tool count reconciliation

The source-derived registry currently contains 86 `@mcp.tool` entries. README must keep its advertised tool total aligned with the runtime registry before this branch publishes the compatibility story.

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
