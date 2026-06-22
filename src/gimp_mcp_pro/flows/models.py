"""Validated schema for declarative GIMP flows."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

FLOW_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PARAMETER_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

ParameterType = Literal[
    "text",
    "integer",
    "number",
    "boolean",
    "color",
    "choice",
    "image",
    "layer",
    "channel",
    "path",
    "brush",
    "font",
    "palette",
    "gradient",
    "filter",
    "procedure",
    "export-format",
    "rectangle",
    "point",
    "dimensions",
    "opacity",
    "angle",
]


class FlowParameter(BaseModel):
    """One primitive or live GIMP resource parameter."""

    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    type: ParameterType
    description: str = ""
    required: bool = False
    default: Any = None
    choices: list[Any] = Field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None


class FlowStep(BaseModel):
    """One typed MCP operation invocation."""

    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    when: str | None = None


class FlowPhase(BaseModel):
    """A transaction phase containing ordered steps."""

    id: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_-]*$")
    title: str | None = None
    steps: list[FlowStep] = Field(min_length=1)
    checkpoint: bool = False


class FlowUI(BaseModel):
    """GIMP menu presentation metadata."""

    pinned: bool = False
    category: str = "Repeatable Flows"
    order: int = 100


class FlowDefinition(BaseModel):
    """Complete versioned repeatable-flow definition."""

    schema_version: Literal[1] = 1
    id: str = Field(pattern=FLOW_ID_RE.pattern)
    title: str = Field(min_length=1)
    description: str = ""
    author: str = ""
    state: Literal["draft", "validated", "active"] = "draft"
    parameters: list[FlowParameter] = Field(default_factory=list)
    phases: list[FlowPhase] = Field(min_length=1)
    review_policy: Literal["none", "final", "phased"] = "final"
    capabilities: list[str] = Field(default_factory=list)
    ui: FlowUI = Field(default_factory=FlowUI)
    trusted_hash: str | None = None

    @model_validator(mode="after")
    def validate_parameter_references(self) -> FlowDefinition:
        names = [parameter.name for parameter in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("parameter names must be unique")
        known = set(names)
        referenced: set[str] = set()
        for phase in self.phases:
            for step in phase.steps:
                referenced.update(_references(step.arguments))
                referenced.update(_references(step.when))
        unknown = sorted(referenced - known)
        if unknown:
            raise ValueError(f"unknown parameter reference(s): {', '.join(unknown)}")
        inferred = infer_capabilities(self)
        self.capabilities = sorted(set(self.capabilities) | inferred)
        return self


def _references(value: Any) -> set[str]:
    if isinstance(value, str):
        return set(PARAMETER_REF_RE.findall(value))
    if isinstance(value, dict):
        return {name for item in value.values() for name in _references(item)}
    if isinstance(value, list):
        return {name for item in value for name in _references(item)}
    return set()


def infer_capabilities(flow: FlowDefinition) -> set[str]:
    """Infer visible safety tags from operation names."""
    tools = {step.tool for phase in flow.phases for step in phase.steps}
    capabilities: set[str] = set()
    if "execute_python" in tools:
        capabilities.add("arbitrary-code")
    if any("pdb" in tool for tool in tools):
        capabilities.add("pdb")
    if tools & {"export_image", "save_image", "file_save"}:
        capabilities.add("filesystem-write")
    return capabilities


def content_hash(flow: FlowDefinition) -> str:
    """Hash executable flow content while ignoring lifecycle/UI state."""
    payload = flow.model_dump(mode="json")
    for key in ("state", "trusted_hash"):
        payload.pop(key, None)
    ui = payload.get("ui", {})
    if isinstance(ui, dict):
        ui.pop("pinned", None)
        ui.pop("order", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
