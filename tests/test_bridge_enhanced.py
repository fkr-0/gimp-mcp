"""Additional tests for bridge resilience and edge cases."""

from __future__ import annotations

import socket
import threading
import time

import pytest

from gimp_mcp_pro.bridge import GimpBridge
from gimp_mcp_pro.utils.errors import GimpConnectionError, GimpTimeoutError
from tests.test_bridge import MockGimpServer


def test_connect_retry_eventual_success() -> None:
    """A server that starts during the retry window should still connect."""
    server = MockGimpServer()
    original_start = server.start

    def start_later() -> None:
        time.sleep(0.05)
        original_start()

    thread = threading.Thread(target=start_later, daemon=True)
    thread.start()

    bridge = GimpBridge(
        host="localhost",
        port=server.port,
        timeout=0.2,
        reconnect_delays=[0.01, 0.05, 0.1],
    )
    try:
        bridge.connect()
        assert bridge.connected
    finally:
        bridge.disconnect()
        server.stop()
        thread.join(timeout=1.0)


def test_send_command_timeout_resets_connection() -> None:
    """An open connection that never responds should raise a timeout."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("localhost", 0))
    port = listener.getsockname()[1]
    listener.listen(1)

    def accept_and_hold() -> None:
        conn, _ = listener.accept()
        try:
            conn.recv(1024)
            time.sleep(0.25)
        finally:
            conn.close()
            listener.close()

    thread = threading.Thread(target=accept_and_hold, daemon=True)
    thread.start()

    bridge = GimpBridge(host="localhost", port=port, timeout=0.2, reconnect_delays=[])
    bridge.connect()

    with pytest.raises(GimpTimeoutError):
        bridge.send_command("no_response", timeout=0.05)

    assert not bridge.connected
    thread.join(timeout=1.0)


def test_instance_max_message_size_is_enforced() -> None:
    """The per-instance size limit should reject oversized framed responses."""
    server = MockGimpServer()
    server.queue_response({"status": "success", "results": "x" * 100})
    server.start()

    bridge = GimpBridge(host="localhost", port=server.port, max_message_size=32)
    bridge.connect()
    try:
        with pytest.raises(GimpConnectionError):
            bridge.send_command("oversized")
    finally:
        server.stop()
        bridge.disconnect()


def test_thread_safe_command_dispatch() -> None:
    """Concurrent callers should be serialized by the bridge lock."""
    server = MockGimpServer()
    for _ in range(4):
        server.queue_response({"status": "success", "results": {}})
    server.start()

    bridge = GimpBridge(host="localhost", port=server.port)
    bridge.connect()
    results: list[dict] = []

    def worker() -> None:
        results.append(bridge.send_command("echo", {}))

    try:
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=1.0)

        assert len(results) == 4
        ids = [request["id"] for request in server.received_requests]
        assert ids == [1, 2, 3, 4]
    finally:
        server.stop()
        bridge.disconnect()
