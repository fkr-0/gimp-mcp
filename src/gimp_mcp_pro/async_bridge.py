"""Asyncio-native GIMP bridge.

This module provides a real async transport for the GIMP MCP plug-in.  It
shares the same framed JSON protocol and error semantics as ``GimpBridge`` but
uses ``asyncio.open_connection`` and stream APIs instead of moving synchronous
socket calls into worker threads.
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
from contextlib import suppress
from typing import Any, cast

from gimp_mcp_pro.bridge import (
    DEFAULT_TIMEOUT,
    HEADER_SIZE,
    LONG_TIMEOUT,
    MAX_MESSAGE_SIZE,
    RECONNECT_DELAYS,
)
from gimp_mcp_pro.utils.errors import GimpCommandError, GimpConnectionError, GimpTimeoutError

logger = logging.getLogger("gimp_mcp_pro.async_bridge")


class AsyncGimpBridge:
    """Asyncio-native TCP bridge for the GIMP MCP Pro plug-in."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9877,
        timeout: float = DEFAULT_TIMEOUT,
        use_length_prefix: bool = True,
        long_timeout: float = LONG_TIMEOUT,
        max_message_size: int = MAX_MESSAGE_SIZE,
        reconnect_delays: list[float] | tuple[float, ...] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.use_length_prefix = use_length_prefix
        self.long_timeout = long_timeout
        self.max_message_size = max_message_size
        self.reconnect_delays = list(reconnect_delays or RECONNECT_DELAYS)

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._command_id = 0
        self._connected = False

    @property
    def connected(self) -> bool:
        """Return whether the bridge has an open stream pair."""
        return self._connected and self._reader is not None and self._writer is not None

    async def connect(self) -> None:
        """Connect to the plug-in, retrying with configured backoff."""
        if self.connected:
            return

        for delay in self.reconnect_delays:
            try:
                await self._do_connect()
                return
            except Exception as exc:
                logger.warning("Connection attempt failed: %s. Retrying in %ss...", exc, delay)
                await asyncio.sleep(delay)

        try:
            await self._do_connect()
        except Exception as exc:
            raise GimpConnectionError(
                f"Could not connect to GIMP at {self.host}:{self.port} "
                f"after {len(self.reconnect_delays) + 1} attempts. "
                f"Ensure the GIMP MCP plugin is running. Last error: {exc}"
            ) from exc

    async def _do_connect(self) -> None:
        """Perform one async connection attempt."""
        await self.disconnect()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
        except TimeoutError as exc:
            raise GimpTimeoutError(
                f"Connection to {self.host}:{self.port} timed out after {self.timeout}s",
                timeout_seconds=self.timeout,
            ) from exc
        self._reader = reader
        self._writer = writer
        self._connected = True
        logger.info("Connected to GIMP at %s:%s", self.host, self.port)

    async def disconnect(self) -> None:
        """Close the stream connection."""
        writer = self._writer
        self._reader = None
        self._writer = None
        self._connected = False
        if writer is not None:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()

    async def ensure_connected(self) -> None:
        """Ensure a stream connection exists."""
        if not self.connected:
            await self.connect()

    def _next_id(self) -> int:
        self._command_id += 1
        return self._command_id

    async def send_command(
        self,
        command_type: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send a command and wait for its response."""
        effective_timeout = timeout or self.timeout
        async with self._lock:
            await self.ensure_connected()
            payload = {
                "id": self._next_id(),
                "type": command_type,
                "params": params or {},
            }
            try:
                response = await asyncio.wait_for(
                    self._send_and_receive(payload),
                    timeout=effective_timeout,
                )
            except TimeoutError as exc:
                await self.disconnect()
                raise GimpTimeoutError(
                    f"Command '{command_type}' timed out after {effective_timeout}s",
                    timeout_seconds=effective_timeout,
                ) from exc
            except (ConnectionError, OSError, asyncio.IncompleteReadError) as exc:
                await self.disconnect()
                raise GimpConnectionError(
                    f"Connection lost while executing '{command_type}': {exc}"
                ) from exc
            except (json.JSONDecodeError, UnicodeDecodeError, struct.error) as exc:
                await self.disconnect()
                raise GimpConnectionError(
                    f"Protocol error while executing '{command_type}': {exc}"
                ) from exc

        if response.get("status") == "error":
            raise GimpCommandError(
                message=response.get("error", "Unknown GIMP error"),
                command=command_type,
                traceback=response.get("traceback"),
            )
        return response

    async def _send_and_receive(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self._send(payload)
        return await self._receive()

    async def _send(self, payload: dict[str, Any]) -> None:
        """Send one JSON payload."""
        if self._writer is None:
            raise GimpConnectionError("Not connected")
        data = json.dumps(payload).encode("utf-8")
        if self.use_length_prefix:
            self._writer.write(struct.pack(">I", len(data)) + data)
        else:
            self._writer.write(data)
        await self._writer.drain()

    async def _receive(self) -> dict[str, Any]:
        if self.use_length_prefix:
            return await self._receive_length_prefixed()
        return await self._receive_json_boundary()

    async def _receive_length_prefixed(self) -> dict[str, Any]:
        """Receive one length-prefixed JSON response."""
        if self._reader is None:
            raise GimpConnectionError("Not connected")
        header = await self._reader.readexactly(HEADER_SIZE)
        length = struct.unpack(">I", header)[0]
        if length > self.max_message_size:
            raise GimpConnectionError(
                f"Message size {length} exceeds maximum {self.max_message_size}"
            )
        data = await self._reader.readexactly(length)
        return cast(dict[str, Any], json.loads(data.decode("utf-8")))

    async def _receive_json_boundary(self) -> dict[str, Any]:
        """Receive one raw JSON response by parsing until complete."""
        if self._reader is None:
            raise GimpConnectionError("Not connected")
        buffer = b""
        while True:
            chunk = await self._reader.read(8192)
            if not chunk:
                if buffer:
                    return cast(dict[str, Any], json.loads(buffer.decode("utf-8")))
                raise GimpConnectionError("Connection closed by GIMP plugin")
            buffer += chunk
            try:
                return cast(dict[str, Any], json.loads(buffer.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

    async def execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute Python code in GIMP's PyGObject console."""
        return await self.send_command(
            "exec",
            {"args": ["pyGObject-console", code_lines]},
            timeout=timeout,
        )

    async def evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Evaluate Python expressions in GIMP."""
        return await self.send_command(
            "exec",
            {"args": ["pyGObject-eval", expressions]},
            timeout=timeout,
        )

    async def get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Get the current image as base64 PNG data."""
        params: dict[str, Any] = {}
        if max_width is not None:
            params["max_width"] = max_width
        if max_height is not None:
            params["max_height"] = max_height
        if region is not None:
            params["region"] = region
        return await self.send_command("get_image_bitmap", params, timeout=self.long_timeout)

    async def get_image_metadata(self) -> dict[str, Any]:
        """Get active image metadata."""
        return await self.send_command("get_image_metadata")

    async def get_context_state(self) -> dict[str, Any]:
        """Get current GIMP context state."""
        return await self.send_command("get_context_state")

    async def get_gimp_info(self) -> dict[str, Any]:
        """Get GIMP environment information."""
        return await self.send_command("get_gimp_info")

    async def async_send_command(
        self,
        command_type: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Compatibility alias matching GimpBridge's async adapter name."""
        return await self.send_command(command_type, params, timeout)

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Compatibility alias matching GimpBridge's async adapter name."""
        return await self.execute_python(code_lines, timeout)

    async def async_evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Compatibility alias matching GimpBridge's async adapter name."""
        return await self.evaluate_python(expressions, timeout)

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Compatibility alias matching GimpBridge's async adapter name."""
        return await self.get_image_bitmap(max_width, max_height, region)

    async def async_get_image_metadata(self) -> dict[str, Any]:
        """Compatibility alias matching GimpBridge's async adapter name."""
        return await self.get_image_metadata()

    async def async_get_context_state(self) -> dict[str, Any]:
        """Compatibility alias matching GimpBridge's async adapter name."""
        return await self.get_context_state()

    async def async_get_gimp_info(self) -> dict[str, Any]:
        """Compatibility alias matching GimpBridge's async adapter name."""
        return await self.get_gimp_info()

    async def __aenter__(self) -> AsyncGimpBridge:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()
