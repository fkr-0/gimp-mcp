"""TDD coverage for remaining features declared in features.yml."""

from __future__ import annotations

import pytest

from gimp_mcp_pro.tools.roadmap_tools import register_roadmap_tools
from tests.roadmap_tool_cases import ROADMAP_TOOL_CASES
from tests.test_tool_generated_code_paths import CaptureMCP, ScriptedBridge


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(ROADMAP_TOOL_CASES))
async def test_missing_roadmap_tool_generates_bounded_gimp_code(tool_name: str) -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_roadmap_tools(mcp, bridge)

    case = ROADMAP_TOOL_CASES[tool_name]
    result = await mcp.tools[tool_name](**case["kwargs"])

    assert result["success"] is True
    assert result["operation"] == tool_name
    assert bridge.calls, f"{tool_name} should call the bridge"
    generated = "\n".join(bridge.calls[-1][1])
    assert case["marker"] in generated
    assert "json.dumps" in generated


@pytest.mark.asyncio
async def test_safe_python_eval_is_disabled_by_default_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_roadmap_tools(mcp, bridge)

    result = await mcp.tools["safe_python_eval"]("1 + 1")

    assert result["success"] is False
    assert "disabled" in result["error"].lower()
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_batch_export_variants_rejects_unsupported_format_before_bridge_call() -> None:
    mcp = CaptureMCP()
    bridge = ScriptedBridge()
    register_roadmap_tools(mcp, bridge)

    result = await mcp.tools["batch_export_variants"](
        variants=[{"format": "exe", "width": 64, "height": 64}],
        base_path="/tmp/gimp-mcp-variant",
    )

    assert result["success"] is False
    assert "unsupported" in result["error"].lower()
    assert bridge.calls == []
