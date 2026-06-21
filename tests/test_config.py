"""Tests for pydantic-settings based configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from gimp_mcp_pro.config import ServerConfig

ENV_KEYS = [
    "GIMP_MCP_PRO_HOST",
    "GIMP_MCP_PRO_PORT",
    "GIMP_MCP_PRO_TIMEOUT",
    "GIMP_MCP_PRO_LONG_TIMEOUT",
    "GIMP_MCP_PRO_MAX_MESSAGE_SIZE",
    "GIMP_MCP_PRO_RECONNECT_DELAYS",
    "GIMP_MCP_PRO_LOG_LEVEL",
    "GIMP_MCP_PRO_DEBUG",
    "GIMP_MCP_PRO_USE_LENGTH_PREFIX",
    "GIMP_MCP_PRO_PLUGIN_DIR",
    "GIMP_MCP_HOST",
    "GIMP_MCP_PORT",
    "GIMP_MCP_TIMEOUT",
    "GIMP_MCP_LENGTH_PREFIX",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests independent from the developer's shell environment."""
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults_are_safe_and_backward_compatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = ServerConfig()

    assert config.gimp_host == "localhost"
    assert config.gimp_port == 9877
    assert config.timeout == 30.0
    assert config.long_timeout == 120.0
    assert config.max_message_size == 100 * 1024 * 1024
    assert config.reconnect_delays == (0.5, 1.0, 2.0, 4.0, 8.0)
    assert config.log_level == "INFO"
    assert config.debug is False
    assert config.use_length_prefix is True


def test_new_environment_prefix_overrides_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIMP_MCP_PRO_HOST", "127.0.0.1")
    monkeypatch.setenv("GIMP_MCP_PRO_PORT", "9999")
    monkeypatch.setenv("GIMP_MCP_PRO_TIMEOUT", "7.5")
    monkeypatch.setenv("GIMP_MCP_PRO_LONG_TIMEOUT", "33")
    monkeypatch.setenv("GIMP_MCP_PRO_MAX_MESSAGE_SIZE", "4096")
    monkeypatch.setenv("GIMP_MCP_PRO_RECONNECT_DELAYS", "0, 0.25, 0.5")
    monkeypatch.setenv("GIMP_MCP_PRO_LOG_LEVEL", "debug")
    monkeypatch.setenv("GIMP_MCP_PRO_DEBUG", "true")
    monkeypatch.setenv("GIMP_MCP_PRO_USE_LENGTH_PREFIX", "false")

    config = ServerConfig()

    assert config.gimp_host == "127.0.0.1"
    assert config.gimp_port == 9999
    assert config.timeout == 7.5
    assert config.long_timeout == 33.0
    assert config.max_message_size == 4096
    assert config.reconnect_delays == (0.0, 0.25, 0.5)
    assert config.log_level == "DEBUG"
    assert config.debug is True
    assert config.use_length_prefix is False


def test_legacy_environment_names_still_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIMP_MCP_HOST", "legacy.local")
    monkeypatch.setenv("GIMP_MCP_PORT", "9988")
    monkeypatch.setenv("GIMP_MCP_TIMEOUT", "9")
    monkeypatch.setenv("GIMP_MCP_LENGTH_PREFIX", "false")

    config = ServerConfig()

    assert config.gimp_host == "legacy.local"
    assert config.gimp_port == 9988
    assert config.timeout == 9.0
    assert config.use_length_prefix is False


def test_dotenv_file_is_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "GIMP_MCP_PRO_HOST=dotenv.local",
                "GIMP_MCP_PRO_PORT=9878",
                "GIMP_MCP_PRO_RECONNECT_DELAYS=0.1,0.2",
            ]
        )
    )

    config = ServerConfig()

    assert config.gimp_host == "dotenv.local"
    assert config.gimp_port == 9878
    assert config.reconnect_delays == (0.1, 0.2)


def test_invalid_port_fails_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIMP_MCP_PRO_PORT", "70000")

    with pytest.raises(ValidationError):
        ServerConfig()


def test_invalid_log_level_fails_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIMP_MCP_PRO_LOG_LEVEL", "chatty")

    with pytest.raises(ValidationError):
        ServerConfig()


def test_bridge_kwargs_contains_all_bridge_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = ServerConfig(
        gimp_host="example",
        gimp_port=1234,
        reconnect_delays=(0.1,),
    )

    assert config.bridge_kwargs() == {
        "host": "example",
        "port": 1234,
        "timeout": 30.0,
        "long_timeout": 120.0,
        "max_message_size": 100 * 1024 * 1024,
        "reconnect_delays": [0.1],
        "use_length_prefix": True,
    }
