"""Command line interface for GIMP MCP Pro."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable, Sequence
from typing import Any, cast

from pydantic import ValidationError

from gimp_mcp_pro.bridge import GimpBridge
from gimp_mcp_pro.config import ServerConfig
from gimp_mcp_pro.utils.errors import GimpMCPError
from gimp_mcp_pro.utils.logging import setup_logging


def _make_config(env_file: str | None = None) -> ServerConfig:
    """Create settings, optionally loading a caller-provided .env file."""
    if env_file:
        return ServerConfig(_env_file=env_file)  # type: ignore[call-arg]
    return ServerConfig()


def _apply_overrides(config: ServerConfig, args: argparse.Namespace) -> ServerConfig:
    """Apply CLI option overrides on top of environment-loaded settings."""
    updates: dict[str, Any] = {}
    for arg_name, field_name in (
        ("host", "gimp_host"),
        ("port", "gimp_port"),
        ("timeout", "timeout"),
        ("long_timeout", "long_timeout"),
        ("log_level", "log_level"),
    ):
        value = getattr(args, arg_name, None)
        if value is not None:
            updates[field_name] = value
    if getattr(args, "debug", False):
        updates["debug"] = True
    return config.model_copy(update=updates)


def _config_as_json(config: ServerConfig) -> str:
    """Serialize settings in a stable, human-readable JSON form."""
    return json.dumps(config.model_dump(mode="json"), indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    """Build the root CLI parser."""
    parser = argparse.ArgumentParser(
        prog="gimp-mcp-pro",
        description="Run and inspect the GIMP MCP Pro server.",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional .env file to load instead of the project-local default.",
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--host", default=None, help="Override the GIMP plugin host.")
    common.add_argument("--port", type=int, default=None, help="Override the GIMP plugin port.")
    common.add_argument(
        "--timeout", type=float, default=None, help="Override command timeout seconds."
    )
    common.add_argument(
        "--long-timeout",
        type=float,
        default=None,
        help="Override long command timeout seconds.",
    )
    common.add_argument("--log-level", default=None, help="Override logging level.")
    common.add_argument("--debug", action="store_true", help="Enable debug logging.")

    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser("serve", parents=[common], help="Run the MCP server.")
    serve.set_defaults(func=cmd_serve)

    config = subparsers.add_parser("config", parents=[common], help="Print resolved configuration.")
    config.add_argument(
        "--json", action="store_true", help="Print JSON instead of key=value lines."
    )
    config.set_defaults(func=cmd_config)

    doctor = subparsers.add_parser(
        "doctor", parents=[common], help="Inspect config and optionally test GIMP connectivity."
    )
    doctor.add_argument(
        "--connect", action="store_true", help="Attempt to connect to the GIMP plugin."
    )
    doctor.set_defaults(func=cmd_doctor)

    repl = subparsers.add_parser(
        "repl", parents=[common], help="Interactive bridge REPL for a live GIMP plugin."
    )
    repl.set_defaults(func=cmd_repl)

    parser.set_defaults(func=cmd_serve, command="serve")
    return parser


def cmd_config(args: argparse.Namespace, config: ServerConfig) -> int:
    """Print resolved settings."""
    if args.json:
        print(_config_as_json(config))
        return 0

    for key, value in config.model_dump(mode="json").items():
        print(f"{key}={value}")
    return 0


def cmd_doctor(args: argparse.Namespace, config: ServerConfig) -> int:
    """Print runtime diagnostics and optionally verify socket connectivity."""
    print("GIMP MCP Pro diagnostics")
    print(_config_as_json(config))

    if not args.connect:
        print("connectivity=skipped")
        return 0

    bridge = GimpBridge(**config.bridge_kwargs())
    try:
        bridge.connect()
    except GimpMCPError as exc:
        print(f"connectivity=failed: {exc}", file=sys.stderr)
        return 2
    finally:
        bridge.disconnect()

    print("connectivity=ok")
    return 0


def cmd_repl(args: argparse.Namespace, config: ServerConfig) -> int:
    """Run a small line-oriented bridge REPL.

    Commands:
    - :quit / :exit exits
    - :metadata calls get_image_metadata
    - :context calls get_context_state
    - JSON lines shaped as {"type": "command", "params": {...}} call send_command
    - all other lines are executed as one-line Python through execute_python
    """
    setup_logging(level=config.log_level_value, debug=config.debug)
    bridge = GimpBridge(**config.bridge_kwargs())
    bridge.connect()
    print("Connected. Type :quit to exit.")

    try:
        while True:
            try:
                line = input("gimp-mcp> ").strip()
            except EOFError:
                print()
                return 0

            if not line:
                continue
            if line in {":quit", ":exit"}:
                return 0
            if line == ":metadata":
                print(json.dumps(bridge.get_image_metadata(), indent=2, sort_keys=True))
                continue
            if line == ":context":
                print(json.dumps(bridge.get_context_state(), indent=2, sort_keys=True))
                continue

            try:
                if line.startswith("{"):
                    payload = json.loads(line)
                    command = payload["type"]
                    params = payload.get("params", {})
                    result = bridge.send_command(command, params)
                else:
                    result = bridge.execute_python([line])
                print(json.dumps(result, indent=2, sort_keys=True))
            except (GimpMCPError, KeyError, json.JSONDecodeError) as exc:
                print(f"error: {exc}", file=sys.stderr)
    finally:
        bridge.disconnect()


def cmd_async_repl(args: argparse.Namespace, config: ServerConfig) -> int:
    """Run the asyncio-native bridge REPL."""
    return asyncio.run(_run_async_repl(args, config))


async def _run_async_repl(args: argparse.Namespace, config: ServerConfig) -> int:
    """Async line-oriented REPL backed by AsyncGimpBridge."""
    setup_logging(level=config.log_level_value, debug=config.debug)
    from gimp_mcp_pro.async_bridge import AsyncGimpBridge

    bridge = AsyncGimpBridge(**config.bridge_kwargs())
    await bridge.connect()
    print("Connected with AsyncGimpBridge. Type :quit to exit.")

    try:
        while True:
            try:
                line = await asyncio.to_thread(input, "gimp-mcp-async> ")
            except EOFError:
                print()
                return 0

            line = line.strip()
            if not line:
                continue
            if line in {":quit", ":exit"}:
                return 0
            if line == ":metadata":
                print(json.dumps(await bridge.get_image_metadata(), indent=2, sort_keys=True))
                continue
            if line == ":context":
                print(json.dumps(await bridge.get_context_state(), indent=2, sort_keys=True))
                continue

            try:
                if line.startswith("{"):
                    payload = json.loads(line)
                    command = payload["type"]
                    params = payload.get("params", {})
                    result = await bridge.send_command(command, params)
                else:
                    result = await bridge.execute_python([line])
                print(json.dumps(result, indent=2, sort_keys=True))
            except (GimpMCPError, KeyError, json.JSONDecodeError) as exc:
                print(f"error: {exc}", file=sys.stderr)
    finally:
        await bridge.disconnect()


def cmd_serve(args: argparse.Namespace, config: ServerConfig) -> int:
    """Run the MCP server."""
    setup_logging(level=config.log_level_value, debug=config.debug)
    from gimp_mcp_pro.server import create_server

    mcp = create_server(config)
    mcp.run()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = _apply_overrides(_make_config(args.env_file), args)
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        return 2
    command = cast(Callable[[argparse.Namespace, ServerConfig], int], args.func)
    return command(args, config)


if __name__ == "__main__":
    raise SystemExit(main())
