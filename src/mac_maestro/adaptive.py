from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .invariants import InvariantReport
from .models import ClickAction, UIAction
from .replay import TraceDiff


class PlannerAdapter(Protocol):
    def propose(
        self,
        intent: str,
        *,
        previous_actions: list[UIAction],
        feedback: dict[str, Any],
    ) -> list[UIAction]: ...


@dataclass(frozen=True)
class AdaptiveDecision:
    retry: bool
    reason: str
    actions: list[UIAction]
    feedback: dict[str, Any]


@dataclass
class ConservativeAdapter:
    """Small deterministic adapter for known safe recovery cases."""

    fallback_titles: dict[str, str] = field(
        default_factory=lambda: {
            "save": "Save",
            "confirm": "OK",
            "cancel": "Cancel",
            "close": "Close",
        }
    )

    def propose(
        self,
        intent: str,
        *,
        previous_actions: list[UIAction],
        feedback: dict[str, Any],
    ) -> list[UIAction]:
        normalized = intent.lower()
        for key, title in self.fallback_titles.items():
            if key in normalized:
                return [ClickAction(role="AXButton", title=title)]
        return list(previous_actions)


@dataclass
class AdaptiveOmega:
    """Turns diff + invariant feedback into a bounded planner retry decision."""

    adapter: PlannerAdapter = field(default_factory=ConservativeAdapter)
    max_retries: int = 1

    def decide(
        self,
        *,
        intent: str,
        previous_actions: list[UIAction],
        diff: TraceDiff,
        invariants: InvariantReport,
        attempt: int = 0,
    ) -> AdaptiveDecision:
        feedback = {
            "diff": diff.to_dict(),
            "invariants": invariants.to_dict(),
            "attempt": attempt,
        }
        if attempt >= self.max_retries:
            return AdaptiveDecision(
                retry=False,
                reason="retry_budget_exhausted",
                actions=previous_actions,
                feedback=feedback,
            )
        if invariants.ok and diff.severity in {"none", "low"}:
            return AdaptiveDecision(
                retry=False,
                reason="accepted",
                actions=previous_actions,
                feedback=feedback,
            )
        next_actions = self.adapter.propose(
            intent,
            previous_actions=previous_actions,
            feedback=feedback,
        )
        return AdaptiveDecision(
            retry=True,
            reason="adaptive_retry",
            actions=next_actions,
            feedback=feedback,
        )
