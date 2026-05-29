from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .models import RunTrace, UIAction
from .replay import ReplayResult, TraceDiff

InvariantSeverity = Literal["info", "warning", "error", "critical"]
InvariantTarget = Literal["action", "trace", "diff", "replay"]


@dataclass(frozen=True)
class InvariantViolation:
    name: str
    severity: InvariantSeverity
    target: InvariantTarget
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InvariantReport:
    ok: bool
    violations: list[InvariantViolation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "violations": [
                {
                    "name": violation.name,
                    "severity": violation.severity,
                    "target": violation.target,
                    "message": violation.message,
                    "context": violation.context,
                }
                for violation in self.violations
            ],
        }

    def raise_for_violations(self) -> None:
        if self.ok:
            return
        rendered = "; ".join(
            f"{violation.severity}:{violation.name}: {violation.message}"
            for violation in self.violations
        )
        raise InvariantViolationError(rendered)


class InvariantViolationError(Exception):
    """Raised when one or more critical invariants fail."""


class Invariant:
    """Base class for executable operational invariants."""

    name: str = "invariant"
    severity: InvariantSeverity = "error"
    target: InvariantTarget = "trace"

    def evaluate(
        self,
        *,
        actions: list[UIAction] | None = None,
        trace: RunTrace | None = None,
        diff: TraceDiff | None = None,
        replay: ReplayResult | None = None,
    ) -> list[InvariantViolation]:
        raise NotImplementedError


@dataclass(frozen=True)
class NoDestructiveTitleInvariant(Invariant):
    """Reject actions/events containing destructive UI titles."""

    blocked_terms: tuple[str, ...] = (
        "delete",
        "erase",
        "format",
        "wipe",
        "remove all",
        "destroy",
    )
    name: str = "no_destructive_titles"
    severity: InvariantSeverity = "critical"
    target: InvariantTarget = "action"

    def evaluate(
        self,
        *,
        actions: list[UIAction] | None = None,
        trace: RunTrace | None = None,
        diff: TraceDiff | None = None,
        replay: ReplayResult | None = None,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        for index, action in enumerate(actions or []):
            payload = action.model_dump(mode="json")
            haystack = " ".join(
                str(val).lower() for val in payload.values() if val is not None
            )
            matched = [term for term in self.blocked_terms if term in haystack]
            if matched:
                violations.append(
                    InvariantViolation(
                        name=self.name,
                        severity=self.severity,
                        target=self.target,
                        message="Action contains destructive UI language.",
                        context={"action_index": index, "terms": matched, "action": payload},
                    )
                )
        return violations


@dataclass(frozen=True)
class MinimumConfidenceInvariant(Invariant):
    """Require matched elements to stay above a confidence floor."""

    minimum: float = 0.75
    name: str = "minimum_confidence"
    severity: InvariantSeverity = "error"
    target: InvariantTarget = "trace"

    def evaluate(
        self,
        *,
        actions: list[UIAction] | None = None,
        trace: RunTrace | None = None,
        diff: TraceDiff | None = None,
        replay: ReplayResult | None = None,
    ) -> list[InvariantViolation]:
        if trace is None:
            return []
        violations: list[InvariantViolation] = []
        for index, event in enumerate(trace.events):
            confidence = event.payload.get("confidence")
            if isinstance(confidence, int | float) and float(confidence) < self.minimum:
                violations.append(
                    InvariantViolation(
                        name=self.name,
                        severity=self.severity,
                        target=self.target,
                        message="Matched element confidence below invariant floor.",
                        context={
                            "event_index": index,
                            "confidence": float(confidence),
                            "minimum": self.minimum,
                        },
                    )
                )
        return violations


@dataclass(frozen=True)
class NoCriticalDriftInvariant(Invariant):
    """Reject replay results with high or critical drift."""

    allowed: tuple[str, ...] = ("none", "low")
    name: str = "no_critical_drift"
    severity: InvariantSeverity = "critical"
    target: InvariantTarget = "diff"

    def evaluate(
        self,
        *,
        actions: list[UIAction] | None = None,
        trace: RunTrace | None = None,
        diff: TraceDiff | None = None,
        replay: ReplayResult | None = None,
    ) -> list[InvariantViolation]:
        if diff is None and replay is not None:
            diff = replay.diff
        if diff is None or diff.severity in self.allowed:
            return []
        return [
            InvariantViolation(
                name=self.name,
                severity=self.severity,
                target=self.target,
                message="Replay drift exceeds allowed severity.",
                context=diff.to_dict(),
            )
        ]


@dataclass(frozen=True)
class ReplayMustMatchStatusInvariant(Invariant):
    """Original and replay execution status must agree."""

    name: str = "replay_status_match"
    severity: InvariantSeverity = "critical"
    target: InvariantTarget = "replay"

    def evaluate(
        self,
        *,
        actions: list[UIAction] | None = None,
        trace: RunTrace | None = None,
        diff: TraceDiff | None = None,
        replay: ReplayResult | None = None,
    ) -> list[InvariantViolation]:
        if replay is None or replay.original_ok == replay.replay_ok:
            return []
        return [
            InvariantViolation(
                name=self.name,
                severity=self.severity,
                target=self.target,
                message="Original trace and replay status diverge.",
                context={"original_ok": replay.original_ok, "replay_ok": replay.replay_ok},
            )
        ]


@dataclass
class InvariantEngine:
    invariants: list[Invariant] = field(default_factory=list)

    @classmethod
    def default(cls) -> InvariantEngine:
        return cls(
            invariants=[
                NoDestructiveTitleInvariant(),
                MinimumConfidenceInvariant(),
                NoCriticalDriftInvariant(),
                ReplayMustMatchStatusInvariant(),
            ]
        )

    def evaluate(
        self,
        *,
        actions: list[UIAction] | None = None,
        trace: RunTrace | None = None,
        diff: TraceDiff | None = None,
        replay: ReplayResult | None = None,
    ) -> InvariantReport:
        violations: list[InvariantViolation] = []
        for invariant in self.invariants:
            violations.extend(
                invariant.evaluate(actions=actions, trace=trace, diff=diff, replay=replay)
            )
        blocking = [v for v in violations if v.severity in {"error", "critical"}]
        return InvariantReport(ok=not blocking, violations=violations)
