"""Atomic JSON persistence for user-local repeatable flows."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from gimp_mcp_pro.flows.models import FlowDefinition, content_hash


def default_flow_dir() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "gimp-mcp-pro" / "flows"


class FlowStore:
    """Load and atomically persist flow definition files."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_flow_dir()

    def path_for(self, flow_id: str) -> Path:
        return self.root / f"{flow_id}.flow.json"

    def save(self, flow: FlowDefinition) -> FlowDefinition:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(flow.id)
        if path.exists():
            previous = self.get(flow.id)
            if content_hash(previous) != content_hash(flow):
                flow.trusted_hash = None
        data = json.dumps(flow.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.root, prefix=f".{flow.id}.", delete=False
        ) as handle:
            handle.write(data)
            temporary = Path(handle.name)
        temporary.replace(path)
        return flow

    def get(self, flow_id: str) -> FlowDefinition:
        path = self.path_for(flow_id)
        if not path.exists():
            raise KeyError(f"flow not found: {flow_id}")
        return FlowDefinition.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[FlowDefinition]:
        if not self.root.exists():
            return []
        return [
            FlowDefinition.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.root.glob("*.flow.json"))
        ]

    def set_state(
        self, flow_id: str, state: Literal["draft", "validated", "active"]
    ) -> FlowDefinition:
        flow = self.get(flow_id)
        if state == "active" and flow.state not in {"validated", "active"}:
            raise ValueError("flow must be validated before activation")
        flow.state = state
        return self.save(flow)

    def set_pinned(self, flow_id: str, pinned: bool) -> FlowDefinition:
        flow = self.get(flow_id)
        if pinned and flow.state != "active":
            raise ValueError("only active flows can be pinned")
        flow.ui.pinned = pinned
        return self.save(flow)
