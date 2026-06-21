"""Typed settings for GIMP MCP Pro.

The project now uses pydantic-settings instead of manual os.getenv calls.
Settings are loaded from the process environment and, when present, from a
project-local .env file.  New variables use the GIMP_MCP_PRO_ prefix while the
older GIMP_MCP_ names remain accepted for compatibility.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class ServerConfig(BaseSettings):
    """Runtime configuration for the MCP server and GIMP bridge."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    gimp_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("GIMP_MCP_PRO_HOST", "GIMP_MCP_HOST"),
        description="GIMP plugin socket host",
    )
    gimp_port: int = Field(
        default=9877,
        validation_alias=AliasChoices("GIMP_MCP_PRO_PORT", "GIMP_MCP_PORT"),
        ge=1,
        le=65535,
        description="GIMP plugin socket port",
    )
    timeout: float = Field(
        default=30.0,
        validation_alias=AliasChoices("GIMP_MCP_PRO_TIMEOUT", "GIMP_MCP_TIMEOUT"),
        gt=0,
        description="Default command timeout in seconds",
    )
    long_timeout: float = Field(
        default=120.0,
        validation_alias=AliasChoices("GIMP_MCP_PRO_LONG_TIMEOUT", "GIMP_MCP_LONG_TIMEOUT"),
        gt=0,
        description="Long-running command timeout in seconds",
    )
    max_message_size: int = Field(
        default=100 * 1024 * 1024,
        validation_alias=AliasChoices("GIMP_MCP_PRO_MAX_MESSAGE_SIZE", "GIMP_MCP_MAX_MESSAGE_SIZE"),
        gt=0,
        description="Maximum accepted framed message size in bytes",
    )
    reconnect_delays: Annotated[tuple[float, ...], NoDecode] = Field(
        default=(0.5, 1.0, 2.0, 4.0, 8.0),
        validation_alias=AliasChoices("GIMP_MCP_PRO_RECONNECT_DELAYS", "GIMP_MCP_RECONNECT_DELAYS"),
        description="Retry delays in seconds for bridge reconnects",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("GIMP_MCP_PRO_LOG_LEVEL", "GIMP_MCP_LOG_LEVEL"),
        description="Logging level",
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("GIMP_MCP_PRO_DEBUG", "GIMP_MCP_DEBUG"),
        description="Enable debug logging",
    )
    use_length_prefix: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GIMP_MCP_PRO_USE_LENGTH_PREFIX",
            "GIMP_MCP_PRO_LENGTH_PREFIX",
            "GIMP_MCP_LENGTH_PREFIX",
        ),
        description="Use length-prefixed framing; disable for legacy JSON-boundary plugins",
    )
    plugin_dir: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("GIMP_MCP_PRO_PLUGIN_DIR", "GIMP_MCP_PLUGIN_DIR"),
        description="Optional explicit GIMP plugin directory",
    )
    gimp_dev_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("GIMP_MCP_PRO_GIMP_DEV_ENABLED", "GIMP_DEV_ENABLED"),
        description="Enable optional read-only integration with a local gimp.dev checkout",
    )
    gimp_dev_root: Path = Field(
        default=Path.home() / "code" / "gimp.dev",
        validation_alias=AliasChoices("GIMP_MCP_PRO_GIMP_DEV_ROOT", "GIMP_DEV_ROOT"),
        description="Local gimp.dev checkout used for catalog discovery",
    )
    gimp_dev_cli: str = Field(
        default="gimp-dev",
        validation_alias=AliasChoices("GIMP_MCP_PRO_GIMP_DEV_CLI", "GIMP_DEV_CLI"),
        description="gimp.dev console script name",
    )
    gimp_dev_uv: str = Field(
        default="uv",
        validation_alias=AliasChoices("GIMP_MCP_PRO_GIMP_DEV_UV", "GIMP_DEV_UV"),
        description="uv executable used to run gimp.dev CLI commands",
    )
    gimp_dev_timeout: float = Field(
        default=15.0,
        validation_alias=AliasChoices("GIMP_MCP_PRO_GIMP_DEV_TIMEOUT", "GIMP_DEV_TIMEOUT"),
        gt=0,
        description="Timeout in seconds for pure gimp.dev catalog commands",
    )

    @field_validator("reconnect_delays", mode="before")
    @classmethod
    def parse_reconnect_delays(cls, value: Any) -> Any:
        """Accept JSON arrays as well as comma/space separated delay strings."""
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ()
            if raw.startswith("["):
                return tuple(float(part) for part in json.loads(raw))
            separators = raw.replace(",", " ").split()
            return tuple(float(part) for part in separators)
        if isinstance(value, list):
            return tuple(float(part) for part in value)
        return value

    @field_validator("reconnect_delays")
    @classmethod
    def validate_reconnect_delays(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        """Reject negative reconnect delays while allowing zero for tests."""
        if any(delay < 0 for delay in value):
            raise ValueError("reconnect_delays must not contain negative values")
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: Any) -> str:
        """Normalize log levels and fail early on typos."""
        text = str(value).upper()
        if logging.getLevelName(text) == f"Level {text}":
            raise ValueError(f"invalid log level: {value!r}")
        return text

    @property
    def log_level_value(self) -> int:
        """Return the numeric logging level expected by logging APIs."""
        level = logging.getLevelName(self.log_level)
        if not isinstance(level, int):
            raise ValueError(f"invalid log level: {self.log_level!r}")
        return level

    def bridge_kwargs(self) -> dict[str, Any]:
        """Return constructor kwargs for GimpBridge."""
        return {
            "host": self.gimp_host,
            "port": self.gimp_port,
            "timeout": self.timeout,
            "long_timeout": self.long_timeout,
            "max_message_size": self.max_message_size,
            "reconnect_delays": list(self.reconnect_delays),
            "use_length_prefix": self.use_length_prefix,
        }
