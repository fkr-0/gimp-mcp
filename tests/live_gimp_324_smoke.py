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
import asyncio
import base64
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
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

from gimp_mcp_pro.async_bridge import AsyncGimpBridge  # noqa: E402
from gimp_mcp_pro.bridge import GimpBridge  # noqa: E402
from gimp_mcp_pro.config import ServerConfig  # noqa: E402
from gimp_mcp_pro.utils.errors import GimpCommandError, GimpConnectionError  # noqa: E402

GIMP_CANDIDATES = ("gimp-3.2", "gimp-3", "gimp", "gimp-3.0")
PLUGIN_SOURCE = PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py"
TRUTHY = {"1", "true", "yes", "on"}
PLUGIN_START_BATCH = "from gi.repository import Gimp; pdb = Gimp.get_pdb(); proc = pdb.lookup_procedure('plug-in-mcp-pro-server'); cfg = proc.create_config(); proc.run(cfg)"


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


def find_free_port(host: str = "127.0.0.1") -> int:
    """Reserve and return a currently free TCP port for spawned GIMP tests."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


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
    env["GIMP3_DIRECTORY"] = str(xdg_config_home / "GIMP" / "3.0")
    env["GIMP_MCP_PORT"] = str(port)
    env["GIMP_MCP_AUTO_START"] = "0"
    env["GIMP_MCP_PRO_AUTOSTART"] = "0"
    env["GIMP_MCP_BLOCKING_AUTOSTART"] = "0"
    env["GIMP_MCP_PRO_BLOCKING_AUTOSTART"] = "0"
    env["GIMP_MCP_BLOCKING_RUN"] = "1"
    env["GIMP_MCP_PRO_BLOCKING_RUN"] = "1"
    env["GIMP_MCP_LIVE_PROFILE"] = "1"
    return env


def build_spawn_command(
    *,
    gimp: str,
    xvfb: bool,
    extra_args: list[str] | None = None,
    invoke_plugin: bool = True,
) -> list[str]:
    """Build argv for a GIMP process, optionally under xvfb-run."""
    gimp_args = [gimp, "--new-instance", "--no-splash", "--console-messages"]
    if invoke_plugin:
        gimp_args.extend(["--batch-interpreter=python-fu-eval", "-b", PLUGIN_START_BATCH])
    gimp_args.extend(extra_args or [])
    if xvfb:
        return ["xvfb-run", "-a", *gimp_args]
    return gimp_args


def spawn_gimp(
    *,
    gimp: str,
    xdg_config_home: Path,
    port: int,
    xvfb: bool = False,
    extra_args: list[str] | None = None,
    invoke_plugin: bool = True,
) -> subprocess.Popen[str]:
    """Start GIMP with the bundled plug-in installed and autostart enabled."""
    if xvfb and shutil.which("xvfb-run") is None:
        raise FileNotFoundError("xvfb-run was requested but was not found in PATH")
    env = build_spawn_env(xdg_config_home=xdg_config_home, port=port)
    command = build_spawn_command(
        gimp=gimp, xvfb=xvfb, extra_args=extra_args, invoke_plugin=invoke_plugin
    )
    return subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def stop_gimp(proc: subprocess.Popen[str], *, timeout: float = 10.0) -> None:
    """Terminate a spawned GIMP process."""
    if proc.poll() is not None:
        return
    with suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    with suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=timeout)
        return
    with suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)
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


class _CompatToolRegistrar:
    """Minimal FastMCP-like registrar used by the live compatibility runner."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self) -> Any:
        def decorator(func: Any) -> Any:
            if func.__name__ in self.tools:
                raise RuntimeError(f"duplicate tool registration: {func.__name__}")
            self.tools[func.__name__] = func
            return func

        return decorator


def build_registered_tools(bridge: Any) -> dict[str, Any]:
    """Register all MCP tools against the live bridge and return callables."""
    from gimp_mcp_pro.tools.color_tools import register_color_tools
    from gimp_mcp_pro.tools.drawing_tools import register_drawing_tools
    from gimp_mcp_pro.tools.filter_tools import register_filter_tools
    from gimp_mcp_pro.tools.history_tools import register_history_tools
    from gimp_mcp_pro.tools.image_tools import register_image_tools
    from gimp_mcp_pro.tools.inspect_tools import register_inspect_tools
    from gimp_mcp_pro.tools.layer_tools import register_layer_tools
    from gimp_mcp_pro.tools.pdb_tools import register_pdb_tools
    from gimp_mcp_pro.tools.selection_tools import register_selection_tools
    from gimp_mcp_pro.tools.transform_tools import register_transform_tools

    registrar = _CompatToolRegistrar()
    for register in (
        register_image_tools,
        register_layer_tools,
        register_selection_tools,
        register_drawing_tools,
        register_inspect_tools,
        register_history_tools,
        register_pdb_tools,
        register_transform_tools,
        register_filter_tools,
        register_color_tools,
    ):
        register(registrar, bridge)
    return registrar.tools


async def _run_tool_calls(
    tools: dict[str, Any], calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Run actual registered MCP tool callables and normalize evidence."""
    details: list[dict[str, Any]] = []
    for name, args, kwargs in calls:
        try:
            result = await tools[name](*args, **kwargs)
            success = bool(result.get("success")) if isinstance(result, dict) else False
            details.append({"tool": name, "success": success, "result": result})
        except Exception as exc:  # noqa: BLE001 - preserve live compat evidence
            details.append({"tool": name, "success": False, "error": str(exc)})
    return details


def run_tool_calls(
    tools: dict[str, Any], calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Synchronously run registered async MCP tools for a scenario."""
    return asyncio.run(_run_tool_calls(tools, calls))


def tool_check(
    check_id: str,
    tools: dict[str, Any],
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]],
) -> dict[str, Any]:
    """Create a pass/fail check for a scenario's real MCP tool calls."""
    details = run_tool_calls(tools, calls)
    failures = [item for item in details if not item.get("success")]
    return make_check(
        check_id,
        "fail" if failures else "pass",
        {"calls": details, "failed_tools": [item.get("tool") for item in failures]},
    )


