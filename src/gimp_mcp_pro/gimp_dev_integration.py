"""Optional adapter for the local ``gimp.dev`` helper project.

The adapter treats ``gimp.dev`` as an external capability provider. It shells out
to the ``gimp-dev`` CLI for pure JSON metadata and does not import GIMP-facing
plug-in internals into the MCP server process.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CompletedTextProcess = subprocess.CompletedProcess[str]
Runner = Callable[[Sequence[str], Path, float], CompletedTextProcess]

SAFE_GIMP_DEV_COMMANDS: tuple[str, ...] = (
    "doctor",
    "env",
    "command",
    "plugin-list",
    "plugin-catalog",
    "gtk-frame-plan",
    "sprite-sheet-plan",
    "sprite-onion-plan",
    "sprite-clip-plan",
)
"""Pure/read-only or planning commands that do not mutate the GIMP profile."""

UNSAFE_GIMP_DEV_COMMANDS: tuple[str, ...] = (
    "start",
    "plugin-install",
    "plugin-uninstall",
)
"""Commands that start a GUI session or mutate the user's GIMP profile."""

DEFAULT_GIMP_DEV_ROOT = Path.home() / "code" / "gimp.dev"
"""Default local checkout path used by Flo's workspace."""


class GimpDevIntegrationError(RuntimeError):
    """Base error for optional ``gimp.dev`` integration failures."""


class GimpDevUnavailableError(GimpDevIntegrationError):
    """Raised when the configured ``gimp.dev`` checkout is not usable."""


class GimpDevCommandError(GimpDevIntegrationError):
    """Raised when a ``gimp-dev`` subprocess returns a non-zero status."""


class GimpDevJSONError(GimpDevIntegrationError):
    """Raised when a ``gimp-dev`` command does not return a JSON object."""


