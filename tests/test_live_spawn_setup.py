from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from gimp_mcp_pro.config import ServerConfig
from tests import live_gimp_324_smoke as live


def test_install_plugin_to_clean_xdg_profile(tmp_path: Path) -> None:
    source = tmp_path / "gimp_mcp_plugin.py"
    source.write_text("#!/usr/bin/env python3\nprint('plugin')\n", encoding="utf-8")

    target = live.install_plugin_to_profile(tmp_path / "config", source=source)

    assert target.name == "gimp_mcp_plugin.py"
    assert target.parent.name == "gimp_mcp_plugin"
    assert target.stat().st_mode & 0o111


def test_spawn_environment_is_clean_profile_and_runs_plugin_procedure(tmp_path: Path) -> None:
    repo_venv = live.PROJECT_ROOT / ".venv" / "bin"
    env = live.build_spawn_env(
        xdg_config_home=tmp_path / "config",
        port=12345,
        base={
            "PATH": f"{repo_venv}:/usr/bin",
            "VIRTUAL_ENV": "/tmp/venv",
            "PYTHONHOME": "/tmp/py",
        },
    )

    assert env["XDG_CONFIG_HOME"] == str(tmp_path / "config")
    assert env["GIMP_MCP_PORT"] == "12345"
    assert env["GIMP_MCP_AUTO_START"] == "0"
    assert env["GIMP_MCP_BLOCKING_AUTOSTART"] == "0"
    assert env["GIMP_MCP_BLOCKING_RUN"] == "1"
    assert env["GIMP3_DIRECTORY"] == str(tmp_path / "config" / "GIMP" / "3.0")
    assert "VIRTUAL_ENV" not in env
    assert "PYTHONHOME" not in env
    assert str(repo_venv) not in env["PATH"]


def test_spawn_command_can_wrap_gimp_in_xvfb() -> None:
    command = live.build_spawn_command(gimp="gimp-3.2", xvfb=False)
    assert command[:4] == [
        "gimp-3.2",
        "--new-instance",
        "--no-splash",
        "--console-messages",
    ]
    assert "--batch-interpreter=python-fu-eval" in command
    assert any("plug-in-mcp-pro-server" in part for part in command)
    assert live.build_spawn_command(gimp="gimp-3.2", xvfb=True)[:3] == [
        "xvfb-run",
        "-a",
        "gimp-3.2",
    ]


def test_plugin_server_autostart_is_static_registered() -> None:
    source = live.PLUGIN_SOURCE.read_text(encoding="utf-8")

    assert "def do_init_procedures" in source
    assert "GIMP_MCP_AUTO_START" in source
    assert "_start_server_thread" in source
    assert "self._server_loop" in source
    assert "def do_quit" in source


def test_bitmap_export_uses_gimp_3_2_image_flatten_api() -> None:
    source = live.PLUGIN_SOURCE.read_text(encoding="utf-8")

    assert ".flatten_image()" not in source
    assert ".flatten()" in source


def test_existing_server_mode_does_not_spawn_by_default() -> None:
    parser = live.build_parser()
    args = parser.parse_args([])
    config = live.ServerConfig()
    config.gimp_port = 9877

    live.normalize_spawn_args(parser, args, config)

    assert args.spawn is False
    assert args.xvfb is False
    assert config.gimp_port == 9877


def test_spawned_mode_uses_xvfb_and_ephemeral_port_by_default(monkeypatch: Any) -> None:
    parser = live.build_parser()
    args = parser.parse_args(["--spawn"])
    config = live.ServerConfig()
    config.gimp_port = 9877
    monkeypatch.setattr(live.shutil, "which", lambda _name: "/usr/bin/xvfb-run")
    monkeypatch.setattr(live, "find_free_port", lambda: 43210)

    live.normalize_spawn_args(parser, args, config)

    assert args.xvfb is True
    assert args.allow_display_spawn is False
    assert config.gimp_port == 43210


def test_xvfb_flag_implies_spawn(monkeypatch: Any) -> None:
    parser = live.build_parser()
    args = parser.parse_args(["--xvfb"])
    config = live.ServerConfig()
    monkeypatch.setattr(live.shutil, "which", lambda _name: "/usr/bin/xvfb-run")

    live.normalize_spawn_args(parser, args, config)

    assert args.spawn is True
    assert args.xvfb is True


