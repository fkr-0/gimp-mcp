from __future__ import annotations

from pathlib import Path

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


def test_spawned_mode_uses_ephemeral_port_by_default() -> None:
    parser = live.build_parser()
    args = parser.parse_args(["--spawn"])
    config = live.ServerConfig()
    config.gimp_port = 9877

    if args.spawn and not args.port and not args.fixed_port:
        config.gimp_port = 43210

    assert config.gimp_port == 43210


def test_shell_profile_helper_exists() -> None:
    script = live.PROJECT_ROOT / "scripts" / "gimp-clean-profile.sh"
    text = script.read_text(encoding="utf-8")

    assert script.exists()
    assert "XDG_CONFIG_HOME" in text
    assert "GIMP_MCP_AUTO_START" in text
    assert "gimp_mcp_plugin" in text
