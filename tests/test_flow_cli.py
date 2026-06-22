from __future__ import annotations

import json

import gimp_mcp_pro.cli as cli
from gimp_mcp_pro.flows.models import FlowDefinition
from gimp_mcp_pro.flows.operations import OperationRegistry
from gimp_mcp_pro.flows.store import FlowStore
from tests.test_flow_models import flow_payload


def seed_flow(tmp_path, *, state: str = "validated") -> FlowStore:
    store = FlowStore(tmp_path)
    payload = flow_payload()
    payload["state"] = state
    store.save(FlowDefinition.model_validate(payload))
    return store


def test_flow_list_and_show_emit_json(tmp_path, capsys) -> None:
    seed_flow(tmp_path)

    assert cli.main(["flow", "--flow-dir", str(tmp_path), "list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["id"] == "prepare-product-image"

    assert cli.main(["flow", "--flow-dir", str(tmp_path), "show", "prepare-product-image"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["title"] == "Prepare Product Image"


def test_flow_validate_reports_unknown_tool(tmp_path, capsys) -> None:
    payload = flow_payload()
    payload["phases"][0]["steps"][0]["tool"] = "missing"  # type: ignore[index]
    FlowStore(tmp_path).save(FlowDefinition.model_validate(payload))

    assert cli.main(["flow", "--flow-dir", str(tmp_path), "validate", "prepare-product-image"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert "missing" in result["errors"][0]


def test_flow_run_executes_with_json_parameters(tmp_path, capsys, monkeypatch) -> None:
    seed_flow(tmp_path)
    registry = OperationRegistry()

    @registry.tool()
    async def scale_image(width: int, height: int) -> dict[str, object]:
        return {"success": True, "width": width, "height": height}

    @registry.tool()
    async def apply_unsharp_mask() -> dict[str, object]:
        return {"success": True}

    monkeypatch.setattr(cli, "build_operation_registry", lambda _bridge: registry)

    result = cli.main(
        [
            "flow",
            "--flow-dir",
            str(tmp_path),
            "run",
            "prepare-product-image",
            "--params-json",
            '{"width": 640, "image": 1, "sharpen": false}',
        ]
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["steps"][0]["arguments"]["width"] == 640


def test_flow_run_rejects_invalid_params_json(tmp_path, capsys) -> None:
    seed_flow(tmp_path)

    assert (
        cli.main(
            [
                "flow",
                "--flow-dir",
                str(tmp_path),
                "run",
                "prepare-product-image",
                "--params-json",
                "not-json",
            ]
        )
        == 2
    )
    assert "invalid params JSON" in capsys.readouterr().err
