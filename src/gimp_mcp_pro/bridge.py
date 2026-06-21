"""GimpBridge — reliable communication layer between MCP server and GIMP plugin.

Key improvements over existing implementations:
- Length-prefixed framing (no more JSON boundary guessing)
- Persistent connection (no socket-per-command overhead)
- Automatic reconnection with exponential backoff
- Thread-safe send/receive with locking
- Configurable timeouts per command
- Fallback to JSON boundary detection for backward compatibility
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import struct
import threading
import time
from contextlib import suppress
from typing import Any, cast

from gimp_mcp_pro.protocol import BitmapRegion, CommandParams, PluginResponse
from gimp_mcp_pro.utils.errors import (
    GimpCommandError,
    GimpConnectionError,
    GimpTimeoutError,
)

logger = logging.getLogger("gimp_mcp_pro.bridge")

# Protocol constants
HEADER_SIZE = 4  # 4-byte big-endian uint32 length prefix
MAX_MESSAGE_SIZE = 100 * 1024 * 1024  # 100 MB max (for base64 image data)
DEFAULT_TIMEOUT = 30.0
LONG_TIMEOUT = 120.0  # For filters, exports, large operations
RECONNECT_DELAYS = [0.5, 1.0, 2.0, 4.0, 8.0]  # Exponential backoff


class GimpBridge:
    """Synchronous TCP bridge for the GIMP MCP Pro plug-in.

    The bridge owns one socket connection, serializes commands with a lock, and
    preserves the length-prefixed JSON protocol used by the GIMP plug-in. Async
    MCP tools should prefer ``AsyncGimpBridge``; this class remains the stable
    synchronous adapter for CLI utilities, diagnostics, and legacy callers.

    Args:
        host: Hostname or IP address where the GIMP plug-in listens.
        port: TCP port exposed by the GIMP plug-in.
        timeout: Default command and connection timeout in seconds.
        use_length_prefix: Whether to use the four-byte length-prefixed JSON
            framing protocol.
        long_timeout: Timeout in seconds for heavy operations such as bitmap
            export or filters.
        max_message_size: Maximum accepted response size in bytes.
        reconnect_delays: Retry backoff values used before the final connection
            attempt.

    Examples:
        >>> bridge = GimpBridge(host="localhost", port=9877)
        >>> bridge.connect()
        >>> bridge.get_image_metadata()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9877,
        timeout: float = DEFAULT_TIMEOUT,
        use_length_prefix: bool = True,
        long_timeout: float = LONG_TIMEOUT,
        max_message_size: int = MAX_MESSAGE_SIZE,
        reconnect_delays: list[float] | tuple[float, ...] | None = None,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.long_timeout = long_timeout
        self.max_message_size = max_message_size
        self.reconnect_delays = list(reconnect_delays or RECONNECT_DELAYS)
        self.use_length_prefix = use_length_prefix

        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._command_id = 0
        self._connected = False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Whether the bridge currently owns an open socket.

        Returns:
            True when the bridge is marked connected and a socket object is
            present, otherwise False.
        """
        return self._connected and self._sock is not None

    def connect(self) -> None:
        """Connect to the GIMP plugin socket with retry logic."""
        if self._connected and self._sock is not None:
            return

        for delay in self.reconnect_delays:
            try:
                self._do_connect()
                return
            except Exception as e:
                logger.warning(f"Connection attempt failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)

        # Final attempt
        try:
            self._do_connect()
        except Exception as e:
            raise GimpConnectionError(
                f"Could not connect to GIMP at {self.host}:{self.port} "
                f"after {len(self.reconnect_delays) + 1} attempts. "
                f"Ensure the GIMP MCP plugin is running. Last error: {e}"
            ) from e

    def _do_connect(self) -> None:
        """Perform a single connection attempt."""
        self.disconnect()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        self._sock = sock
        self._connected = True
        logger.info(f"Connected to GIMP at {self.host}:{self.port}")

    def disconnect(self) -> None:
        """Close the connection."""
        if self._sock is not None:
            with suppress(Exception):
                self._sock.close()
            self._sock = None
        self._connected = False

    def ensure_connected(self) -> None:
        """Ensure we have an active connection, reconnecting if needed."""
        if not self.connected:
            self.connect()

    # ------------------------------------------------------------------
    # Command sending
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._command_id += 1
        return self._command_id

    def send_command(
        self,
        command_type: str,
        params: CommandParams | None = None,
        timeout: float | None = None,
    ) -> PluginResponse:
        """Send a command to GIMP and wait for the response.

        Args:
            command_type: The command identifier (e.g., "get_image_metadata",
                          "exec", "create_layer")
            params: Command parameters dict
            timeout: Override default timeout for this command

        Returns:
            Response dict from GIMP plugin

        Raises:
            GimpConnectionError: If connection fails
            GimpCommandError: If GIMP returns an error
            GimpTimeoutError: If command times out
        """
        effective_timeout = timeout or self.timeout

        with self._lock:
            self.ensure_connected()
            assert self._sock is not None

            # Set timeout for this command
            self._sock.settimeout(effective_timeout)

            cmd_id = self._next_id()
            payload = {
                "id": cmd_id,
                "type": command_type,
                "params": params or {},
            }

            try:
                self._send(payload)
                response = self._receive()
            except TimeoutError as e:
                self.disconnect()
                raise GimpTimeoutError(
                    f"Command '{command_type}' timed out after {effective_timeout}s",
                    timeout_seconds=effective_timeout,
                ) from e
            except (ConnectionError, OSError, BrokenPipeError) as e:
                self.disconnect()
                raise GimpConnectionError(
                    f"Connection lost while executing '{command_type}': {e}"
                ) from e

        # Check for error in response
        if isinstance(response, dict) and response.get("status") == "error":
            raise GimpCommandError(
                message=response.get("error", "Unknown GIMP error"),
                command=command_type,
                traceback=response.get("traceback"),
            )

        return response

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        """Execute Python code in GIMP's PyGObject console.

        This is the escape hatch for operations that don't have a
        dedicated command handler in the plugin. The code runs in
        GIMP's persistent Python context, so imports and variables
        persist across calls.

        Args:
            code_lines: List of Python code strings to execute sequentially
            timeout: Override timeout (use longer for heavy operations)

        Returns:
            Response dict with "results" containing stdout output per line
        """
        return self.send_command(
            "exec",
            {"args": ["pyGObject-console", code_lines]},
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Async adapters
    # ------------------------------------------------------------------

    async def async_send_command(
        self,
        command_type: str,
        params: CommandParams | None = None,
        timeout: float | None = None,
    ) -> PluginResponse:
        """Async adapter for send_command.

        This is the low-risk first migration step: it preserves the proven
        synchronous socket implementation and moves the blocking call to a
        worker thread so async MCP tools do not block the event loop.
        """
        return await asyncio.to_thread(self.send_command, command_type, params, timeout)

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        """Async adapter for execute_python."""
        return await asyncio.to_thread(self.execute_python, code_lines, timeout)

    async def async_evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        """Async adapter for evaluate_python."""
        return await asyncio.to_thread(self.evaluate_python, expressions, timeout)

    async def async_get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: BitmapRegion | None = None,
    ) -> PluginResponse:
        """Async adapter for get_image_bitmap."""
        return await asyncio.to_thread(self.get_image_bitmap, max_width, max_height, region)

    async def async_get_image_metadata(self) -> PluginResponse:
        """Async adapter for get_image_metadata."""
        return await asyncio.to_thread(self.get_image_metadata)

    async def async_get_context_state(self) -> PluginResponse:
        """Async adapter for get_context_state."""
        return await asyncio.to_thread(self.get_context_state)

    async def async_get_gimp_info(self) -> PluginResponse:
        """Async adapter for get_gimp_info."""
        return await asyncio.to_thread(self.get_gimp_info)

    def evaluate_python(
        self,
        expressions: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        """Evaluate Python expressions in GIMP and return their values.

        Unlike execute_python, this returns the actual values of expressions
        rather than captured stdout.
        """
        return self.send_command(
            "exec",
            {"args": ["pyGObject-eval", expressions]},
            timeout=timeout,
        )

    def get_image_bitmap(
        self,
        max_width: int | None = None,
        max_height: int | None = None,
        region: BitmapRegion | None = None,
    ) -> PluginResponse:
        """Get the current image as base64 PNG data.

        This is a high-level convenience for the get_image_bitmap
        command, which has native handling in the GIMP plugin.
        """
        params: CommandParams = {}
        if max_width is not None:
            params["max_width"] = max_width
        if max_height is not None:
            params["max_height"] = max_height
        if region is not None:
            params["region"] = region
        return self.send_command(
            "get_image_bitmap",
            params,
            timeout=self.long_timeout,
        )

    def get_image_metadata(self) -> PluginResponse:
        """Get metadata about the current image (no bitmap transfer)."""
        return self.send_command("get_image_metadata")

    def get_context_state(self) -> PluginResponse:
        """Get GIMP's current context (colors, brush, opacity, etc.)."""
        return self.send_command("get_context_state")

    def get_gimp_info(self) -> PluginResponse:
        """Get GIMP environment information."""
        return self.send_command("get_gimp_info")

    # ------------------------------------------------------------------
    # Wire protocol — length-prefixed framing
    # ------------------------------------------------------------------

    def _send(self, payload: dict[str, Any]) -> None:
        """Send a JSON payload with length-prefix framing."""
        assert self._sock is not None
        data = json.dumps(payload).encode("utf-8")

        if self.use_length_prefix:
            header = struct.pack(">I", len(data))
            self._sock.sendall(header + data)
        else:
            # Fallback: raw JSON (backward compat with maorcc plugin)
            self._sock.sendall(data)

    def _receive(self) -> PluginResponse:
        """Receive a JSON response."""
        assert self._sock is not None

        if self.use_length_prefix:
            return self._receive_length_prefixed()
        else:
            return self._receive_json_boundary()

    def _receive_length_prefixed(self) -> PluginResponse:
        """Receive using 4-byte length prefix."""
        assert self._sock is not None

        # Read length header
        header = self._recv_exact(HEADER_SIZE)
        length = struct.unpack(">I", header)[0]

        if length > self.max_message_size:
            raise GimpConnectionError(
                f"Message size {length} exceeds maximum {self.max_message_size}"
            )

        # Read payload
        data = self._recv_exact(length)
        return cast(PluginResponse, json.loads(data.decode("utf-8")))

    def _receive_json_boundary(self) -> PluginResponse:
        """Receive by detecting JSON boundaries (fallback mode).

        This replicates the approach used by maorcc's implementation
        for backward compatibility with existing GIMP plugins.
        """
        assert self._sock is not None

        buffer = b""
        while True:
            chunk = self._sock.recv(8192)
            if not chunk:
                if buffer:
                    try:
                        return cast(PluginResponse, json.loads(buffer.decode("utf-8")))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
                raise GimpConnectionError("Connection closed by GIMP plugin")

            buffer += chunk

            # Try to parse as complete JSON
            try:
                return cast(PluginResponse, json.loads(buffer.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue  # Need more data

    def _recv_exact(self, n: int) -> bytes:
        """Receive exactly n bytes from the socket."""
        assert self._sock is not None

        data = bytearray()
        while len(data) < n:
            remaining = n - len(data)
            chunk = self._sock.recv(min(remaining, 65536))
            if not chunk:
                raise GimpConnectionError(
                    f"Connection closed while reading (got {len(data)} of {n} bytes)"
                )
            data.extend(chunk)
        return bytes(data)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> GimpBridge:
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()
