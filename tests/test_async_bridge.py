"""Tests for the first async bridge migration layer."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.bridge import GimpBridge
from tests.test_bridge import MockGimpServer


@pytest.mark.asyncio
async def test_async_execute_python_uses_existing_protocol() -> None:
    server = MockGimpServer()
    server.queue_response({"status": "success", "results": ["42\n"]})
    server.start()

    bridge = GimpBridge(host="localhost", port=server.port)
    bridge.connect()
    try:
        result = await bridge.async_execute_python(["print(42)"])
    finally:
        bridge.disconnect()
        server.stop()

    assert result["results"] == ["42\n"]
    assert server.received_requests[0]["type"] == "exec"
    assert server.received_requests[0]["params"]["args"] == ["pyGObject-console", ["print(42)"]]


@pytest.mark.asyncio
async def test_async_get_gimp_info_delegates_to_native_command() -> None:
    server = MockGimpServer()
    server.queue_response({"status": "success", "results": {"gimp": {"version": "3.2.4"}}})
    server.start()

    bridge = GimpBridge(host="localhost", port=server.port)
    bridge.connect()
    try:
        result = await bridge.async_get_gimp_info()
    finally:
        bridge.disconnect()
        server.stop()

    assert result["results"]["gimp"]["version"] == "3.2.4"
    assert server.received_requests[0]["type"] == "get_gimp_info"