def test_spawned_mode_requires_explicit_display_opt_in(monkeypatch: Any) -> None:
    parser = live.build_parser()
    args = parser.parse_args(["--spawn", "--no-xvfb"])
    config = live.ServerConfig()

    assert args.xvfb is False
    assert args.allow_display_spawn is False
    try:
        live.normalize_spawn_args(parser, args, config)
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected display-spawn safety parser error")

    allowed_args = parser.parse_args(["--spawn", "--no-xvfb", "--allow-display-spawn"])
    monkeypatch.setattr(live, "find_free_port", lambda: 43210)
    live.normalize_spawn_args(parser, allowed_args, config)

    assert allowed_args.xvfb is False
    assert allowed_args.allow_display_spawn is True


def test_shell_profile_helper_exists() -> None:
    script = live.PROJECT_ROOT / "scripts" / "gimp-clean-profile.sh"
    text = script.read_text(encoding="utf-8")

    assert script.exists()
    assert "XDG_CONFIG_HOME" in text
    assert "GIMP_MCP_AUTO_START" in text
    assert "gimp_mcp_plugin" in text


def test_static_checks_do_not_duplicate_live_docs_contract(
    monkeypatch: Any,
) -> None:
    """Static checks should emit S-* records only for documentation claim state."""

    def fake_run(
        command: list[str],
        cwd: Path,
        text: bool,
        stdout: Any,
        stderr: Any,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="ok\n")

    monkeypatch.setattr(live.subprocess, "run", fake_run)
    monkeypatch.setattr(
        live,
        "run_docs_check",
        lambda: live.make_check("C-130-docs-contract", "pass", {"docs": "ok"}),
    )

    checks = live.run_static_checks()
    ids = [check["id"] for check in checks]

    assert "S-040-doc-claim-gate" in ids
    assert "C-130-docs-contract" not in ids
    assert len(ids) == len(set(ids))


