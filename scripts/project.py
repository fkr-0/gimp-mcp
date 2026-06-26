#!/usr/bin/env python3
"""Project maintenance commands backed by uv.

This script keeps common local workflows discoverable and reproducible.  It is
intentionally small: every command shells out to uv so there is one dependency
resolver and one virtual environment source of truth.
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence

Command = list[str]

COMMANDS: dict[str, Command] = {
    "sync": ["uv", "sync", "--extra", "dev"],
    "test": ["uv", "run", "pytest"],
    "test-fast": ["uv", "run", "pytest", "--no-cov"],
    "test-cov": [
        "uv",
        "run",
        "pytest",
        "--cov-report=html",
        "--cov-report=term-missing:skip-covered",
    ],
    "lint": ["uv", "run", "ruff", "check", "."],
    "lint-fix": ["uv", "run", "ruff", "check", "--fix", "."],
    "format": ["uv", "run", "ruff", "format", "."],
    "format-check": ["uv", "run", "ruff", "format", "--check", "."],
    "typecheck": ["uv", "run", "mypy"],
    "doctor": ["uv", "run", "gimp-mcp-pro", "doctor"],
    "config": ["uv", "run", "gimp-mcp-pro", "config", "--json"],
    "docs-generate": ["uv", "run", "python", "scripts/docs.py", "generate"],
    "docs-audit": ["uv", "run", "python", "scripts/docs.py", "audit"],
    "docs-build": ["uv", "run", "--extra", "dev", "mkdocs", "build", "--strict"],
    "docs-pdf": [
        "uv",
        "run",
        "python",
        "scripts/build_docs_pdf.py",
        "--output",
        "dist/gimp-mcp-pro-docs.pdf",
    ],
    "docs-serve": ["uv", "run", "--extra", "dev", "mkdocs", "serve"],
    "install-plugin": ["uv", "run", "python", "scripts/install_gimp_plugin.py"],
    "compat-list-tools": ["uv", "run", "python", "scripts/compat.py", "list-tools", "--grouped"],
    "compat-validate": ["uv", "run", "python", "scripts/compat.py", "validate"],
    "compat-audit": ["uv", "run", "python", "scripts/compat.py", "audit"],
    "compat-validate-results": [
        "uv",
        "run",
        "python",
        "scripts/compat.py",
        "validate-results",
        "compat.results.yml",
    ],
    "compat-template": [
        "uv",
        "run",
        "python",
        "scripts/compat.py",
        "init-results",
        "--output",
        "compat.results.template.yml",
        "--force",
    ],
    "compat-live-smoke": [
        "uv",
        "run",
        "python",
        "tests/live_gimp_324_smoke.py",
        "--output",
        "compat.results.yml",
    ],
    "compat-live-spawn": [
        "uv",
        "run",
        "python",
        "tests/live_gimp_324_smoke.py",
        "--spawn",
        "--xvfb",
        "--output",
        "compat.results.yml",
    ],
    "compat-live-xvfb": [
        "uv",
        "run",
        "python",
        "tests/live_gimp_324_smoke.py",
        "--spawn",
        "--xvfb",
        "--output",
        "compat.results.yml",
    ],
    "async-repl": ["uv", "run", "gimp-mcp-pro", "async-repl"],
    "build-dist": ["uv", "build", "--sdist", "--wheel"],
}

CHECK_COMMANDS = ("docs-audit", "format-check", "lint", "typecheck", "test")


def run_command(command: Command) -> int:
    """Run one command and return its exit code."""
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, check=False).returncode


def cmd_run(args: argparse.Namespace) -> int:
    """Run a single named project command."""
    return run_command(COMMANDS[args.name])


def cmd_check(_: argparse.Namespace) -> int:
    """Run the standard quality gate."""
    for name in CHECK_COMMANDS:
        code = run_command(COMMANDS[name])
        if code != 0:
            return code
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the maintenance CLI parser."""
    parser = argparse.ArgumentParser(description="Run uv-backed project maintenance commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run one named command.")
    run.add_argument("name", choices=sorted(COMMANDS))
    run.set_defaults(func=cmd_run)

    check = subparsers.add_parser(
        "check", help="Run docs-audit, format-check, lint, typecheck, and tests."
    )
    check.set_defaults(func=cmd_check)

    list_cmd = subparsers.add_parser("list", help="List available commands.")
    list_cmd.set_defaults(func=lambda _args: print("\n".join(sorted(COMMANDS))) or 0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Script entry point."""
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
