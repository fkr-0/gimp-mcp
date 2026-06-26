"""Install the bundled GIMP MCP plug-in into a local GIMP profile.

The live plug-in that GIMP executes is a copied script under the user's GIMP
configuration directory.  Keeping that deployed copy synchronized with
``gimp_plugin/gimp_mcp_plugin.py`` avoids confusing runtime failures where the
repository is fixed but GIMP is still running an older plug-in file.
"""

from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "gimp_plugin" / "gimp_mcp_plugin.py"
DEFAULT_PLUGIN_DIR_NAME = "gimp-mcp-pro"
DEFAULT_PLUGIN_EXECUTABLE_NAME = "gimp-mcp-pro"


@dataclass(frozen=True)
class InstallResult:
    """Result of installing the plug-in script."""

    source: Path
    target: Path
    byte_equal: bool


def default_config_home() -> Path:
    """Return the effective XDG config home."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()


def detect_gimp_version(config_home: Path) -> str:
    """Prefer the newest local GIMP profile directory, falling back to 3.2."""
    gimp_root = config_home / "GIMP"
    if not gimp_root.exists():
        return "3.2"

    versions: list[tuple[tuple[int, ...], str]] = []
    for child in gimp_root.iterdir():
        if not child.is_dir():
            continue
        try:
            parsed = tuple(int(part) for part in child.name.split("."))
        except ValueError:
            continue
        versions.append((parsed, child.name))

    if not versions:
        return "3.2"
    return sorted(versions)[-1][1]


def plugin_target(
    *,
    config_home: Path,
    gimp_version: str,
    plugin_dir_name: str = DEFAULT_PLUGIN_DIR_NAME,
    executable_name: str = DEFAULT_PLUGIN_EXECUTABLE_NAME,
) -> Path:
    """Return the target executable path for a GIMP plug-in profile."""
    return config_home / "GIMP" / gimp_version / "plug-ins" / plugin_dir_name / executable_name


def install_plugin(
    *,
    source: Path = DEFAULT_SOURCE,
    target: Path,
) -> InstallResult:
    """Copy the source plug-in to target, mark it executable, and verify bytes."""
    source = source.expanduser().resolve()
    target = target.expanduser()
    if not source.is_file():
        msg = f"source plug-in does not exist: {source}"
        raise FileNotFoundError(msg)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    target.chmod(0o755)

    byte_equal = source.read_bytes() == target.read_bytes()
    if not byte_equal:
        msg = f"installed plug-in differs from source: {target}"
        raise RuntimeError(msg)
    return InstallResult(source=source, target=target, byte_equal=byte_equal)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the installer."""
    parser = argparse.ArgumentParser(description="Install the bundled GIMP MCP plug-in.")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Source plug-in script to install.",
    )
    parser.add_argument(
        "--config-home",
        type=Path,
        default=default_config_home(),
        help="XDG config home containing the GIMP profile directory.",
    )
    parser.add_argument(
        "--gimp-version",
        default=None,
        help="GIMP profile version directory, for example 3.2. Defaults to newest detected profile.",
    )
    parser.add_argument(
        "--plugin-dir-name",
        default=DEFAULT_PLUGIN_DIR_NAME,
        help="Directory name under plug-ins/.",
    )
    parser.add_argument(
        "--executable-name",
        default=DEFAULT_PLUGIN_EXECUTABLE_NAME,
        help="Executable filename inside the plug-in directory.",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Explicit target path. Overrides config/profile naming options.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Install the plug-in and print the resolved paths."""
    args = build_parser().parse_args(argv)
    config_home = args.config_home.expanduser()
    gimp_version = args.gimp_version or detect_gimp_version(config_home)
    target = args.target or plugin_target(
        config_home=config_home,
        gimp_version=gimp_version,
        plugin_dir_name=args.plugin_dir_name,
        executable_name=args.executable_name,
    )
    result = install_plugin(source=args.source, target=target)
    print(f"source={result.source}")
    print(f"target={result.target}")
    print(f"byte_equal={str(result.byte_equal).lower()}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