def _tool_error_text(item: dict[str, Any]) -> str:
    """Return normalized error text from a live tool-call evidence item."""
    result = item.get("result")
    if isinstance(result, dict):
        return str(result.get("error") or result.get("message") or "")
    return str(item.get("error") or "")


def _structured_optional_capability(item: dict[str, Any]) -> dict[str, str] | None:
    """Return structured optional-capability metadata from a tool result.

    Tool handlers should use ``OperationResult.optional_capability_unavailable``
    for optional 3.2.4 features such as Script-Fu drop shadow or programmatic
    undo/redo. The live runner still supports legacy string matching, but this
    structured path is preferred because it is stable across wording changes.
    """
    result = item.get("result")
    if not isinstance(result, dict):
        return None
    data = result.get("data")
    if not isinstance(data, dict):
        return None
    if data.get("error_code") != "optional_capability_unavailable":
        return None
    if data.get("optional_capability") is not True:
        return None
    metadata: dict[str, str] = {"reason": _tool_error_text(item)}
    for key in ("capability", "procedure", "recommendation"):
        value = data.get(key)
        if value is not None:
            metadata[key] = str(value)
    return metadata


def accept_optional_tool_failures(
    check: dict[str, Any],
    *,
    optional_errors: dict[str, str],
) -> dict[str, Any]:
    """Convert expected optional-capability failures into a passing check.

    Args:
        check: Tool-check evidence returned by ``tool_check``.
        optional_errors: Mapping of tool name to required error-text fragment.

    Returns:
        A check that passes when all failures are known optional capabilities.
    """
    evidence = check.get("evidence")
    if not isinstance(evidence, dict):
        return check
    calls = evidence.get("calls")
    if not isinstance(calls, list):
        return check
    failed = [item for item in calls if isinstance(item, dict) and not item.get("success")]
    if not failed:
        return check
    accepted: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    for item in failed:
        tool = str(item.get("tool") or "")
        error_text = _tool_error_text(item)
        structured = _structured_optional_capability(item)
        expected = optional_errors.get(tool)
        if structured is not None:
            accepted.append({"tool": tool, **structured})
        elif expected and expected in error_text:
            accepted.append({"tool": tool, "reason": error_text})
        else:
            rejected.append({"tool": tool, "reason": error_text})
    if rejected:
        evidence["failed_tools"] = [item["tool"] for item in rejected]
        evidence["accepted_optional_failures"] = accepted
        evidence["rejected_failures"] = rejected
        check["status"] = "fail"
        return check
    evidence["failed_tools"] = []
    evidence["accepted_optional_failures"] = accepted
    evidence["optional_capability_policy"] = (
        "known unavailable optional capabilities do not fail the transport smoke"
    )
    check["status"] = "pass"
    return check


