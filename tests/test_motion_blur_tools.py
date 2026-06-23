"""Focused generated-code coverage for motion blur filter tool."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from gimp_mcp_pro.protocol import PluginResponse
from gimp_mcp_pro.tools.filter_tools import register_filter_tools

Tool = Callable[..., Awaitable[dict[str, Any]]]


class CaptureMCP:
    """Small FastMCP-compatible registrar used for direct tool invocation."""

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[Tool], Tool]:
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
        return {"status": "success", "results": ["{}"]}


def registered_tools(bridge: ScriptedBridge) -> dict[str, Tool]:
    mcp = CaptureMCP()
    register_filter_tools(mcp, bridge)
    return mcp.tools


def generated_source(bridge: ScriptedBridge) -> str:
    return "\n".join("\n".join(call) for call in bridge.calls)


@pytest.mark.asyncio
async def test_apply_motion_blur_linear_uses_length_and_angle_properties() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["apply_motion_blur"](
        blur_type="linear",
        length=24.0,
        angle=37.5,
        layer_name="Speed",
    )

    assert result["success"] is True
    assert result["operation"] == "apply_motion_blur"
    assert result["data"] == {"blur_type": "linear", "length": 24.0, "angle": 37.5}
    generated = generated_source(bridge)
    assert "drawable = image.get_layer_by_name('Speed')" in generated
    assert "df = Gimp.DrawableFilter.new(drawable, 'gegl:motion-blur-linear', '')" in generated
    assert "cfg.set_property('length', 24.0)" in generated
    assert "cfg.set_property('angle', 37.5)" in generated
    assert "drawable.append_filter(df)" in generated
    assert "drawable.merge_filter(df)" in generated
    assert "Gimp.displays_flush()" in generated


@pytest.mark.asyncio
async def test_apply_motion_blur_zoom_uses_center_and_factor_properties() -> None:
    bridge = ScriptedBridge()
    tools = registered_tools(bridge)

    result = await tools["apply_motion_blur"](
        blur_type="zoom",
        center_x=120.0,
        center_y=80.0,
        factor=0.42,
        layer_index=0,
    )

    assert result["success"] is True
    assert result["operation"] == "apply_motion_blur"
    assert result["data"] == {
        "blur_type": "zoom",
        "center_x": 120.0,
        "center_y": 80.0,
        "factor": 0.42,
    }
    generated = generated_source(bridge)
    assert "drawable = layers[0]" in generated
    assert "df = Gimp.DrawableFilter.new(drawable, 'gegl:motion-blur-zoom', '')" in generated
    assert "cfg.set_property('center-x', 120.0)" in generated
    assert "cfg.set_property('center-y', 80.0)" in generated
    assert "cfg.set_property('factor', 0.42)" in generated
    assert "Gimp.displays_flush()" in generated
