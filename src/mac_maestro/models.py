from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KeyModifier(StrEnum):
    COMMAND = "command"
    SHIFT = "shift"
    OPTION = "option"
    CONTROL = "control"


class AXNodeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    role: str
    subrole: str | None = None
    title: str | None = None
    description: str | None = None
    value: str | None = None
    enabled: bool = True
    visible: bool = True
    focused: bool = False
    children: list[AXNodeSnapshot] = Field(default_factory=list)


class ElementSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = None
    subrole: str | None = None
    title: str | None = None
    description: str | None = None
    value: str | None = None
    contains_text: str | None = None
    enabled: bool | None = True
    visible: bool | None = True


class ElementMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    node: AXNodeSnapshot


class ClickAction(ElementSelector):
    kind: Literal["click"] = "click"


class DoubleClickAction(ElementSelector):
    kind: Literal["double_click"] = "double_click"


class RightClickAction(ElementSelector):
    kind: Literal["right_click"] = "right_click"


class HoverAction(ElementSelector):
    kind: Literal["hover"] = "hover"


class ScrollAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["scroll"] = "scroll"
    direction: Literal["up", "down", "left", "right"] = "down"
    amount: int = 3
    target: ElementSelector | None = None


class TypeAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["type"] = "type"
    text: str
    clear_first: bool = False
    target: ElementSelector | None = None


class PressAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["press"] = "press"
    key_code: int
    modifiers: list[KeyModifier] = Field(default_factory=list)


UIAction = (
    ClickAction
    | DoubleClickAction
    | RightClickAction
    | HoverAction
    | ScrollAction
    | TypeAction
    | PressAction
)


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: Literal[
        "snapshot",
        "match",
        "safety",
        "execute",
        "result",
        "error",
    ]
    action_index: int
    action_kind: str
    message: str
    payload: dict = Field(default_factory=dict)


class RunTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    dry_run: bool = False
    error: str | None = None
    events: list[TraceEvent] = Field(default_factory=list)
    candidates: list[ElementMatch] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_ndjson(self) -> str:
        """Emit one JSON line per event for streaming / log ingestion."""
        import json

        lines: list[str] = []
        # Header line with trace metadata
        lines.append(
            json.dumps(
                {
                    "type": "trace_start",
                    "ok": self.ok,
                    "dry_run": self.dry_run,
                    "error": self.error,
                }
            )
        )
        for event in self.events:
            lines.append(json.dumps(event.model_dump(mode="json")))
        lines.append(json.dumps({"type": "trace_end", "ok": self.ok}))
        return "\n".join(lines)



def walk_nodes(root: AXNodeSnapshot) -> Sequence[AXNodeSnapshot]:
    result: list[AXNodeSnapshot] = []

    def _walk(node: AXNodeSnapshot) -> None:
        result.append(node)
        for child in node.children:
            _walk(child)

    _walk(root)
    return result


AXNodeSnapshot.model_rebuild()
