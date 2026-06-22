from __future__ import annotations

import pytest
from pydantic import ValidationError

from gimp_mcp_pro.flows.models import FlowDefinition, content_hash, infer_capabilities


def flow_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "prepare-product-image",
        "title": "Prepare Product Image",
        "parameters": [
            {"name": "width", "type": "integer", "default": 1600, "minimum": 1},
            {"name": "image", "type": "image", "required": True},
            {"name": "sharpen", "type": "boolean", "default": True},
        ],
        "phases": [
            {
                "id": "edit",
                "steps": [
                    {
                        "tool": "scale_image",
                        "arguments": {"width": "${width}", "height": 900},
                    },
                    {
                        "tool": "apply_unsharp_mask",
                        "arguments": {},
                        "when": "${sharpen}",
                    },
                ],
            }
        ],
    }


def test_flow_definition_validates_references_and_defaults() -> None:
    flow = FlowDefinition.model_validate(flow_payload())

    assert flow.state == "draft"
    assert flow.review_policy == "final"
    assert flow.parameters[1].type == "image"
    assert flow.ui.pinned is False


def test_flow_definition_rejects_unknown_parameter_reference() -> None:
    payload = flow_payload()
    payload["phases"][0]["steps"][0]["arguments"]["width"] = "${missing}"  # type: ignore[index]

    with pytest.raises(ValidationError, match="missing"):
        FlowDefinition.model_validate(payload)


@pytest.mark.parametrize("flow_id", ["../escape", "Has Spaces", "", "a/b"])
def test_flow_definition_rejects_unsafe_ids(flow_id: str) -> None:
    payload = flow_payload()
    payload["id"] = flow_id

    with pytest.raises(ValidationError):
        FlowDefinition.model_validate(payload)


def test_capability_inference_marks_arbitrary_code_pdb_and_filesystem() -> None:
    payload = flow_payload()
    payload["phases"][0]["steps"].extend(  # type: ignore[index]
        [
            {"tool": "execute_python", "arguments": {"code": ["print('x')"]}},
            {"tool": "search_pdb", "arguments": {"query": "blur"}},
            {"tool": "export_image", "arguments": {"path": "/tmp/out.png"}},
        ]
    )
    flow = FlowDefinition.model_validate(payload)

    assert infer_capabilities(flow) == {"arbitrary-code", "filesystem-write", "pdb"}


def test_content_hash_ignores_lifecycle_pin_and_trust_but_tracks_steps() -> None:
    flow = FlowDefinition.model_validate(flow_payload())
    original = content_hash(flow)
    flow.state = "active"
    flow.ui.pinned = True
    flow.trusted_hash = original

    assert content_hash(flow) == original

    flow.phases[0].steps[0].arguments["width"] = 800
    assert content_hash(flow) != original
