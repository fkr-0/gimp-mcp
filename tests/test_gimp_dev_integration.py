"""Tests for the optional gimp.dev integration adapter and MCP tools."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from gimp_mcp_pro.config import ServerConfig
from gimp_mcp_pro.gimp_dev_integration import (
    GimpDevAdapter,
    GimpDevCommandError,
    GimpDevJSONError,
    GimpDevUnavailableError,
)
from gimp_mcp_pro.tools.gimp_dev_tools import register_gimp_dev_tools


class CaptureMCP:
    """Tiny FastMCP-compatible registrar for tool tests."""

    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        """Return a decorator that records one tool function."""
        del args, kwargs

        def decorator(fn):  # type: ignore[no-untyped-def]
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def make_project_root(tmp_path: Path) -> Path:
    """Create a minimal gimp.dev-like project root."""
    root = tmp_path / "gimp.dev"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'gimp-dev'\n")
    return root


def completed(
    stdout: str, *, returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    """Build a text-mode CompletedProcess fixture."""
    return subprocess.CompletedProcess(
        args=["uv"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_adapter_status_reports_unavailable_without_project(tmp_path: Path) -> None:
    """Missing gimp.dev checkouts are reported without running subprocesses."""
    adapter = GimpDevAdapter(root=tmp_path / "missing")

    status = adapter.status()

    assert status["enabled"] is True
    assert status["available"] is False
    assert status["root_exists"] is False
    assert "plugin-catalog" in status["safe_commands"]
    assert "start" in status["unsafe_commands"]


def test_adapter_from_config_uses_gimp_dev_settings(tmp_path: Path) -> None:
    """ServerConfig controls the optional gimp.dev adapter."""
    config = ServerConfig(
        gimp_dev_enabled=False,
        gimp_dev_root=tmp_path,
        gimp_dev_cli="custom-gimp-dev",
        gimp_dev_uv="uvx",
        gimp_dev_timeout=3.5,
    )

    adapter = GimpDevAdapter.from_config(config)

    assert adapter.enabled is False
    assert adapter.root == tmp_path
    assert adapter.cli == "custom-gimp-dev"
    assert adapter.uv == "uvx"
    assert adapter.timeout == 3.5


def test_run_json_rejects_unsafe_command(tmp_path: Path) -> None:
    """Only the explicit pure/read-only command allowlist can run."""
    adapter = GimpDevAdapter(root=make_project_root(tmp_path))

    with pytest.raises(GimpDevCommandError, match="not allowlisted"):
        adapter.run_json(["start"])


def test_run_json_requires_available_project(tmp_path: Path) -> None:
    """Unavailable checkouts fail before subprocess invocation."""
    adapter = GimpDevAdapter(root=tmp_path / "missing")

    with pytest.raises(GimpDevUnavailableError):
        adapter.run_json(["plugin-catalog"])


def test_run_json_parses_subprocess_json(tmp_path: Path) -> None:
    """Safe gimp.dev commands are executed from the configured checkout root."""
    root = make_project_root(tmp_path)
    calls: list[tuple[list[str], Path, float]] = []

    def runner(argv: Sequence[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
        calls.append((list(argv), cwd, timeout))
        return completed('{"plugins": [], "validation_errors": []}')

    adapter = GimpDevAdapter(root=root, timeout=2.0, runner=runner)

    payload = adapter.run_json(["plugin-catalog", "--check"])

    assert payload == {"plugins": [], "validation_errors": []}
    assert calls == [(["uv", "run", "gimp-dev", "plugin-catalog", "--check"], root, 2.0)]


def test_run_json_reports_subprocess_and_json_errors(tmp_path: Path) -> None:
    """Command failures and malformed stdout become typed adapter errors."""
    root = make_project_root(tmp_path)
    adapter = GimpDevAdapter(
        root=root,
        runner=lambda _argv, _cwd, _timeout: completed("", returncode=2, stderr="bad"),
    )

    with pytest.raises(GimpDevCommandError, match="exit 2"):
        adapter.run_json(["plugin-catalog"])

    adapter = GimpDevAdapter(root=root, runner=lambda _argv, _cwd, _timeout: completed("not json"))
    with pytest.raises(GimpDevJSONError):
        adapter.run_json(["plugin-catalog"])

    adapter = GimpDevAdapter(root=root, runner=lambda _argv, _cwd, _timeout: completed("[]"))
    with pytest.raises(GimpDevJSONError, match="not an object"):
        adapter.run_json(["plugin-catalog"])


def test_catalog_summary_marks_special_policy_procedures(tmp_path: Path) -> None:
    """Catalog summaries preserve compact safety notes for later adapters."""
    adapter = GimpDevAdapter(root=make_project_root(tmp_path))
    catalog = {
        "plugins": [
            {
                "name": "async-repl",
                "validation_errors": [],
                "procedures": [
                    {"name": "python-fu-repl-start", "detail": "Starts a ptpython session"}
                ],
            },
            {
                "name": "sprite-tools",
                "validation_errors": ["plugin warning"],
                "procedures": [
                    {
                        "name": "python-fu-gimp-dev-sprite-background-remove",
                        "handler": "run_background_remove",
                        "commands": ["sprite.bg.remove"],
                        "arguments": [{"name": "red"}],
                    }
                ],
            },
        ],
        "validation_errors": ["root warning"],
    }

    summary = adapter.summarize_catalog(catalog)
    data = summary.as_dict()

    assert summary.plugin_count == 2
    assert summary.procedure_count == 2
    assert data["validation_errors"] == ["root warning", "plugin warning"]
    notes = {procedure["name"]: procedure["safety_note"] for procedure in data["procedures"]}
    assert notes["python-fu-repl-start"] == "developer-repl-manual-session-only"
    assert (
        notes["python-fu-gimp-dev-sprite-background-remove"]
        == "live-mutating-procedure-requires-transaction"
    )


@pytest.mark.asyncio
async def test_mcp_gimp_dev_tools_return_status_and_catalog(tmp_path: Path) -> None:
    """Read-only gimp.dev tools expose status and compact catalog data."""
    root = make_project_root(tmp_path)
    catalog = {
        "plugins": [
            {
                "name": "sprite-tools",
                "validation_errors": [],
                "procedures": [
                    {
                        "name": "python-fu-gimp-dev-sprite-sheet-plan",
                        "handler": "run_sheet_plan",
                        "commands": ["sprite.sheet.detect"],
                        "arguments": [{"name": "columns"}],
                    }
                ],
            }
        ],
        "validation_errors": [],
    }
    adapter = GimpDevAdapter(
        root=root, runner=lambda _argv, _cwd, _timeout: completed(json.dumps(catalog))
    )
    mcp = CaptureMCP()
    register_gimp_dev_tools(mcp, adapter=adapter)

    status = await mcp.tools["gimp_dev_status"]()  # type: ignore[operator]
    result = await mcp.tools["gimp_dev_plugin_catalog"](include_raw_catalog=True)  # type: ignore[operator]

    assert status["success"] is True
    assert result["success"] is True
    assert result["data"]["plugin_count"] == 1
    assert result["data"]["procedure_count"] == 1
    assert result["data"]["raw_catalog"] == catalog


@pytest.mark.asyncio
async def test_mcp_gimp_dev_catalog_handles_unavailable_project(tmp_path: Path) -> None:
    """Catalog tool returns structured failure when gimp.dev is absent."""
    adapter = GimpDevAdapter(root=tmp_path / "missing")
    mcp = CaptureMCP()
    register_gimp_dev_tools(mcp, adapter=adapter)

    result = await mcp.tools["gimp_dev_plugin_catalog"]()  # type: ignore[operator]

    assert result["success"] is False
    assert result["operation"] == "gimp_dev_plugin_catalog"
    assert result["data"]["available"] is False
