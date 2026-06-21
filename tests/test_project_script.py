"""Tests for the uv-backed project helper script."""

from __future__ import annotations

import pytest

import scripts.project as project


def test_project_script_lists_commands(capsys: pytest.CaptureFixture[str]) -> None:
    status = project.main(["list"])

    captured = capsys.readouterr()
    assert status == 0
    assert "format" in captured.out
    assert "test-cov" in captured.out
    assert "compat-live-spawn" in captured.out
    assert "compat-live-xvfb" in captured.out
    assert "compat-validate" in captured.out
    assert "docs-generate" in captured.out
    assert "docs-build" in captured.out


def test_project_script_exposes_quality_gate() -> None:
    assert project.CHECK_COMMANDS == ("docs-audit", "format-check", "lint", "typecheck", "test")
    for name in project.CHECK_COMMANDS:
        assert name in project.COMMANDS


def test_project_script_exposes_compat_commands() -> None:
    assert "compat-list-tools" in project.COMMANDS
    assert "compat-validate" in project.COMMANDS
    assert "compat-audit" in project.COMMANDS
    assert "compat-validate-results" in project.COMMANDS
    assert "compat-template" in project.COMMANDS


def test_project_script_exposes_docs_commands() -> None:
    assert "docs-generate" in project.COMMANDS
    assert "docs-audit" in project.COMMANDS
    assert "docs-build" in project.COMMANDS
    assert "--extra" in project.COMMANDS["docs-build"]
    assert "dev" in project.COMMANDS["docs-build"]
