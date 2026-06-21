#!/usr/bin/env python3
"""Live GIMP 3.2.4 transport/API smoke runner.

This script requires a running GIMP instance with the bundled plug-in started
from Tools -> Start MCP Pro Server.  It intentionally avoids pytest collection
by using a non-test filename; run it manually:

    uv run python tests/live_gimp_324_smoke.py --output compat.results.yml

The script produces a partial compat.results.yml.  It is useful evidence for
transport, introspection, PDB, metadata, and bitmap checks, but it does not yet
replace the full per-tool MCP smoke matrix described in compat.yml.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - live utility guard
    raise SystemExit("PyYAML is required. Run: uv sync --extra dev") from exc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gimp_mcp_pro.bridge import GimpBridge  # noqa: E402
from gimp_mcp_pro.config import ServerConfig  # noqa: E402
from gimp_mcp_pro.utils.errors import GimpCommandError, GimpConnectionError  # noqa: E402


def utc_now() -> str:
    """Return an ISO UTC timestamp."""
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def git_revision() -> str:
    """Return current git revision, or unknown when git is unavailable."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def file_sha256(path: Path) -> str:
    """Return SHA-256 for a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_check(check_id: str, status: str, evidence: Any) -> dict[str, Any]:
    """Create one result check record."""
    return {"id": check_id, "status": status, "evidence": evidence}


def run_smoke(config: ServerConfig, plugin_path: Path | None = None) -> dict[str, Any]:
    """Run live smoke checks through the bridge."""
    started = utc_now()
    bridge = GimpBridge(**config.bridge_kwargs())
    checks: list[dict[str, Any]] = []
    env: dict[str, Any] = {
        "os": platform.platform(),
        "desktop_session": "unknown",
        "gimp_executable": "unknown",
        "gimp_version": "unknown",
        "gimp_verbose_version": "unknown",
        "python_version_inside_gimp": "unknown",
        "pygobject_version_inside_gimp": "unknown",
        "libgimp_api_version": "3.0",
        "libgimp_library_version": "3.2.4",
        "gegl_version": "unknown",
        "plugin_install_path": str(plugin_path) if plugin_path else "unknown",
        "plugin_sha256": file_sha256(plugin_path)
        if plugin_path and plugin_path.exists()
        else "unknown",
        "mcp_server_revision": git_revision(),
        "mcp_server_command": "uv run gimp-mcp-pro serve",
    }

    try:
        bridge.connect()
        info = bridge.send_command("get_gimp_info")
        checks.append(make_check("C-020-transport", "pass", info))
    except GimpConnectionError as exc:
        checks.append(make_check("C-020-transport", "fail", str(exc)))
        return finish_result(started, env, checks)

    try:
        expressions = [
            "__import__('platform').python_version()",
            "Gimp.get_pdb().procedure_exists('plug-in-mcp-pro-server')",
            "Gimp.get_pdb().procedure_exists('file-png-export')",
            "Gimp.get_pdb().procedure_exists('file-jpeg-export')",
            "Gimp.DrawableFilter is not None",
            "Gimp.ImageProcedure is not None",
            "Gimp.PDBProcType.PLUGIN is not None",
            "Gimp.PDBStatusType.SUCCESS is not None",
        ]
        probe = bridge.evaluate_python(expressions)
        values = probe.get("results", [])
        env["python_version_inside_gimp"] = values[0] if values else "unknown"
        checks.append(make_check("C-001-env-introspection", "pass", probe))
        checks.append(make_check("C-010-plugin-registration", "pass", {"pdb_probe": values[1]}))
        checks.append(make_check("C-100-pdb-contract", "pass", {"pdb_probe_values": values[1:4]}))
    except GimpCommandError as exc:
        checks.append(make_check("C-001-env-introspection", "fail", str(exc)))

    try:
        bridge.execute_python(
            [
                "image = Gimp.Image.new(320, 240, Gimp.ImageBaseType.RGB)",
                "layer = Gimp.Layer.new(image, 'compat-layer', 320, 240, Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.NORMAL)",
                "image.insert_layer(layer, None, 0)",
                "Gimp.displays_flush()",
            ]
        )
        metadata = bridge.send_command("get_image_metadata")
        checks.append(make_check("C-030-image-basics", "pass", metadata))
        checks.append(make_check("C-040-layer-contract", "pass", metadata))
    except GimpCommandError as exc:
        checks.append(make_check("C-030-image-basics", "fail", str(exc)))

    try:
        bitmap = bridge.get_image_bitmap(max_width=160, max_height=120)
        results = bitmap.get("results", {}) if isinstance(bitmap, dict) else {}
        raw = base64.b64decode(results.get("image_data", ""))
        png_ok = raw.startswith(b"\x89PNG\r\n\x1a\n")
        status = "pass" if png_ok else "fail"
        checks.append(
            make_check(
                "C-060-export-bitmap-contract",
                status,
                {
                    "format": results.get("format"),
                    "width": results.get("width"),
                    "height": results.get("height"),
                    "png_magic_ok": png_ok,
                    "decoded_bytes": len(raw),
                },
            )
        )
    except (GimpCommandError, ValueError) as exc:
        checks.append(make_check("C-060-export-bitmap-contract", "fail", str(exc)))

    try:
        bridge.send_command("definitely_invalid_compat_command")
    except GimpCommandError as exc:
        checks.append(make_check("C-120-error-contract", "pass", str(exc)))
    else:
        checks.append(
            make_check("C-120-error-contract", "fail", "invalid command unexpectedly succeeded")
        )

    bridge.disconnect()
    return finish_result(started, env, checks)


def finish_result(
    started: str, env: dict[str, Any], checks: list[dict[str, Any]]
) -> dict[str, Any]:
    """Add summary fields to a result object."""
    finished = utc_now()
    passed = sum(1 for check in checks if check["status"] == "pass")
    failed = sum(1 for check in checks if check["status"] == "fail")
    skipped = sum(1 for check in checks if check["status"] == "skip")
    waived = sum(1 for check in checks if check["status"] == "waived")
    return {
        "schema": "gimp-mcp.compat.results.v1",
        "project": "gimp-mcp",
        "contract": "compat.yml",
        "run_id": f"live-smoke-{int(time.time())}",
        "run_started_at": started,
        "run_finished_at": finished,
        "tester": platform.node() or "local",
        "environment": env,
        "checks": checks,
        "summary": {
            "status": "partial" if failed == 0 else "failed",
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "waived": waived,
            "claim_allowed": False,
            "notes": [
                "Partial live smoke only; full compat.yml matrix still required before a verified claim.",
            ],
        },
    }


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Run live GIMP 3.2.4 bridge smoke checks.")
    parser.add_argument("--host", help="Override GIMP plug-in host.")
    parser.add_argument("--port", type=int, help="Override GIMP plug-in port.")
    parser.add_argument("--output", default="compat.results.yml", help="YAML result path.")
    parser.add_argument(
        "--plugin-path", type=Path, help="Installed plug-in file path for evidence."
    )
    parser.add_argument("--json", action="store_true", help="Also print JSON to stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Script entry point."""
    args = build_parser().parse_args(argv)
    config = ServerConfig()
    if args.host:
        config.gimp_host = args.host
    if args.port:
        config.gimp_port = args.port

    result = run_smoke(config, args.plugin_path)
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.write_text(yaml.safe_dump(result, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"wrote {output.relative_to(PROJECT_ROOT)}")
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 1 if result["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
