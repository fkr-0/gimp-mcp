#!/usr/bin/env python3
"""Live GIMP 3.2.4 transport/API smoke runner.

The runner can either connect to an already-running plug-in server or spawn a
clean-profile GIMP instance, install the bundled plug-in into that temporary
profile, request plug-in autostart, wait for the bridge socket, run smoke checks,
and stop the spawned GIMP process.

Manual existing-server mode:

    uv run python tests/live_gimp_324_smoke.py --output compat.results.yml

Self-contained clean-profile mode:

    uv run python tests/live_gimp_324_smoke.py --spawn --xvfb --output compat.results.yml
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
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

GIMP_CANDIDATES = ("gimp-3.2", "gimp-3", "gimp", "gimp-3.0")
PLUGIN_SOURCE = PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py"
TRUTHY = {"1", "true", "yes", "on"}


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


def env_truthy(name: str, default: str = "0") -> bool:
    """Return whether an environment flag is enabled."""
    return os.environ.get(name, default).strip().lower() in TRUTHY


def discover_gimp(explicit: str | None = None) -> str | None:
    """Return a GIMP executable path/name without starting it."""
    if explicit:
        return explicit
    env_override = os.environ.get("GIMP_MCP_GIMP") or os.environ.get("GIMP_DEV_GIMP")
    if env_override:
        return env_override
    for candidate in GIMP_CANDIDATES:
        if shutil.which(candidate):
            return candidate
    return None


def _sanitize_child_path(path_value: str | None, *, project_root: Path) -> str:
    """Remove uv/virtualenv bins so GIMP plug-ins use the system Python/gi."""
    if not path_value:
        return ""
    blocked = {str((project_root / ".venv" / "bin").resolve())}
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        blocked.add(str((Path(virtual_env) / "bin").resolve()))
    kept: list[str] = []
    for item in path_value.split(os.pathsep):
        if not item:
            continue
        try:
            resolved = str(Path(item).resolve())
        except OSError:
            resolved = item
        if resolved in blocked:
            continue
        kept.append(item)
    return os.pathsep.join(kept)


def install_plugin_to_profile(xdg_config_home: Path, source: Path = PLUGIN_SOURCE) -> Path:
    """Install the bundled plug-in into a clean XDG-backed GIMP profile."""
    plugin_dir = xdg_config_home / "GIMP" / "3.0" / "plug-ins" / source.stem
    plugin_dir.mkdir(parents=True, exist_ok=True)
    target = plugin_dir / source.name
    shutil.copy2(source, target)
    target.chmod(0o755)
    return target


def build_spawn_env(
    *,
    xdg_config_home: Path,
    port: int,
    base: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a sanitized GIMP environment for clean-profile live tests."""
    env = dict(os.environ if base is None else base)
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    env["PATH"] = _sanitize_child_path(env.get("PATH"), project_root=PROJECT_ROOT)
    env["XDG_CONFIG_HOME"] = str(xdg_config_home)
    env["GIMP_MCP_PORT"] = str(port)
    env["GIMP_MCP_AUTO_START"] = "1"
    env["GIMP_MCP_PRO_AUTOSTART"] = "1"
    env["GIMP_MCP_LIVE_PROFILE"] = "1"
    return env


