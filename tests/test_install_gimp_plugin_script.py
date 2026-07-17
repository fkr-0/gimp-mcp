from __future__ import annotations

import stat
from pathlib import Path

from scripts.install_gimp_plugin import (
    DEFAULT_GIMP_VERSION,
    detect_gimp_version,
    gimp_profile_dir,
    install_plugin,
    plugin_target,
)


def test_detect_gimp_version_prefers_newest_profile(tmp_path: Path) -> None:
    (tmp_path / "GIMP" / "3.0").mkdir(parents=True)
    (tmp_path / "GIMP" / "3.2").mkdir(parents=True)

    assert detect_gimp_version(tmp_path) == "3.2"


def test_detect_gimp_version_uses_canonical_default_when_no_profile_exists(tmp_path: Path) -> None:
    assert detect_gimp_version(tmp_path) == DEFAULT_GIMP_VERSION


def test_gimp_profile_dir_uses_detected_profile_version(tmp_path: Path) -> None:
    (tmp_path / "GIMP" / "3.0").mkdir(parents=True)
    (tmp_path / "GIMP" / "3.2").mkdir(parents=True)

    assert gimp_profile_dir(tmp_path) == tmp_path / "GIMP" / "3.2"


def test_plugin_target_uses_gimp_profile_layout(tmp_path: Path) -> None:
    target = plugin_target(config_home=tmp_path, gimp_version="3.2")

    assert target == tmp_path / "GIMP" / "3.2" / "plug-ins" / "gimp-mcp-pro" / "gimp-mcp-pro"


def test_install_plugin_copies_verifies_and_marks_executable(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
    target = tmp_path / "GIMP" / "3.2" / "plug-ins" / "gimp-mcp-pro" / "gimp-mcp-pro"

    result = install_plugin(source=source, target=target)

    assert result.source == source.resolve()
    assert result.target == target
    assert result.byte_equal is True
    assert target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert target.stat().st_mode & stat.S_IXUSR


def test_setup_script_delegates_plugin_install_to_python_installer() -> None:
    text = (Path(__file__).resolve().parents[1] / "setup.sh").read_text(encoding="utf-8")

    assert "scripts/install_gimp_plugin.py" in text
    assert "--target" in text
    assert "cp gimp_plugin/gimp_mcp_plugin.py" not in text