def test_spawned_smoke_records_autostart_failure_without_full_matrix(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """A spawned GIMP that never opens the socket should produce concise evidence."""

    class FakeProcess:
        pid = 1234
        stdout = None

        def poll(self) -> int | None:
            return None

    parser = live.build_parser()
    args = parser.parse_args(
        ["--spawn", "--profile-dir", str(tmp_path), "--startup-timeout", "0.01"]
    )
    config = ServerConfig(gimp_host="127.0.0.1", gimp_port=43210, reconnect_delays=())

    def discover_gimp_stub(_explicit: str | None = None) -> str:
        return "gimp-3.2"

    def spawn_gimp_stub(**_kwargs: Any) -> FakeProcess:
        return FakeProcess()

    def stop_gimp_stub(_proc: FakeProcess) -> None:
        return None

    def collect_process_output_stub(_proc: FakeProcess) -> str:
        return "gimp output tail"

    def wait_for_bridge_stub(_config: ServerConfig, *, timeout: float) -> tuple[bool, str]:
        assert timeout == 0.01
        return False, "connection refused"

    monkeypatch.setattr(live, "discover_gimp", discover_gimp_stub)
    monkeypatch.setattr(live, "spawn_gimp", spawn_gimp_stub)
    monkeypatch.setattr(live, "stop_gimp", stop_gimp_stub)
    monkeypatch.setattr(live, "collect_process_output", collect_process_output_stub)
    monkeypatch.setattr(live, "wait_for_bridge", wait_for_bridge_stub)

    result = live.run_spawned_smoke(args, config)
    ids = [check["id"] for check in result["checks"]]
    by_id = {check["id"]: check for check in result["checks"]}

    assert ids == ["C-000-spawn-gimp", "C-005-autostart-server"]
    assert len(ids) == len(set(ids))
    assert by_id["C-000-spawn-gimp"]["status"] == "pass"
    assert by_id["C-005-autostart-server"]["status"] == "fail"
    assert by_id["C-005-autostart-server"]["evidence"]["detail"] == "connection refused"
    assert result["summary"]["claim_allowed"] is False
    assert result["environment"]["gimp_process_output"] == "gimp output tail"


def test_existing_server_mode_controls_static_checks(
    monkeypatch: Any,
) -> None:
    """Existing-server mode should not append static checks unless requested."""

    class FakeBridge:
        def __init__(self, **kwargs: Any) -> None:
            self.long_timeout = 1.0

        def connect(self) -> None:
            return None

        def send_command(
            self, command: str, params: Any = None, timeout: float | None = None
        ) -> dict[str, Any]:
            return {"status": "success", "results": {"command": command}}

        def disconnect(self) -> None:
            return None

    monkeypatch.setattr(live, "GimpBridge", FakeBridge)

    def transport_check_stub(
        _bridge: FakeBridge, _config: ServerConfig, _info: dict[str, Any]
    ) -> dict[str, Any]:
        return live.make_check("C-020-transport", "pass", {})

    def env_introspection_check_stub(_bridge: FakeBridge, _env: dict[str, Any]) -> dict[str, Any]:
        return live.make_check("C-001-env-introspection", "pass", {})

    def plugin_registration_check_stub(_bridge: FakeBridge) -> dict[str, Any]:
        return live.make_check("C-010-plugin-registration", "pass", {})

    def build_registered_tools_stub(_bridge: FakeBridge) -> dict[str, Any]:
        return {}

    monkeypatch.setattr(live, "_transport_check", transport_check_stub)
    monkeypatch.setattr(live, "_env_introspection_check", env_introspection_check_stub)
    monkeypatch.setattr(live, "_plugin_registration_check", plugin_registration_check_stub)
    monkeypatch.setattr(live, "build_registered_tools", build_registered_tools_stub)
    monkeypatch.setattr(
        live, "run_docs_check", lambda: live.make_check("C-130-docs-contract", "pass", {})
    )
    monkeypatch.setattr(
        live, "run_static_checks", lambda: [live.make_check("S-001-yaml-validity", "pass", {})]
    )

    smoke_only = live.run_smoke(ServerConfig(reconnect_delays=()), include_static_checks=False)
    full = live.run_smoke(ServerConfig(reconnect_delays=()), include_static_checks=True)

    assert "S-001-yaml-validity" not in [check["id"] for check in smoke_only["checks"]]
    assert "S-001-yaml-validity" in [check["id"] for check in full["checks"]]


def test_optional_tool_failures_are_accepted_only_when_expected() -> None:
    """Known optional capability failures should not fail transport smoke."""
    check = live.make_check(
        "C-090-filter-contract",
        "fail",
        {
            "calls": [
                {"tool": "apply_gaussian_blur", "success": True, "result": {"success": True}},
                {
                    "tool": "apply_drop_shadow",
                    "success": False,
                    "result": {"success": False, "error": "Drop shadow procedure not found"},
                },
            ],
            "failed_tools": ["apply_drop_shadow"],
        },
    )

    normalized = live.accept_optional_tool_failures(
        check, optional_errors={"apply_drop_shadow": "Drop shadow procedure not found"}
    )

    assert normalized["status"] == "pass"
    assert normalized["evidence"]["failed_tools"] == []
    assert normalized["evidence"]["accepted_optional_failures"][0]["tool"] == "apply_drop_shadow"


def test_structured_optional_tool_failure_is_accepted_without_string_policy() -> None:
    """Machine-readable optional-capability results should drive smoke normalization."""
    check = live.make_check(
        "C-110-history-contract",
        "fail",
        {
            "calls": [
                {
                    "tool": "undo",
                    "success": False,
                    "result": {
                        "success": False,
                        "operation": "undo",
                        "error": "localized or changed wording",
                        "data": {
                            "error_code": "optional_capability_unavailable",
                            "optional_capability": True,
                            "capability": "programmatic image undo",
                            "procedure": "gimp-image-undo",
                        },
                    },
                }
            ],
            "failed_tools": ["undo"],
        },
    )

    normalized = live.accept_optional_tool_failures(check, optional_errors={})

    assert normalized["status"] == "pass"
    assert normalized["evidence"]["failed_tools"] == []
    accepted = normalized["evidence"]["accepted_optional_failures"][0]
    assert accepted["tool"] == "undo"
    assert accepted["procedure"] == "gimp-image-undo"
    assert accepted["capability"] == "programmatic image undo"


def test_unexpected_tool_failures_still_fail() -> None:
    """Optional normalization must not hide unrelated tool failures."""
    check = live.make_check(
        "C-090-filter-contract",
        "fail",
        {
            "calls": [
                {
                    "tool": "apply_gaussian_blur",
                    "success": False,
                    "result": {"success": False, "error": "unexpected blur failure"},
                }
            ],
            "failed_tools": ["apply_gaussian_blur"],
        },
    )

    normalized = live.accept_optional_tool_failures(
        check, optional_errors={"apply_drop_shadow": "Drop shadow procedure not found"}
    )

    assert normalized["status"] == "fail"
    assert normalized["evidence"]["failed_tools"] == ["apply_gaussian_blur"]
    assert normalized["evidence"]["rejected_failures"][0]["tool"] == "apply_gaussian_blur"