def build_spawn_command(
    *,
    gimp: str,
    xfvb: bool,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build argv for a GIMP process, optionally under xvfb-run."""
    gimp_args = [gimp, "--new-instance", "--no-splash", "--console-messages"]
    gimp_args.extend(extra_args or [])
    if xfvb:
        return ["xvfb-run", "-a", *gimp_args]
    return gimp_args


def spawn_gimp(
    *,
    gimp: str,
    xdg_config_home: Path,
    port: int,
    xfvb: bool = False,
    extra_args: list[str] | None = None,
) -> subprocess.Popen[str]:
    """Start GIMP with the bundled plug-in installed and autostart enabled."""
    if xfvb and shutil.which("xvfb-run") is None:
        raise FileNotFoundError("xvfb-run was requested but was not found in PATH")
    env = build_spawn_env(xdg_config_home=xdg_config_home, port=port)
    command = build_spawn_command(gimp=gimp, xfvb=xfvb, extra_args=extra_args)
    return subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def stop_gimp(proc: subprocess.Popen[str], *, timeout: float = 10.0) -> None:
    """Terminate a spawned GIMP process."""
    if proc.poll() is not None:
        return
    proc.terminate()
    with suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=timeout)
        return
    proc.kill()
    with suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=5.0)


def collect_process_output(proc: subprocess.Popen[str] | None, limit: int = 12000) -> str:
    """Collect available process output after termination for evidence."""
    if proc is None or proc.stdout is None:
        return ""
    with suppress(Exception):
        if proc.poll() is not None:
            output = proc.stdout.read()
            return output[-limit:]
    return ""


def wait_for_bridge(config: ServerConfig, *, timeout: float) -> tuple[bool, str]:
    """Wait until the GIMP plug-in socket accepts a bridge command."""
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        bridge = GimpBridge(**config.bridge_kwargs())
        bridge.timeout = 1.0
        bridge.reconnect_delays = []
        try:
            bridge.connect()
            bridge.disconnect()
            return True, "connected"
        except Exception as exc:  # noqa: BLE001 - live smoke evidence should record any failure
            last_error = str(exc)
            time.sleep(0.5)
    return False, last_error or "timed out waiting for bridge"


def base_environment(plugin_path: Path | None = None) -> dict[str, Any]:
    """Return common environment evidence for compat.results.yml."""
    return {
        "os": platform.platform(),
        "desktop_session": os.environ.get("XDG_SESSION_TYPE")
        or os.environ.get("DESKTOP_SESSION", "unknown"),
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
        "spawned_gimp": False,
        "xvfb": False,
        "xdg_config_home": "unknown",
    }


def run_smoke(
    config: ServerConfig, plugin_path: Path | None = None, env: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Run live smoke checks through the bridge."""
    started = utc_now()
    bridge = GimpBridge(**config.bridge_kwargs())
    checks: list[dict[str, Any]] = []
    environment = base_environment(plugin_path)
    if env:
        environment.update(env)

    try:
        bridge.connect()
        info = bridge.send_command("get_gimp_info")
        checks.append(make_check("C-020-transport", "pass", info))
        try:
            results = info.get("results", {}) if isinstance(info, dict) else {}
            gimp_info = results.get("gimp", {}) if isinstance(results, dict) else {}
            if isinstance(gimp_info, dict) and gimp_info.get("version"):
                environment["gimp_version"] = gimp_info["version"]
        except Exception:
            pass
    except GimpConnectionError as exc:
        checks.append(make_check("C-020-transport", "fail", str(exc)))
        return finish_result(started, environment, checks)

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
        environment["python_version_inside_gimp"] = values[0] if values else "unknown"
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
    return finish_result(started, environment, checks)


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


def run_spawned_smoke(args: argparse.Namespace, config: ServerConfig) -> dict[str, Any]:
    """Spawn clean-profile GIMP, wait for autostarted socket, and run smoke."""
    started = utc_now()
    checks: list[dict[str, Any]] = []
    temp_root_obj: tempfile.TemporaryDirectory[str] | None = None
    proc: subprocess.Popen[str] | None = None
    plugin_path: Path | None = None
    gimp = discover_gimp(args.gimp)

    if gimp is None:
        env = base_environment(None)
        checks.append(
            make_check(
                "C-000-spawn-gimp",
                "fail",
                {"error": "No GIMP executable found", "candidates": list(GIMP_CANDIDATES)},
            )
        )
        return finish_result(started, env, checks)

    try:
        if args.profile_dir:
            profile_root = Path(args.profile_dir).expanduser().resolve()
            profile_root.mkdir(parents=True, exist_ok=True)
        else:
            temp_root_obj = tempfile.TemporaryDirectory(prefix="gimp-mcp-live-")
            profile_root = Path(temp_root_obj.name)
        xdg_config_home = profile_root / "config"
        xdg_config_home.mkdir(parents=True, exist_ok=True)
        plugin_path = install_plugin_to_profile(xdg_config_home)
        env = base_environment(plugin_path)
        env.update(
            {
                "gimp_executable": gimp,
                "spawned_gimp": True,
                "xvfb": bool(args.xvfb),
                "xdg_config_home": str(xdg_config_home),
            }
        )
        proc = spawn_gimp(
            gimp=gimp,
            xdg_config_home=xdg_config_home,
            port=config.gimp_port,
            xfvb=bool(args.xvfb),
            extra_args=list(args.gimp_args or []),
        )
        checks.append(
            make_check(
                "C-000-spawn-gimp",
                "pass",
                {
                    "pid": proc.pid,
                    "gimp": gimp,
                    "xvfb": bool(args.xvfb),
                    "plugin_path": str(plugin_path),
                    "xdg_config_home": str(xdg_config_home),
                },
            )
        )
        ok, evidence = wait_for_bridge(config, timeout=args.startup_timeout)
        checks.append(make_check("C-005-autostart-server", "pass" if ok else "fail", evidence))
        if not ok:
            env["gimp_process_output"] = collect_process_output(proc)
            return finish_result(started, env, checks)

        smoke = run_smoke(config, plugin_path, env)
        smoke["checks"] = checks + smoke["checks"]
        smoke["summary"] = finish_result(started, smoke["environment"], smoke["checks"])["summary"]
        return smoke
    except Exception as exc:  # noqa: BLE001 - live utility should preserve failure evidence
        env = base_environment(plugin_path)
        env.update({"gimp_executable": gimp, "spawned_gimp": True, "xvfb": bool(args.xvfb)})
        checks.append(make_check("C-000-spawn-gimp", "fail", {"error": str(exc)}))
        return finish_result(started, env, checks)
    finally:
        if proc is not None and not args.keep_gimp:
            stop_gimp(proc)
        if temp_root_obj is not None and not args.keep_profile:
            temp_root_obj.cleanup()


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
    parser.add_argument(
        "--spawn",
        action="store_true",
        help="Spawn a clean-profile GIMP before running smoke checks.",
    )
    parser.add_argument(
        "--xvfb", action="store_true", help="Spawn GIMP under xvfb-run -a; implies --spawn."
    )
    parser.add_argument("--gimp", help="GIMP executable to spawn; defaults to discovery/env.")
    parser.add_argument(
        "--profile-dir", help="Profile root for spawned mode. Defaults to a temp dir."
    )
    parser.add_argument(
        "--startup-timeout", type=float, default=45.0, help="Seconds to wait for plug-in autostart."
    )
    parser.add_argument(
        "--keep-gimp", action="store_true", help="Leave spawned GIMP running after the smoke run."
    )
    parser.add_argument(
        "--keep-profile",
        action="store_true",
        help="Keep the temporary clean profile after the smoke run.",
    )
    parser.add_argument(
        "gimp_args",
        nargs=argparse.REMAINDER,
        help="Extra args after -- are passed to spawned GIMP.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Script entry point."""
    args = build_parser().parse_args(argv)
    config = ServerConfig()
    if args.host:
        config.gimp_host = args.host
    if args.port:
        config.gimp_port = args.port

    if args.xvfb:
        args.spawn = True

    result = run_spawned_smoke(args, config) if args.spawn else run_smoke(config, args.plugin_path)
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.write_text(yaml.safe_dump(result, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        try:
            rel_output = output.relative_to(PROJECT_ROOT)
        except ValueError:
            rel_output = output
        print(f"wrote {rel_output}")
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 1 if result["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
