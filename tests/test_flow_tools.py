from __future__ import annotations

from typing import Any

import pytest

from gimp_mcp_pro.flows.operations import OperationRegistry
from gimp_mcp_pro.flows.store import FlowStore
from gimp_mcp_pro.tools.flow_tools import register_flow_tools
from tests.test_flow_models import flow_payload


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func

        return decorator


def registry_factory(_bridge: Any) -> OperationRegistry:
    registry = OperationRegistry()

    @registry.tool()
    async def scale_image(width: int, height: int) -> dict[str, object]:
        return {"status": "success", "data": {"width": width, "height": height}}

    @registry.tool()
    async def apply_unsharp_mask() -> dict[str, object]:
        return {"status": "success"}

    return registry


@pytest.mark.asyncio
async def test_flow_management_lifecycle(tmp_path) -> None:
    mcp = FakeMCP()
    store = FlowStore(tmp_path)
    register_flow_tools(mcp, object(), store=store, registry_factory=registry_factory)

    proposed = await mcp.tools["propose_flow"](flow_payload())
    assert proposed["success"] is True
    assert store.get("prepare-product-image").state == "draft"

    listed = await mcp.tools["list_flows"]()
    assert listed["data"]["flows"][0]["id"] == "prepare-product-image"
    shown = await mcp.tools["get_flow"]("prepare-product-image")
    assert shown["data"]["flow"]["title"] == "Prepare Product Image"

    validated = await mcp.tools["validate_flow"]("prepare-product-image")
    assert validated["data"]["valid"] is True
    assert store.get("prepare-product-image").state == "validated"

    activated = await mcp.tools["activate_flow"]("prepare-product-image")
    assert activated["success"] is True
    pinned = await mcp.tools["pin_flow"]("prepare-product-image")
    assert pinned["data"]["flow"]["ui"]["pinned"] is True

    unpinned = await mcp.tools["unpin_flow"]("prepare-product-image")
    assert unpinned["data"]["flow"]["ui"]["pinned"] is False
    deactivated = await mcp.tools["deactivate_flow"]("prepare-product-image")
    assert deactivated["data"]["flow"]["state"] == "validated"


@pytest.mark.asyncio
async def test_proposal_forces_draft_and_run_executes_validated_flow(tmp_path) -> None:
    mcp = FakeMCP()
    store = FlowStore(tmp_path)
    register_flow_tools(mcp, object(), store=store, registry_factory=registry_factory)
    payload = flow_payload()
    payload["state"] = "active"
    payload["ui"] = {"pinned": True}

    await mcp.tools["propose_flow"](payload)
    assert store.get("prepare-product-image").state == "draft"
    await mcp.tools["validate_flow"]("prepare-product-image")
    result = await mcp.tools["run_flow"](
        "prepare-product-image", {"width": 800, "image": 1, "sharpen": False}
    )

    assert result["success"] is True
    assert result["data"]["run"]["steps"][0]["arguments"]["width"] == 800


@pytest.mark.asyncio
async def test_validate_flow_reports_unknown_operation(tmp_path) -> None:
    mcp = FakeMCP()
    store = FlowStore(tmp_path)
    register_flow_tools(mcp, object(), store=store, registry_factory=registry_factory)
    payload = flow_payload()
    payload["phases"][0]["steps"][0]["tool"] = "missing_tool"  # type: ignore[index]
    await mcp.tools["propose_flow"](payload)

    result = await mcp.tools["validate_flow"]("prepare-product-image")

    assert result["success"] is False
    assert "missing_tool" in result["error"]
