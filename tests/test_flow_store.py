from __future__ import annotations

import json

import pytest

from gimp_mcp_pro.flows.models import FlowDefinition, content_hash
from gimp_mcp_pro.flows.store import FlowStore
from tests.test_flow_models import flow_payload


def test_store_round_trips_and_lists_flows(tmp_path) -> None:
    store = FlowStore(tmp_path)
    flow = FlowDefinition.model_validate(flow_payload())

    store.save(flow)

    assert store.get(flow.id) == flow
    assert [item.id for item in store.list()] == [flow.id]
    assert json.loads((tmp_path / f"{flow.id}.flow.json").read_text())["title"] == flow.title


def test_store_lifecycle_and_pinning(tmp_path) -> None:
    store = FlowStore(tmp_path)
    store.save(FlowDefinition.model_validate(flow_payload()))

    validated = store.set_state("prepare-product-image", "validated")
    active = store.set_state(validated.id, "active")
    pinned = store.set_pinned(active.id, True)

    assert pinned.state == "active"
    assert pinned.ui.pinned is True


def test_store_rejects_activation_before_validation(tmp_path) -> None:
    store = FlowStore(tmp_path)
    store.save(FlowDefinition.model_validate(flow_payload()))

    with pytest.raises(ValueError, match="validated"):
        store.set_state("prepare-product-image", "active")


def test_store_invalidates_trust_when_executable_content_changes(tmp_path) -> None:
    store = FlowStore(tmp_path)
    flow = FlowDefinition.model_validate(flow_payload())
    flow.trusted_hash = content_hash(flow)
    store.save(flow)

    flow.phases[0].steps[0].arguments["width"] = 800
    saved = store.save(flow)

    assert saved.trusted_hash is None


def test_store_rejects_missing_flow(tmp_path) -> None:
    with pytest.raises(KeyError, match="missing"):
        FlowStore(tmp_path).get("missing")