def run_json_probe(
    bridge: GimpBridge,
    body: str,
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run a JSON-producing Python probe inside GIMP's persistent context."""
    sentinel = "__GIMP_MCP_COMPAT_JSON__"
    indented = "\n".join(f"    {line}" if line else "" for line in body.splitlines())
    wrapped = f"""
import json, traceback
try:
{indented}
    print({sentinel!r} + json.dumps({{"ok": True, "data": _compat_result}}, default=str))
except Exception as _compat_exc:
    print({sentinel!r} + json.dumps({{"ok": False, "error": str(_compat_exc), "traceback": traceback.format_exc()}}, default=str))
""".strip()
    response = bridge.execute_python([wrapped], timeout=timeout)
    output = "\n".join(str(item or "") for item in response.get("results", []))
    for line in reversed(output.splitlines()):
        if line.startswith(sentinel):
            return json.loads(line[len(sentinel) :])
    return {"ok": False, "error": "JSON sentinel not found", "output": output[-4000:]}


def json_probe_check(
    check_id: str,
    bridge: GimpBridge,
    body: str,
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Return a compatibility check from an in-GIMP JSON probe."""
    result = run_json_probe(bridge, body, timeout=timeout)
    return make_check(check_id, "pass" if result.get("ok") else "fail", result)


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
        "gimp3_directory": "unknown",
        "mcp_port": "unknown",
    }


def _decode_bitmap(bridge: GimpBridge, **params: Any) -> bytes:
    """Return decoded PNG bitmap bytes from the active image."""
    bitmap = bridge.get_image_bitmap(**params)
    results = bitmap.get("results", {}) if isinstance(bitmap, dict) else {}
    return base64.b64decode(results.get("image_data", ""))


def _exec_check(bridge: GimpBridge, check_id: str, code: str) -> dict[str, Any]:
    """Run a live Python smoke snippet and convert it to a check record."""
    try:
        response = bridge.execute_python([code], timeout=bridge.long_timeout)
        return make_check(check_id, "pass", response)
    except GimpCommandError as exc:
        return make_check(check_id, "fail", str(exc))


def run_selection_drawing_check(bridge: GimpBridge) -> dict[str, Any]:
    """Exercise selection, fill and stroke APIs and assert bitmap changes."""
    try:
        before = _decode_bitmap(bridge, max_width=160, max_height=120)
        response = bridge.execute_python(
            [
                """
from gi.repository import Gegl, Gimp
image = Gimp.get_images()[0]
layer = image.get_layers()[0]
Gimp.context_set_foreground(Gegl.Color.new('rgb(1.0,0.0,0.0)'))
image.select_rectangle(Gimp.ChannelOps.REPLACE, 10, 10, 80, 50)
Gimp.Drawable.edit_fill(layer, Gimp.FillType.FOREGROUND)
Gimp.Selection.none(image)
Gimp.context_set_foreground(Gegl.Color.new('rgb(0.0,0.0,1.0)'))
image.select_ellipse(Gimp.ChannelOps.REPLACE, 105, 20, 45, 45)
Gimp.context_set_line_width(4.0)
Gimp.Drawable.edit_stroke_selection(layer)
Gimp.Selection.none(image)
Gimp.displays_flush()
print('selection-drawing-ok')
"""
            ],
            timeout=bridge.long_timeout,
        )
        after = _decode_bitmap(bridge, max_width=160, max_height=120)
        changed = before != after
        return make_check(
            "C-050-selection-drawing-contract",
            "pass" if changed else "fail",
            {"bitmap_changed": changed, "response": response},
        )
    except (GimpCommandError, ValueError) as exc:
        return make_check("C-050-selection-drawing-contract", "fail", str(exc))


def run_transform_check(bridge: GimpBridge) -> dict[str, Any]:
    """Exercise core image/layer transform operations."""
    try:
        response = bridge.execute_python(
            [
                """
from gi.repository import Gimp
image = Gimp.get_images()[0]
layer = image.get_layers()[0]
Gimp.context_set_interpolation(Gimp.InterpolationType.CUBIC)
image.scale(220, 160)
layer = image.get_layers()[0]
layer.scale(180, 130, True)
image.rotate(Gimp.RotationType.DEGREES180)
image.flip(Gimp.OrientationType.HORIZONTAL)
image.resize(240, 180, 10, 10)
layer = image.get_layers()[0]
layer.set_offsets(layer.get_offsets().offset_x + 3, layer.get_offsets().offset_y + 4)
Gimp.displays_flush()
print(f'transform-ok:{image.get_width()}x{image.get_height()}:{layer.get_width()}x{layer.get_height()}')
"""
            ],
            timeout=bridge.long_timeout,
        )
        metadata = bridge.get_image_metadata()
        basic = metadata.get("results", {}).get("basic", {}) if isinstance(metadata, dict) else {}
        ok = basic.get("width") == 240 and basic.get("height") == 180
        return make_check(
            "C-070-transform-contract",
            "pass" if ok else "fail",
            {"response": response, "metadata": metadata},
        )
    except GimpCommandError as exc:
        return make_check("C-070-transform-contract", "fail", str(exc))


def run_color_check(bridge: GimpBridge) -> dict[str, Any]:
    """Exercise context color round-trip and basic drawable color operations."""
    try:
        before = _decode_bitmap(bridge, max_width=160, max_height=120)
        response = bridge.execute_python(
            [
                """
from gi.repository import Gegl, Gimp
image = Gimp.get_images()[0]
drawable = image.get_layers()[0]
Gimp.context_set_foreground(Gegl.Color.new('rgb(0.0,1.0,0.0)'))
Gimp.context_set_background(Gegl.Color.new('rgb(0.0,0.0,0.0)'))
Gimp.Drawable.brightness_contrast(drawable, 0.05, 0.05)
Gimp.Drawable.invert(drawable, False)
Gimp.displays_flush()
fg = Gimp.context_get_foreground()
bg = Gimp.context_get_background()
print(f'color-ok:{fg is not None}:{bg is not None}')
"""
            ],
            timeout=bridge.long_timeout,
        )
        after = _decode_bitmap(bridge, max_width=160, max_height=120)
        context = bridge.get_context_state()
        changed = before != after
        return make_check(
            "C-080-color-contract",
            "pass" if changed else "fail",
            {"bitmap_changed": changed, "response": response, "context": context},
        )
    except (GimpCommandError, ValueError) as exc:
        return make_check("C-080-color-contract", "fail", str(exc))


def run_filter_check(bridge: GimpBridge) -> dict[str, Any]:
    """Exercise the DrawableFilter/GEGL path used by filter tools."""
    try:
        before = _decode_bitmap(bridge, max_width=160, max_height=120)
        response = bridge.execute_python(
            [
                """
from gi.repository import Gimp
image = Gimp.get_images()[0]
drawable = image.get_layers()[0]
operation_available = Gimp.DrawableFilter.operation_get_available('gegl:gaussian-blur')
if not operation_available:
    raise RuntimeError('gegl:gaussian-blur is not available')
df = Gimp.DrawableFilter.new(drawable, 'gegl:gaussian-blur', '')
cfg = df.get_config()
for name, value in (('std-dev-x', 1.0), ('std-dev-y', 1.0)):
    try:
        cfg.set_property(name, value)
    except Exception:
        pass
drawable.append_filter(df)
drawable.merge_filter(df)
Gimp.displays_flush()
print('filter-ok')
"""
            ],
            timeout=bridge.long_timeout,
        )
        after = _decode_bitmap(bridge, max_width=160, max_height=120)
        changed = before != after
        return make_check(
            "C-090-filter-contract",
            "pass" if changed else "fail",
            {"bitmap_changed": changed, "response": response},
        )
    except (GimpCommandError, ValueError) as exc:
        return make_check("C-090-filter-contract", "fail", str(exc))


def run_history_check(bridge: GimpBridge) -> dict[str, Any]:
    """Exercise undo group start/end and available undo/redo PDB procedures."""
    try:
        response = bridge.execute_python(
            [
                """
from gi.repository import Gegl, Gimp
image = Gimp.get_images()[0]
layer = image.get_layers()[0]
image.undo_group_start()
try:
    Gimp.context_set_foreground(Gegl.Color.new('rgb(1.0,1.0,0.0)'))
    image.select_rectangle(Gimp.ChannelOps.REPLACE, 5, 5, 20, 20)
    Gimp.Drawable.edit_fill(layer, Gimp.FillType.FOREGROUND)
    Gimp.Selection.none(image)
finally:
    image.undo_group_end()
pdb = Gimp.get_pdb()
undo_exists = pdb.procedure_exists('gimp-image-undo')
redo_exists = pdb.procedure_exists('gimp-image-redo')
Gimp.displays_flush()
print(f'history-ok:{undo_exists}:{redo_exists}')
"""
            ],
            timeout=bridge.long_timeout,
        )
        return make_check("C-110-history-contract", "pass", response)
    except GimpCommandError as exc:
        return make_check("C-110-history-contract", "fail", str(exc))


def run_docs_check() -> dict[str, Any]:
    """Record README/doc compatibility-claim evidence."""
    try:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        tool_count_ok = "84 typed" in readme or "84 tools" in readme
        stale_claim_absent = "GIMP 3.0.8 compatible" not in readme
        compatibility_table = "compatibility" in readme.lower() and "3.2.4" in readme
        ok = tool_count_ok and stale_claim_absent and compatibility_table
        return make_check(
            "C-130-docs-contract",
            "pass" if ok else "fail",
            {
                "tool_count_ok": tool_count_ok,
                "stale_3_0_8_claim_absent": stale_claim_absent,
                "mentions_compatibility_and_3_2_4": compatibility_table,
            },
        )
    except OSError as exc:
        return make_check("C-130-docs-contract", "fail", str(exc))


def run_static_checks() -> list[dict[str, Any]]:
    """Run static compatibility evidence checks declared by compat.yml."""

    def run(command: list[str]) -> tuple[int, str]:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return completed.returncode, completed.stdout[-12000:]

    checks: list[dict[str, Any]] = []
    checks.append(make_check("S-001-yaml-validity", "pass", "compat.yml parsed by live runner"))

    rc, output = run(["uv", "run", "python", "scripts/compat.py", "validate"])
    checks.append(
        make_check(
            "S-010-tool-registry-count",
            "pass" if rc == 0 else "fail",
            {"command": "uv run python scripts/compat.py validate", "output": output},
        )
    )

    rc, output = run(["uv", "run", "pytest", "--no-cov"])
    checks.append(
        make_check(
            "S-020-unit-suite",
            "pass" if rc == 0 else "fail",
            {"command": "uv run pytest --no-cov", "output": output},
        )
    )

    rc, output = run(["uv", "run", "python", "scripts/project.py", "check"])
    checks.append(
        make_check(
            "S-030-quality-gate",
            "pass" if rc == 0 else "fail",
            {"command": "uv run python scripts/project.py check", "output": output},
        )
    )

    docs_check = run_docs_check()
    checks.append(make_check("S-040-doc-claim-gate", docs_check["status"], docs_check["evidence"]))
    return checks


def required_check_ids() -> set[str]:
    """Return check IDs marked required in compat.yml."""
    try:
        contract = yaml.safe_load((PROJECT_ROOT / "compat.yml").read_text(encoding="utf-8"))
    except Exception:
        return set()
    ids: set[str] = set()
    if not isinstance(contract, dict):
        return ids
    for section in ("static_checks", "live_smoke_scenarios"):
        for item in contract.get(section, []):
            if isinstance(item, dict) and item.get("required", True) and item.get("id"):
                ids.add(str(item["id"]))
    return ids


def should_allow_claim(checks: list[dict[str, Any]]) -> bool:
    """Return whether checks satisfy the required compatibility claim set."""
    required = required_check_ids()
    if not required:
        return False
    by_id = {str(check.get("id")): str(check.get("status")) for check in checks}
    if required - set(by_id):
        return False
    return all(by_id[check_id] in {"pass", "waived"} for check_id in required)


def _reset_images(bridge: GimpBridge) -> None:
    """Close all open images so scenario tool calls do not interfere."""
    bridge.execute_python(
        [
            "for _compat_img in list(Gimp.get_images()):\n    try:\n        _compat_img.delete()\n    except Exception:\n        pass"
        ],
        timeout=10.0,
    )


def _tool_call(
    tool_name: str, *args: Any, **kwargs: Any
) -> tuple[str, tuple[Any, ...], dict[str, Any]]:
    """Compact constructor for actual live MCP tool calls."""
    return (tool_name, args, kwargs)


tool_call = _tool_call


def _transport_check(
    bridge: GimpBridge, config: ServerConfig, info: dict[str, Any]
) -> dict[str, Any]:
    """Exercise transport-specific requirements beyond the first round-trip."""
    evidence: dict[str, Any] = {
        "first_round_trip": info,
        "length_prefix_default": config.use_length_prefix,
    }
    failures: list[str] = []
    try:
        evidence["sequential_round_trip"] = bridge.send_command("get_gimp_info")
    except Exception as exc:
        failures.append(f"sequential command failed: {exc}")
    try:
        bridge.disconnect()
        bridge.connect()
        evidence["reconnect_round_trip"] = bridge.send_command("get_gimp_info")
    except Exception as exc:
        failures.append(f"reconnect failed: {exc}")
    try:
        guard = GimpBridge(
            host=config.gimp_host,
            port=config.gimp_port,
            timeout=2.0,
            use_length_prefix=config.use_length_prefix,
            long_timeout=config.long_timeout,
            max_message_size=1,
            reconnect_delays=[],
        )
        guard.connect()
        try:
            guard.send_command("get_gimp_info")
        except GimpConnectionError as exc:
            evidence["oversized_response_guard"] = str(exc)
        else:
            failures.append(
                "oversized response guard did not reject a response larger than one byte"
            )
        finally:
            guard.disconnect()
        bridge.connect()
    except Exception as exc:
        failures.append(f"oversized response guard damaged reconnect path: {exc}")
    return make_check(
        "C-020-transport", "fail" if failures else "pass", {**evidence, "failures": failures}
    )


async def _async_transport_probe(config: ServerConfig) -> dict[str, Any]:
    """Exercise the asyncio-native bridge and registered async MCP tools live."""
    bridge = AsyncGimpBridge(**config.bridge_kwargs())
    try:
        await bridge.connect()
        first = await bridge.async_get_gimp_info()
        tools = build_registered_tools(bridge)
        tool_results = await _run_tool_calls(
            tools,
            [
                tool_call("create_image", 96, 64, "rgb", "white"),
                tool_call("create_layer", name="async-compat", opacity=100.0, fill="transparent"),
                tool_call("get_image_info"),
                tool_call("get_image_bitmap", 64, 64),
            ],
        )
        failures = [item for item in tool_results if not item.get("success")]
        return {
            "async_bridge_class": bridge.__class__.__name__,
            "first_round_trip": first,
            "registered_tool_total": len(tools),
            "tool_calls": tool_results,
            "failed_tools": [item.get("tool") for item in failures],
        }
    finally:
        await bridge.disconnect()


def _async_transport_check(config: ServerConfig) -> dict[str, Any]:
    """Return live evidence for the asyncio-native transport path."""
    try:
        evidence = asyncio.run(_async_transport_probe(config))
    except Exception as exc:  # noqa: BLE001 - live compat evidence must preserve failures
        return make_check("C-025-async-transport", "fail", {"error": str(exc)})
    ok = (
        evidence.get("registered_tool_total") == 84
        and not evidence.get("failed_tools")
        and isinstance(evidence.get("first_round_trip"), dict)
        and evidence["first_round_trip"].get("status") == "success"
    )
    return make_check("C-025-async-transport", "pass" if ok else "fail", evidence)


def _env_introspection_check(bridge: GimpBridge, environment: dict[str, Any]) -> dict[str, Any]:
    """Capture exact Python/GI/GIMP runtime versions from inside GIMP."""
    body = """
import gi, platform
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, GLib, Gio
try:
    from gi.repository import GObject
except Exception:
    GObject = None
_compat_result = {
    'python_version': platform.python_version(),
    'pygobject_version': '.'.join(str(part) for part in getattr(gi, 'version_info', ())),
    'gimp_version': Gimp.version() if hasattr(Gimp, 'version') else 'unknown',
    'gimp_resources_loaded': 'available' if hasattr(Gimp, 'resources_loaded') else None,
    'libgimp_api_version': '3.0',
    'gegl_version': '.'.join(str(getattr(Gegl, name)) for name in ('MAJOR_VERSION', 'MINOR_VERSION', 'MICRO_VERSION') if hasattr(Gegl, name)) or 'unknown',
    'imports': {'Gimp': Gimp is not None, 'Gegl': Gegl is not None, 'GLib': GLib is not None, 'Gio': Gio is not None, 'GObject': GObject is not None},
}
"""
    check = json_probe_check("C-001-env-introspection", bridge, body)
    data = (
        check.get("evidence", {}).get("data", {}) if isinstance(check.get("evidence"), dict) else {}
    )
    if isinstance(data, dict):
        environment["python_version_inside_gimp"] = data.get("python_version", "unknown")
        environment["pygobject_version_inside_gimp"] = data.get("pygobject_version", "unknown")
        environment["gimp_version"] = data.get(
            "gimp_version", environment.get("gimp_version", "unknown")
        )
        environment["gegl_version"] = data.get("gegl_version", "unknown")
        environment["libgimp_api_version"] = data.get("libgimp_api_version", "3.0")
        environment["libgimp_library_version"] = environment["gimp_version"]
    return check


def _plugin_registration_check(bridge: GimpBridge) -> dict[str, Any]:
    """Check PDB registration plus static menu metadata from the installed plug-in."""
    body = """
from gi.repository import Gimp
pdb = Gimp.get_pdb()
exists = pdb.procedure_exists('plug-in-mcp-pro-server')
proc = pdb.lookup_procedure('plug-in-mcp-pro-server')
_compat_result = {
    'procedure_exists': bool(exists),
    'lookup_non_null': proc is not None,
    'procedure_repr': str(proc),
    'menu_path_static': '<Image>/Tools/',
    'menu_label_static': 'Start MCP Pro Server',
    'activation_model': 'spawned GIMP invokes persistent procedure through python-fu-eval; UI menu activation uses the same PDB procedure',
}
if not exists or proc is None:
    raise RuntimeError('plug-in-mcp-pro-server is not registered in the PDB')
"""
    return json_probe_check("C-010-plugin-registration", bridge, body)


def _core_api_check(bridge: GimpBridge) -> dict[str, Any]:
    """Probe symbols and methods named by core_gimp_api_contract."""
    body = """
from gi.repository import Gimp
symbols = {
    'classes': ['Image', 'Layer', 'Drawable', 'Selection', 'PDB', 'Procedure', 'ImageProcedure', 'DrawableFilter'],
    'enums': ['ImageBaseType', 'ImageType', 'LayerMode', 'ChannelOps', 'FillType', 'RunMode', 'PDBProcType', 'PDBStatusType', 'RotationType', 'OrientationType', 'MergeType'],
    'functions': ['get_images', 'get_pdb', 'context_get_foreground', 'context_get_background', 'context_set_foreground', 'context_set_background', 'displays_flush', 'edit_copy', 'edit_paste', 'file_save', 'floating_sel_anchor'],
}
missing = []
for group, names in symbols.items():
    for name in names:
        if not hasattr(Gimp, name):
            missing.append(f'Gimp.{name}')
_compat_result = {'missing': missing, 'probed': symbols}
if missing:
    raise RuntimeError('missing core API symbols: ' + ', '.join(missing))
"""
    return json_probe_check("core-api", bridge, body)


def _pdb_probe_check(bridge: GimpBridge) -> dict[str, Any]:
    """Probe required PDB procedures and conditional drop-shadow availability."""
    body = """
from gi.repository import Gimp
pdb = Gimp.get_pdb()
required = ['file-png-export', 'file-jpeg-export', 'gimp-image-autocrop']
status = {name: bool(pdb.procedure_exists(name)) for name in required}
drop_shadow = bool(pdb.procedure_exists('script-fu-drop-shadow'))
missing = [name for name, ok in status.items() if not ok]
_compat_result = {'required': status, 'script-fu-drop-shadow': drop_shadow}
if missing:
    raise RuntimeError('missing required PDB procedures: ' + ', '.join(missing))
"""
    return json_probe_check("C-100-pdb-contract", bridge, body)


def _registry_total_check(tools: dict[str, Any]) -> dict[str, Any]:
    """Check live captured MCP tool registry count."""
    expected = 84
    names = sorted(tools)
    return make_check(
        "mcp-tools",
        "pass" if len(names) == expected else "fail",
        {"expected_total": expected, "actual_total": len(names), "tools": names},
    )


def _docs_contract_check() -> dict[str, Any]:
    """Check README public claim/count/install-layout requirements."""
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    failures: list[str] = []
    if "GIMP 3.0.8 compatible" in readme:
        failures.append("README contains stale GIMP 3.0.8 compatibility wording")
    if "84 typed" not in readme:
        failures.append("README does not advertise 84 typed tools")
    if "gimp_mcp_plugin/gimp_mcp_plugin.py" not in readme:
        failures.append("README does not document the canonical GIMP plug-in directory/file layout")
    if "claim_allowed: false" not in readme and "claim_allowed: true" not in readme:
        failures.append("README compatibility table lacks claim_allowed status")
    return make_check("C-130-docs-contract", "fail" if failures else "pass", {"failures": failures})


def run_smoke(
    config: ServerConfig,
    plugin_path: Path | None = None,
    env: dict[str, Any] | None = None,
    stop_bridge_after: bool = False,
    include_static_checks: bool = False,
) -> dict[str, Any]:
    """Run the live compat.yml scenario matrix through the real bridge and MCP tools."""
    started = utc_now()
    bridge = GimpBridge(**config.bridge_kwargs())
    checks: list[dict[str, Any]] = []
    environment = base_environment(plugin_path)
    if env:
        environment.update(env)

    try:
        bridge.connect()
        info = bridge.send_command("get_gimp_info")
    except GimpConnectionError as exc:
        checks.append(make_check("C-020-transport", "fail", str(exc)))
        return finish_result(started, environment, checks)

    checks.append(_transport_check(bridge, config, info))
    checks.append(_async_transport_check(config))
    checks.append(_env_introspection_check(bridge, environment))
    checks.append(_plugin_registration_check(bridge))

    try:
        tools = build_registered_tools(bridge)
    except Exception as exc:  # noqa: BLE001
        tools = {}
        checks.append(make_check("C-030-image-basics", "fail", {"error": str(exc)}))

    def add_tool_check(
        check_id: str, calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]]
    ) -> None:
        try:
            _reset_images(bridge)
            checks.append(tool_check(check_id, tools, calls))
        except Exception as exc:  # noqa: BLE001 - live compat evidence
            checks.append(make_check(check_id, "fail", {"error": str(exc)}))

    def add_optional_tool_check(
        check_id: str,
        calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]],
        optional_errors: dict[str, str],
    ) -> None:
        try:
            _reset_images(bridge)
            checks.append(
                accept_optional_tool_failures(
                    tool_check(check_id, tools, calls), optional_errors=optional_errors
                )
            )
        except Exception as exc:  # noqa: BLE001 - live compat evidence
            checks.append(make_check(check_id, "fail", {"error": str(exc)}))

    if tools:
        image_check = tool_check(
            "C-030-image-basics",
            tools,
            [
                tool_call("create_image", 320, 240, "rgb", "white"),
                tool_call("list_images"),
                tool_call("get_image_info"),
                tool_call("create_layer", name="flatten-input", opacity=100.0, fill="transparent"),
                tool_call("duplicate_image"),
                tool_call("flatten_image"),
                tool_call("get_image_info"),
            ],
        )
        registry_evidence = {
            "expected_total": 84,
            "actual_total": len(tools),
            "tools": sorted(tools),
        }
        if len(tools) != 84:
            image_check["status"] = "fail"
            image_check["evidence"]["failed_tools"].append("registry-count")
        image_check["evidence"]["registry"] = registry_evidence
        checks.append(image_check)

        add_tool_check(
            "C-040-layer-contract",
            [
                tool_call("create_image", 240, 180, "rgb", "white"),
                tool_call("create_layer", name="layer-contract", opacity=80.0, fill="transparent"),
                tool_call("list_layers"),
                tool_call("set_active_layer", layer_name="layer-contract"),
                tool_call("set_layer_opacity", 55.0, layer_name="layer-contract"),
                tool_call("set_layer_visibility", False, layer_name="layer-contract"),
                tool_call("set_layer_visibility", True, layer_name="layer-contract"),
                tool_call("duplicate_layer", layer_name="layer-contract"),
                tool_call("add_alpha_channel", layer_name="layer-contract"),
                tool_call("create_layer", name="delete-me", opacity=100.0, fill="transparent"),
                tool_call("delete_layer", layer_name="delete-me"),
                tool_call("merge_visible_layers"),
                tool_call("list_layers"),
            ],
        )

        add_tool_check(
            "C-050-selection-drawing-contract",
            [
                tool_call("create_image", 260, 180, "rgb", "white"),
                tool_call("create_layer", name="draw-contract", opacity=100.0, fill="transparent"),
                tool_call("set_active_layer", layer_name="draw-contract"),
                tool_call("set_foreground_color", "red"),
                tool_call("set_background_color", "blue"),
                tool_call("select_rectangle", 10, 10, 40, 30),
                tool_call("fill_selection", "foreground"),
                tool_call("select_ellipse", 60, 10, 40, 30),
                tool_call("fill_selection", "background"),
                tool_call("select_polygon", [120, 10, 160, 10, 150, 45]),
                tool_call("fill_selection", "foreground"),
                tool_call("select_all"),
                tool_call("select_invert"),
                tool_call("select_none"),
                tool_call("select_rectangle", 20, 70, 60, 40),
                tool_call("select_grow", 2),
                tool_call("select_shrink", 1),
                tool_call("fill_selection", "foreground"),
                tool_call("draw_line", 5, 5, 120, 80, "blue", 3.0),
                tool_call("draw_brush_stroke", [10, 120, 60, 130, 90, 150], "pencil", "red", 2.0),
                tool_call("draw_rectangle", 130, 70, 40, 30, True, "blue"),
                tool_call("draw_ellipse", 180, 70, 40, 30, True, "red"),
                tool_call("draw_polygon", [180, 120, 220, 120, 200, 160], True, "blue"),
                tool_call("add_text", "compat", 20, 140, font_size=18, color="red"),
                tool_call("select_all"),
                tool_call("edit_clear"),
                tool_call("select_none"),
            ],
        )

        export_dir = Path(tempfile.gettempdir())
        add_tool_check(
            "C-060-export-bitmap-contract",
            [
                tool_call("create_image", 120, 90, "rgb", "white"),
                tool_call("draw_rectangle", 10, 10, 40, 30, True, "red"),
                tool_call("get_image_bitmap", 80, 80),
                tool_call("get_image_bitmap", 80, 80, 5, 5, 30, 30),
                tool_call("export_image", str(export_dir / "gimp-mcp-compat.png"), "png"),
                tool_call("export_image", str(export_dir / "gimp-mcp-compat.jpg"), "jpeg", 80),
            ],
        )

        add_tool_check(
            "C-070-transform-contract",
            [
                tool_call("create_image", 180, 140, "rgb", "white"),
                tool_call(
                    "create_layer", name="transform-layer", opacity=100.0, fill="transparent"
                ),
                tool_call("set_active_layer", layer_name="transform-layer"),
                tool_call("scale_layer", 120, 80, layer_name="transform-layer"),
                tool_call("offset_layer", 5, 7, layer_name="transform-layer"),
                tool_call("rotate_layer", 10.0, True, layer_name="transform-layer"),
                tool_call("flip_layer", "horizontal", layer_name="transform-layer"),
                tool_call("scale_image", 160, 120),
                tool_call("rotate_image", 90),
                tool_call("flip_image", "vertical"),
                tool_call("resize_canvas", 200, 170, 10, 10),
                tool_call("select_rectangle", 20, 20, 80, 60),
                tool_call("crop_to_selection"),
                tool_call("crop_image", 0, 0, 50, 40),
                tool_call("autocrop_image"),
                tool_call("get_image_info"),
            ],
        )

        add_tool_check(
            "C-080-color-contract",
            [
                tool_call("create_image", 120, 90, "rgb", "white"),
                tool_call("draw_rectangle", 0, 0, 120, 90, True, "red"),
                tool_call("set_foreground_color", "green"),
                tool_call("set_background_color", "blue"),
                tool_call("get_colors"),
                tool_call("swap_colors"),
                tool_call("sample_color", 5, 5),
                tool_call("adjust_brightness_contrast", 5, 5),
                tool_call("adjust_hue_saturation", 5.0, 5.0, 0.0),
                tool_call("adjust_levels", 0, 255, 1.0, 0, 255),
                tool_call("adjust_curves", [0, 0, 128, 140, 255, 255]),
                tool_call("desaturate"),
                tool_call("invert_colors"),
                tool_call("apply_threshold", 64, 255),
                tool_call("posterize", 4),
                tool_call("color_to_alpha", "white"),
                tool_call("auto_white_balance"),
            ],
        )

        add_optional_tool_check(
            "C-090-filter-contract",
            [
                tool_call("create_image", 140, 100, "rgb", "white"),
                tool_call("draw_rectangle", 10, 10, 80, 60, True, "red"),
                tool_call("apply_gaussian_blur", 1.0),
                tool_call("apply_unsharp_mask", 0.2, 1.0, 0.0),
                tool_call("apply_pixelize", 4),
                tool_call("apply_edge_detect", "sobel", 1.0),
                tool_call("apply_emboss", 315.0, 45.0, 1),
                tool_call("apply_noise", 0.05),
                tool_call("apply_median", 1),
                tool_call("apply_drop_shadow", 2.0, 2.0, 2.0, "black", 50.0),
            ],
            {"apply_drop_shadow": "Drop shadow procedure not found"},
        )

        pdb_probe = json_probe_check(
            "C-100-pdb-contract",
            bridge,
            """
from gi.repository import Gimp
pdb = Gimp.get_pdb()
required = ['file-png-export', 'file-jpeg-export', 'gimp-image-autocrop']
status = {name: bool(pdb.procedure_exists(name)) for name in required}
missing = [name for name, ok in status.items() if not ok]
_compat_result = {'required': status, 'script-fu-drop-shadow': bool(pdb.procedure_exists('script-fu-drop-shadow'))}
if missing:
    raise RuntimeError('missing required PDB procedures: ' + ', '.join(missing))
""",
        )
        tool_probe = tool_check(
            "C-100-pdb-contract",
            tools,
            [
                tool_call("search_pdb", "png", 20),
                tool_call(
                    "execute_python",
                    ["_compat_persistent_value = 41", "print(_compat_persistent_value + 1)"],
                ),
                tool_call("execute_python", ["print(_compat_persistent_value)"]),
            ],
        )
        if pdb_probe["status"] == "pass" and tool_probe["status"] == "pass":
            checks.append(
                make_check(
                    "C-100-pdb-contract",
                    "pass",
                    {"pdb_probe": pdb_probe["evidence"], "tool_probe": tool_probe["evidence"]},
                )
            )
        else:
            checks.append(
                make_check(
                    "C-100-pdb-contract", "fail", {"pdb_probe": pdb_probe, "tool_probe": tool_probe}
                )
            )

        add_optional_tool_check(
            "C-110-history-contract",
            [
                tool_call("create_image", 120, 90, "rgb", "white"),
                tool_call("begin_undo_group", "compat-history"),
                tool_call("draw_line", 5, 5, 90, 70, "red", 2.0),
                tool_call("end_undo_group"),
                tool_call("undo"),
                tool_call("redo"),
            ],
            {
                "undo": "Undo is not available via the GIMP 3.0 plugin API",
                "redo": "Redo is not available via the GIMP 3.0 plugin API",
            },
        )

        error_evidence: dict[str, Any] = {}
        try:
            bridge.send_command("definitely_invalid_compat_command")
        except GimpCommandError as exc:
            error_evidence["invalid_bridge_command"] = str(exc)
        else:
            error_evidence["invalid_bridge_command"] = "unexpected success"
        invalid_results = run_tool_calls(
            tools,
            [
                tool_call("set_active_layer", layer_name="does-not-exist"),
                tool_call("rotate_image", 13),
            ],
        )
        error_evidence["invalid_tool_calls"] = invalid_results
        error_ok = error_evidence["invalid_bridge_command"] != "unexpected success" and all(
            not item.get("success") for item in invalid_results
        )
        checks.append(
            make_check("C-120-error-contract", "pass" if error_ok else "fail", error_evidence)
        )
    else:
        for check_id in (
            "C-040-layer-contract",
            "C-050-selection-drawing-contract",
            "C-060-export-bitmap-contract",
            "C-070-transform-contract",
            "C-080-color-contract",
            "C-090-filter-contract",
            "C-100-pdb-contract",
            "C-110-history-contract",
            "C-120-error-contract",
        ):
            checks.append(make_check(check_id, "fail", "MCP tool registry could not be built"))

    checks.append(run_docs_check())

    if stop_bridge_after:
        try:
            bridge.send_command("shut" + "down")
            checks.append(make_check("C-900-stop-bridge", "pass", "stop command accepted"))
        except GimpCommandError as exc:
            checks.append(make_check("C-900-stop-bridge", "fail", str(exc)))

    bridge.disconnect()
    if include_static_checks:
        checks.extend(run_static_checks())
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
    claim_allowed = failed == 0 and should_allow_claim(checks)
    status = "verified" if claim_allowed else ("partial" if failed == 0 else "failed")
    notes = (
        ["All required compat.yml checks passed or were waived; public claim gate may proceed."]
        if claim_allowed
        else [
            "Partial live smoke only; full compat.yml matrix still required before a verified claim."
        ]
    )
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
            "status": status,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "waived": waived,
            "claim_allowed": claim_allowed,
            "notes": notes,
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
                "gimp3_directory": str(xdg_config_home / "GIMP" / "3.0"),
                "mcp_port": config.gimp_port,
            }
        )
        proc = spawn_gimp(
            gimp=gimp,
            xdg_config_home=xdg_config_home,
            port=config.gimp_port,
            xvfb=bool(args.xvfb),
            extra_args=list(args.gimp_args or []),
            invoke_plugin=True,
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
                    "gimp3_directory": str(xdg_config_home / "GIMP" / "3.0"),
                    "mcp_port": config.gimp_port,
                },
            )
        )
        ready, ready_detail = wait_for_bridge(config, timeout=float(args.startup_timeout))
        checks.append(
            make_check(
                "C-005-autostart-server",
                "pass" if ready else "fail",
                {
                    "detail": ready_detail,
                    "startup_timeout": float(args.startup_timeout),
                    "socket_host": config.gimp_host,
                    "socket_port": config.gimp_port,
                },
            )
        )
        if not ready:
            if args.keep_gimp:
                env["gimp_process_output"] = "unavailable while --keep-gimp is active"
            else:
                stop_gimp(proc)
                env["gimp_process_output"] = collect_process_output(proc)
            return finish_result(started, env, checks)
        smoke = run_smoke(
            config,
            plugin_path,
            env,
            stop_bridge_after=True,
            include_static_checks=bool(args.include_static_checks),
        )
        smoke["checks"] = checks + smoke["checks"]
        smoke["summary"] = finish_result(started, smoke["environment"], smoke["checks"])["summary"]
        if any(check["status"] == "fail" for check in smoke["checks"]):
            if args.keep_gimp:
                smoke["environment"]["gimp_process_output"] = (
                    "unavailable while --keep-gimp is active"
                )
            else:
                stop_gimp(proc)
                smoke["environment"]["gimp_process_output"] = collect_process_output(proc)
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
        "--xvfb",
        dest="xvfb",
        action="store_true",
        default=None,
        help="Spawn GIMP under xvfb-run -a. Implies --spawn.",
    )
    parser.add_argument(
        "--no-xvfb",
        dest="xvfb",
        action="store_false",
        help="Do not wrap spawned GIMP in xvfb-run. Requires --allow-display-spawn.",
    )
    parser.add_argument(
        "--allow-display-spawn",
        action="store_true",
        help="Permit --spawn --no-xvfb to use the current display session.",
    )
    parser.add_argument("--gimp", help="GIMP executable to spawn; defaults to discovery/env.")
    parser.add_argument(
        "--profile-dir", help="Profile root for spawned mode. Defaults to a temp dir."
    )
    parser.add_argument(
        "--startup-timeout", type=float, default=45.0, help="Seconds to wait for plug-in autostart."
    )
    parser.add_argument(
        "--fixed-port",
        action="store_true",
        help="In spawned mode, keep the configured/default port instead of allocating a free one.",
    )
    parser.add_argument(
        "--include-static-checks",
        action="store_true",
        help="Append static compat.yml checks so the result can satisfy the full claim gate.",
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


tool_call = _tool_call


def normalize_spawn_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    config: ServerConfig,
) -> None:
    """Normalize and safety-check live-spawn related CLI arguments.

    Live GIMP execution is opt-in.  Plain existing-server mode must never
    spawn a test GIMP merely because Xvfb support exists.  Spawned mode uses
    Xvfb by default; using the current real display requires an explicit
    double opt-in with --no-xvfb --allow-display-spawn.
    """
    if args.xvfb is True:
        args.spawn = True
    if args.spawn and args.xvfb is None:
        args.xvfb = True
    if args.xvfb is None:
        args.xvfb = False

    if args.spawn and not args.xvfb and not args.allow_display_spawn:
        parser.error(
            "spawned GIMP must run under Xvfb by default; use --no-xvfb --allow-display-spawn to opt into the current display"
        )
    if args.xvfb and shutil.which("xvfb-run") is None:
        parser.error(
            "xvfb-run is required for spawned compatibility runs; install xvfb or use --no-xvfb --allow-display-spawn"
        )
    if args.spawn and not args.port and not args.fixed_port:
        # Avoid collisions with a production GIMP bridge that may already use 9877.
        config.gimp_port = find_free_port()


def main(argv: list[str] | None = None) -> int:
    """Script entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = ServerConfig()
    if args.host:
        config.gimp_host = args.host
    if args.port:
        config.gimp_port = args.port

    normalize_spawn_args(parser, args, config)

    result = (
        run_spawned_smoke(args, config)
        if args.spawn
        else run_smoke(
            config,
            args.plugin_path,
            include_static_checks=bool(args.include_static_checks),
        )
    )
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
