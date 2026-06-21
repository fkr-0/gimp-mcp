"""Tests for the asyncio-native bridge transport."""

from __future__ import annotations

import asyncio
import json
import struct
from typing import Any

import pytest

from gimp_mcp_pro.async_bridge import AsyncGimpBridge
from gimp_mcp_pro.bridge import HEADER_SIZE
from gimp_mcp_pro.utils.errors import GimpConnectionError, GimpTimeoutError


class AsyncMockGimpServer:
    """Minimal length-prefixed async test server."""

    def __init__(self, use_length_prefix: bool = True, hold_open: float = 0.0) -> None:
        self.use_length_prefix = use_length_prefix
        self.hold_open = hold_open
        self.responses: list[dict[str, Any]] = []
        self.received: list[dict[str, Any]] = []
        self._server: asyncio.AbstractServer | None = None
        self.port = 0

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        sock = self._server.sockets[0]
        self.port = int(sock.getsockname()[1])

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    def queue_response(self, response: dict[str, Any]) -> None:
        self.responses.append(response)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while self.responses:
                if self.use_length_prefix:
                    header = await reader.readexactly(HEADER_SIZE)
                    length = struct.unpack(">I", header)[0]
                    data = await reader.readexactly(length)
                else:
                    data = await reader.read(65536)
                self.received.append(json.loads(data.decode("utf-8")))
                if self.hold_open:
                    await asyncio.sleep(self.hold_open)
                    continue
                payload = json.dumps(self.responses.pop(0)).encode("utf-8")
                if self.use_length_prefix:
                    writer.write(struct.pack(">I", len(payload)) + payload)
                else:
                    writer.write(payload)
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()


@pytest.mark.asyncio
async def test_native_async_send_command_length_prefixed() -> None:
    server = AsyncMockGimpServer()
    server.queue_response({"status": "success", "results": {"key": "value"}})
    await server.start()

    bridge = AsyncGimpBridge(host="127.0.0.1", port=server.port, reconnect_delays=[])
    try:
        result = await bridge.send_command("test_command", {"arg": 1})
    finally:
        await bridge.disconnect()
        await server.stop()

    assert result["results"]["key"] == "value"
    assert server.received[0]["type"] == "test_command"
    assert server.received[0]["id"] == 1


@pytest.mark.asyncio
async def test_native_async_json_fallback() -> None:
    server = AsyncMockGimpServer(use_length_prefix=False)
    server.queue_response({"status": "success", "results": "ok"})
    await server.start()

    bridge = AsyncGimpBridge(
        host="127.0.0.1",
        port=server.port,
        use_length_prefix=False,
        reconnect_delays=[],
    )
    try:
        result = await bridge.send_command("raw", {})
    finally:
        await bridge.disconnect()
        await server.stop()

    assert result["status"] == "success"
    assert server.received[0]["type"] == "raw"


@pytest.mark.asyncio
async def test_native_async_timeout_resets_connection() -> None:
    server = AsyncMockGimpServer(hold_open=0.2)
    server.queue_response({"status": "success", "results": {}})
    await server.start()

    bridge = AsyncGimpBridge(host="127.0.0.1", port=server.port, reconnect_delays=[])
    try:
        with pytest.raises(GimpTimeoutError):
            await bridge.send_command("slow", {}, timeout=0.05)
        assert not bridge.connected
    finally:
        await bridge.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_native_async_message_size_limit() -> None:
    server = AsyncMockGimpServer()
    server.queue_response({"status": "success", "results": "x" * 100})
    await server.start()

    bridge = AsyncGimpBridge(
        host="127.0.0.1",
        port=server.port,
        max_message_size=32,
        reconnect_delays=[],
    )
    try:
        with pytest.raises(GimpConnectionError):
            await bridge.send_command("oversized")
    finally:
        await bridge.disconnect()
        await server.stop()


@pytest.mark.asyncio
async def test_native_async_context_manager() -> None:
    server = AsyncMockGimpServer()
    server.queue_response({"status": "success", "results": {"gimp": {"version": "3.2.4"}}})
    await server.start()

    try:
        async with AsyncGimpBridge(
            host="127.0.0.1", port=server.port, reconnect_delays=[]
        ) as bridge:
            assert bridge.connected
            result = await bridge.get_gimp_info()
    finally:
        await server.stop()

    assert result["results"]["gimp"]["version"] == "3.2.4"
