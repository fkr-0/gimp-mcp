"""Focused generated-code coverage for perspective and shear transform tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from gimp_mcp_pro.protocol import PluginResponse
from gimp_mcp_pro.tools.transform_tools import register_transform_tools

Tool = Callable[..., Awaitable[dict[str, Any]]]


class CaptureMCP:
    """Small FastMCP-compatible registrar used for direct tool invocation."""

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[Tool], Tool]:
        """Return a decorator that records a tool coroutine by function name."""
        del args, kwargs

        def decorator(fn: Tool) -> Tool:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class ScriptedBridge:
    """Async bridge fake that records generated Python without requiring GIMP."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def async_execute_python(
        self,
        code_lines: list[str],
        timeout: float | None = None,
    ) -> PluginResponse:
        del timeout
        self.calls.append(code_lines)
        return {"status": "success", "results": ["ok"]}


def registered_tools(bridge: ScriptedBridge) -> dict[str, Tool]:
    mcp = CaptureMCP()
    register_transform_tools(mcp, bridge)
    return mcp.tools


def generated_source(bridge: ScriptedBridge) -> str:
    return "\n".join("\n".join(call) for call in bridge.calls)


@pytest.mark.asyncio
async def test_perspective_layer_uses_item_perspective_transform_api() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["perspective_layer"](
        0,
        4,
        80,
        0,
        8,
        60,
        72,
        64,
        interpolation="linear",
        resize="clip",
        layer_name="Photo",
    )

    assert result["success"] is True
    assert result["operation"] == "perspective_layer"
    assert result["data"] == {
        "corners": [0.0, 4.0, 80.0, 0.0, 8.0, 60.0, 72.0, 64.0],
        "interpolation": "linear",
        "resize": "clip",
    }
    generated = generated_source(bridge)
    assert "target = image.get_layer_by_name('Photo')" in generated
    assert "Gimp.context_set_interpolation(Gimp.InterpolationType.LINEAR)" in generated
    assert "Gimp.context_set_transform_resize(Gimp.TransformResize.CLIP)" in generated
    assert (
        "Gimp.Item.transform_perspective(target, 0.0, 4.0, 80.0, 0.0, 8.0, 60.0, 72.0, 64.0)"
        in generated
    )
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_shear_layer_uses_item_shear_transform_api() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["shear_layer"](
        direction="vertical",
        magnitude=-12.5,
        interpolation="nohalo",
        resize="crop",
        layer_index=0,
    )

    assert result["success"] is True
    assert result["operation"] == "shear_layer"
    assert result["data"] == {
        "direction": "vertical",
        "magnitude": -12.5,
        "interpolation": "nohalo",
        "resize": "crop",
    }
    generated = generated_source(bridge)
    assert "target = layers[0]" in generated
    assert "Gimp.context_set_interpolation(Gimp.InterpolationType.NOHALO)" in generated
    assert "Gimp.context_set_transform_resize(Gimp.TransformResize.CROP)" in generated
    assert "Gimp.Item.transform_shear(target, Gimp.OrientationType.VERTICAL, -12.5)" in generated
