"""Tests for the public CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gimp_mcp_pro.cli import main


def test_config_command_prints_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIMP_MCP_PRO_HOST", "cli.local")
    monkeypatch.setenv("GIMP_MCP_PRO_PORT", "9991")

    status = main(["config", "--json"])

    captured = capsys.readouterr()
    assert status == 0
    payload = json.loads(captured.out)
    assert payload["gimp_host"] == "cli.local"
    assert payload["gimp_port"] == 9991


def test_config_command_accepts_cli_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    status = main(["config", "--json", "--host", "override.local", "--port", "9900"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 0
    assert payload["gimp_host"] == "override.local"
    assert payload["gimp_port"] == 9900


def test_doctor_skips_connectivity_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    status = main(["doctor"])

    captured = capsys.readouterr()
    assert status == 0
    assert "connectivity=skipped" in captured.out


def test_invalid_config_returns_error_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIMP_MCP_PRO_PORT", "999999")

    status = main(["config"])

    captured = capsys.readouterr()
    assert status == 2
    assert "GIMP_MCP_PRO_PORT" in captured.err


def test_config_command_prints_key_value_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Non-JSON config output remains shell-friendly."""
    monkeypatch.chdir(tmp_path)

    status = main(["config", "--host", "kv.local", "--port", "9902"])

    captured = capsys.readouterr()
    assert status == 0
    assert "gimp_host=kv.local" in captured.out
    assert "gimp_port=9902" in captured.out


def test_doctor_connectivity_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Doctor --connect reports success and disconnects the bridge."""
    monkeypatch.chdir(tmp_path)
    events: list[str] = []

    class FakeBridge:
        def __init__(self, **kwargs: object) -> None:
            events.append(f"init:{kwargs['host']}:{kwargs['port']}")

        def connect(self) -> None:
            events.append("connect")

        def disconnect(self) -> None:
            events.append("disconnect")

    monkeypatch.setattr("gimp_mcp_pro.cli.GimpBridge", FakeBridge)

    status = main(["doctor", "--connect", "--host", "doctor.local", "--port", "9903"])

    captured = capsys.readouterr()
    assert status == 0
    assert "connectivity=ok" in captured.out
    assert events == ["init:doctor.local:9903", "connect", "disconnect"]


def test_doctor_connectivity_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Doctor --connect maps bridge failures to a diagnostic exit status."""
    from gimp_mcp_pro.utils.errors import GimpConnectionError

    monkeypatch.chdir(tmp_path)
    events: list[str] = []

    class FakeBridge:
        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def connect(self) -> None:
            events.append("connect")
            raise GimpConnectionError("refused")

        def disconnect(self) -> None:
            events.append("disconnect")

    monkeypatch.setattr("gimp_mcp_pro.cli.GimpBridge", FakeBridge)

    status = main(["doctor", "--connect"])

    captured = capsys.readouterr()
    assert status == 2
    assert "connectivity=failed: refused" in captured.err
    assert events == ["connect", "disconnect"]


def test_serve_invokes_created_mcp_server(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """serve delegates to create_server(config).run()."""
    monkeypatch.chdir(tmp_path)
    events: list[str] = []

    class FakeMCP:
        def run(self) -> None:
            events.append("run")

    def fake_create_server(config: object) -> FakeMCP:
        assert config is not None
        events.append("create")
        return FakeMCP()

    monkeypatch.setattr("gimp_mcp_pro.server.create_server", fake_create_server)

    status = main(["serve"])

    assert status == 0
    assert events == ["create", "run"]


def test_repl_handles_metadata_context_json_python_and_quit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The sync REPL routes line-oriented commands through the bridge."""
    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    inputs = iter(
        [
            ":metadata",
            ":context",
            '{"type": "custom", "params": {"x": 1}}',
            "print('hello')",
            ":quit",
        ]
    )

    class FakeBridge:
        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def connect(self) -> None:
            events.append("connect")

        def disconnect(self) -> None:
            events.append("disconnect")

        def get_image_metadata(self) -> dict[str, object]:
            events.append("metadata")
            return {"status": "success", "results": {"width": 1}}

        def get_context_state(self) -> dict[str, object]:
            events.append("context")
            return {"status": "success", "results": {"foreground": "#000000"}}

        def send_command(self, command: str, params: dict[str, object]) -> dict[str, object]:
            events.append(f"send:{command}:{params['x']}")
            return {"status": "success", "results": params}

        def execute_python(self, code: list[str]) -> dict[str, object]:
            events.append(f"exec:{code[0]}")
            return {"status": "success", "results": ["hello"]}

    monkeypatch.setattr("gimp_mcp_pro.cli.GimpBridge", FakeBridge)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    status = main(["repl"])

    captured = capsys.readouterr()
    assert status == 0
    assert "Connected. Type :quit to exit." in captured.out
    assert events == [
        "connect",
        "metadata",
        "context",
        "send:custom:1",
        "exec:print('hello')",
        "disconnect",
    ]


def test_repl_reports_line_errors_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Malformed REPL JSON is reported without tearing down the session."""
    monkeypatch.chdir(tmp_path)
    inputs = iter(["{bad", ":exit"])

    class FakeBridge:
        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def connect(self) -> None:
            pass

        def disconnect(self) -> None:
            pass

    monkeypatch.setattr("gimp_mcp_pro.cli.GimpBridge", FakeBridge)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    status = main(["repl"])

    captured = capsys.readouterr()
    assert status == 0
    assert "error:" in captured.err