@dataclass(frozen=True)
class GimpDevProcedureRef:
    """Compact procedure reference derived from a ``gimp.dev`` catalog."""

    plugin: str
    name: str
    handler: str | None = None
    command_names: tuple[str, ...] = ()
    argument_count: int = 0
    safety_note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable procedure reference."""
        return {
            "plugin": self.plugin,
            "name": self.name,
            "handler": self.handler,
            "commands": list(self.command_names),
            "argument_count": self.argument_count,
            "safety_note": self.safety_note,
        }


@dataclass(frozen=True)
class GimpDevCatalogSummary:
    """Summarized shape of a ``gimp.dev`` plug-in catalog."""

    plugin_count: int
    procedure_count: int
    validation_errors: tuple[str, ...]
    procedures: tuple[GimpDevProcedureRef, ...] = ()

    def as_dict(self, *, include_procedures: bool = True) -> dict[str, Any]:
        """Return a JSON-serializable summary.

        Args:
            include_procedures: Include individual compact procedure references.

        Returns:
            Dictionary suitable for MCP tool result data.
        """
        data: dict[str, Any] = {
            "plugin_count": self.plugin_count,
            "procedure_count": self.procedure_count,
            "validation_errors": list(self.validation_errors),
        }
        if include_procedures:
            data["procedures"] = [procedure.as_dict() for procedure in self.procedures]
        return data


@dataclass
class GimpDevAdapter:
    """Adapter for pure/read-only ``gimp.dev`` CLI metadata.

    Args:
        root: Local ``gimp.dev`` checkout root.
        enabled: Whether the optional integration is enabled.
        cli: Python console script name inside the ``gimp.dev`` environment.
        uv: Executable used to run the local project command.
        timeout: Subprocess timeout in seconds.
        runner: Optional test runner replacing ``subprocess.run``.
    """

    root: Path = DEFAULT_GIMP_DEV_ROOT
    enabled: bool = True
    cli: str = "gimp-dev"
    uv: str = "uv"
    timeout: float = 15.0
    runner: Runner | None = field(default=None, repr=False)

    @classmethod
    def from_config(cls, config: Any) -> GimpDevAdapter:
        """Build an adapter from ``ServerConfig``-like settings.

        Args:
            config: Object with optional ``gimp_dev_*`` attributes.

        Returns:
            Configured adapter instance.
        """
        return cls(
            root=Path(getattr(config, "gimp_dev_root", DEFAULT_GIMP_DEV_ROOT)),
            enabled=bool(getattr(config, "gimp_dev_enabled", True)),
            cli=str(getattr(config, "gimp_dev_cli", "gimp-dev")),
            uv=str(getattr(config, "gimp_dev_uv", "uv")),
            timeout=float(getattr(config, "gimp_dev_timeout", 15.0)),
        )

    @property
    def root_exists(self) -> bool:
        """Return whether the configured checkout root exists."""
        return self.root.exists()

    @property
    def pyproject_exists(self) -> bool:
        """Return whether the checkout looks like a Python project."""
        return (self.root / "pyproject.toml").exists()

    @property
    def available(self) -> bool:
        """Return whether the optional integration can be attempted."""
        return self.enabled and self.root_exists and self.pyproject_exists

    def command(self, args: Sequence[str]) -> list[str]:
        """Build the subprocess argv for a safe ``gimp-dev`` command.

        Args:
            args: Command-specific arguments passed after ``gimp-dev``.

        Returns:
            Complete argv list beginning with ``uv run gimp-dev``.
        """
        return [self.uv, "run", self.cli, *args]

    def status(self) -> dict[str, Any]:
        """Return local availability information without spawning GIMP.

        Returns:
            Dictionary with checkout, command, and safety information.
        """
        return {
            "enabled": self.enabled,
            "available": self.available,
            "root": str(self.root),
            "root_exists": self.root_exists,
            "pyproject_exists": self.pyproject_exists,
            "cli": self.cli,
            "uv": self.uv,
            "timeout": self.timeout,
            "safe_commands": list(SAFE_GIMP_DEV_COMMANDS),
            "unsafe_commands": list(UNSAFE_GIMP_DEV_COMMANDS),
            "policy": "adapter-gated-subprocess-json",
        }

    def load_catalog(self, *, validate: bool = True) -> dict[str, Any]:
        """Load the pure plug-in procedure catalog from ``gimp.dev``.

        Args:
            validate: Ask ``gimp-dev`` to run catalog validation when supported.

        Returns:
            Parsed JSON catalog object.
        """
        args = ["plugin-catalog"]
        if validate:
            args.append("--check")
        return self.run_json(args)

    def run_json(self, args: Sequence[str]) -> dict[str, Any]:
        """Run a safe ``gimp-dev`` command and parse its JSON stdout.

        Args:
            args: Command-specific CLI arguments. The first item must be in the
                safe command allowlist.

        Returns:
            Parsed JSON object from stdout.
        """
        if not args:
            raise GimpDevCommandError("missing gimp.dev command")
        command_name = args[0]
        if command_name not in SAFE_GIMP_DEV_COMMANDS:
            raise GimpDevCommandError(f"gimp.dev command is not allowlisted: {command_name}")
        if not self.available:
            raise GimpDevUnavailableError("gimp.dev integration is not available")

        process = self._run(self.command(args))
        if process.returncode != 0:
            stderr = process.stderr.strip() or "no stderr"
            raise GimpDevCommandError(
                f"gimp-dev {' '.join(args)} failed with exit {process.returncode}: {stderr}"
            )

        try:
            payload = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise GimpDevJSONError(f"gimp-dev returned invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise GimpDevJSONError("gimp-dev returned JSON that is not an object")
        return payload

    def summarize_catalog(self, catalog: dict[str, Any]) -> GimpDevCatalogSummary:
        """Summarize a raw plug-in catalog into a compact MCP-safe shape.

        Args:
            catalog: Raw JSON object from ``plugin-catalog``.

        Returns:
            Compact catalog summary.
        """
        plugins = catalog.get("plugins", [])
        if not isinstance(plugins, list):
            plugins = []

        validation_errors: list[str] = []
        root_errors = catalog.get("validation_errors", [])
        if isinstance(root_errors, list):
            validation_errors.extend(str(error) for error in root_errors)

        procedures: list[GimpDevProcedureRef] = []
        for plugin in plugins:
            if not isinstance(plugin, dict):
                continue
            plugin_name = str(plugin.get("name", "unknown"))
            plugin_errors = plugin.get("validation_errors", [])
            if isinstance(plugin_errors, list):
                validation_errors.extend(str(error) for error in plugin_errors)
            raw_procedures = plugin.get("procedures", [])
            if not isinstance(raw_procedures, list):
                continue
            for procedure in raw_procedures:
                if not isinstance(procedure, dict):
                    continue
                procedures.append(self._procedure_ref(plugin_name, procedure))

        return GimpDevCatalogSummary(
            plugin_count=len(plugins),
            procedure_count=len(procedures),
            validation_errors=tuple(validation_errors),
            procedures=tuple(procedures),
        )

    def _procedure_ref(self, plugin_name: str, procedure: dict[str, Any]) -> GimpDevProcedureRef:
        """Convert one raw procedure object into a compact reference."""
        raw_commands = procedure.get("commands", [])
        command_names = tuple(str(command) for command in raw_commands if isinstance(command, str))
        raw_arguments = procedure.get("arguments", [])
        argument_count = len(raw_arguments) if isinstance(raw_arguments, list) else 0
        name = str(procedure.get("name", "unknown"))
        handler = procedure.get("handler")
        safety_note = self._safety_note(plugin_name, name, procedure)
        return GimpDevProcedureRef(
            plugin=plugin_name,
            name=name,
            handler=str(handler) if handler is not None else None,
            command_names=command_names,
            argument_count=argument_count,
            safety_note=safety_note,
        )

    def _safety_note(
        self,
        plugin_name: str,
        procedure_name: str,
        procedure: dict[str, Any],
    ) -> str | None:
        """Return why a procedure needs a special adapter policy."""
        detail = str(procedure.get("detail", "")).lower()
        blurb = str(procedure.get("blurb", "")).lower()
        handler = str(procedure.get("handler", "")).lower()
        haystack = " ".join([plugin_name.lower(), procedure_name.lower(), detail, blurb, handler])
        if "repl" in haystack or "telnet" in haystack or "ptpython" in haystack:
            return "developer-repl-manual-session-only"
        if "export" in procedure_name and procedure.get("arguments"):
            return "live-file-output-requires-user-path-policy"
        if "remove" in procedure_name or "background-remove" in procedure_name:
            return "live-mutating-procedure-requires-transaction"
        return None

    def _run(self, argv: Sequence[str]) -> CompletedTextProcess:
        """Run the command using the configured runner."""
        if self.runner is not None:
            return self.runner(argv, self.root, self.timeout)
        return subprocess.run(
            list(argv),
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=self.timeout,
        )
