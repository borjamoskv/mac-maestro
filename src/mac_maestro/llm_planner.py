from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .invariants import InvariantEngine
from .models import ClickAction, ElementSelector, KeyModifier, PressAction, TypeAction, UIAction


class LLMClient(Protocol):
    """Small provider-neutral interface for model-backed planning."""

    def complete_json(self, prompt: str) -> dict[str, Any]: ...


class PlannedClick(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = "click"
    role: str | None = None
    title: str | None = None
    description: str | None = None
    value: str | None = None
    contains_text: str | None = None


class PlannedType(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = "type"
    text: str
    clear_first: bool = False
    target: ElementSelector | None = None


class PlannedPress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = "press"
    key_code: int
    modifiers: list[KeyModifier] = Field(default_factory=list)


class LLMPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rationale: str = Field(max_length=500)
    actions: list[PlannedClick | PlannedType | PlannedPress] = Field(min_length=1, max_length=8)


class LLMPlannerError(Exception):
    """Raised when an LLM proposal fails schema or invariant gates."""


@dataclass
class GatedLLMPlanner:
    """LLM-backed planner with deterministic gates.

    The model only proposes a bounded JSON plan. The adapter validates schema,
    converts to typed UIAction objects, and runs invariants before returning.
    """

    client: LLMClient
    invariant_engine: InvariantEngine | None = None
    max_actions: int = 8

    def plan(self, intent: str, *, ui_context: dict[str, Any] | None = None) -> list[UIAction]:
        prompt = self._prompt(intent=intent, ui_context=ui_context or {})
        raw = self.client.complete_json(prompt)
        actions = self._parse(raw)
        invariants = self.invariant_engine or InvariantEngine.default()
        report = invariants.evaluate(actions=actions)
        if not report.ok:
            raise LLMPlannerError(json.dumps(report.to_dict(), sort_keys=True))
        return actions

    def _parse(self, raw: dict[str, Any]) -> list[UIAction]:
        try:
            plan = LLMPlan(**raw)
        except ValidationError as exc:
            raise LLMPlannerError(str(exc)) from exc
        if len(plan.actions) > self.max_actions:
            raise LLMPlannerError(f"Plan exceeds max_actions={self.max_actions}")
        typed: list[UIAction] = []
        for item in plan.actions:
            payload = item.model_dump(exclude_none=True)
            kind = payload.pop("kind")
            if kind == "click":
                typed.append(ClickAction(**payload))
            elif kind == "type":
                typed.append(TypeAction(**payload))
            elif kind == "press":
                typed.append(PressAction(**payload))
            else:
                raise LLMPlannerError(f"Unknown action kind: {kind!r}")
        return typed

    def _prompt(self, *, intent: str, ui_context: dict[str, Any]) -> str:
        allowed = {
            "click": ["role", "title", "description", "value", "contains_text"],
            "type": ["text", "clear_first", "target"],
            "press": ["key_code", "modifiers"],
        }
        return json.dumps(
            {
                "task": "Propose a bounded macOS Accessibility action plan as JSON only.",
                "intent": intent,
                "ui_context": ui_context,
                "allowed_schema": allowed,
                "output_schema": {
                    "rationale": "short non-sensitive reason",
                    "actions": [
                        {
                            "kind": "click|type|press",
                            "role": "optional AX role",
                            "title": "optional AX title",
                        }
                    ],
                },
                "constraints": [
                    "Return JSON only.",
                    "Do not include shell commands or code execution.",
                    "Do not propose destructive UI actions.",
                    "Use semantic selectors instead of screen coordinates.",
                    "Maximum actions are bounded by the caller.",
                ],
            },
            sort_keys=True,
        )
