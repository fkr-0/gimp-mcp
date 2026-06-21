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
