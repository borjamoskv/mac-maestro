from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .models import ClickAction, ElementMatch, PressAction, RunTrace, TraceEvent, TypeAction, UIAction
from .runtime import MacMaestro

DriftSeverity = Literal["none", "low", "medium", "high", "critical"]


class ReplayError(Exception):
    """Raised when a trace envelope cannot be replayed safely."""


@dataclass(frozen=True)
class DriftFinding:
    severity: DriftSeverity
    code: str
    message: str
    original: Any = None
    replayed: Any = None


@dataclass(frozen=True)
class TraceDiff:
    ok: bool
    severity: DriftSeverity
    findings: list[DriftFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "severity": self.severity,
            "findings": [
                {
                    "severity": finding.severity,
                    "code": finding.code,
                    "message": finding.message,
                    "original": finding.original,
                    "replayed": finding.replayed,
                }
                for finding in self.findings
            ],
        }


@dataclass(frozen=True)
class ReplayResult:
    original_ok: bool
    replay_ok: bool
    diff: TraceDiff
    trace: RunTrace

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_ok": self.original_ok,
            "replay_ok": self.replay_ok,
            "diff": self.diff.to_dict(),
            "trace": self.trace.model_dump(mode="json"),
        }


class ReplayEngine:
    """Replay MoskvBot trace envelopes against the current UI backend."""

    def __init__(self, maestro: MacMaestro) -> None:
        self.maestro = maestro

    def replay(self, envelope: dict[str, Any], *, dry_run: bool = True) -> ReplayResult:
        original_trace = _extract_trace(envelope)
        actions = _deserialize_actions(envelope)
        replay_trace = self.maestro.run(actions, dry_run=dry_run)
        diff = TraceDiffEngine().compare(original_trace, replay_trace)
        return ReplayResult(
            original_ok=original_trace.ok,
            replay_ok=replay_trace.ok,
            diff=diff,
            trace=replay_trace,
        )


class TraceDiffEngine:
    """Forensic comparison between original and replayed RunTrace objects.

    The engine is intentionally structural, not fuzzy. It reports exact drift in:
    - run status,
    - event count and phase sequence,
    - matched element identity,
    - confidence score,
    - candidate set.
    """

    def compare(self, original: RunTrace, replayed: RunTrace) -> TraceDiff:
        findings: list[DriftFinding] = []
        findings.extend(self._compare_status(original, replayed))
        findings.extend(self._compare_events(original.events, replayed.events))
        findings.extend(self._compare_candidates(original.candidates, replayed.candidates))
        severity = _max_severity(findings)
        return TraceDiff(ok=severity in {"none", "low"}, severity=severity, findings=findings)

    def _compare_status(self, original: RunTrace, replayed: RunTrace) -> list[DriftFinding]:
        findings: list[DriftFinding] = []
        if original.ok != replayed.ok:
            findings.append(
                DriftFinding(
                    severity="critical",
                    code="ok_mismatch",
                    message="Original and replay status differ.",
                    original=original.ok,
                    replayed=replayed.ok,
                )
            )
        if original.error != replayed.error:
            findings.append(
                DriftFinding(
                    severity="high" if original.error or replayed.error else "low",
                    code="error_mismatch",
                    message="Original and replay error differ.",
                    original=original.error,
                    replayed=replayed.error,
                )
            )
        return findings

    def _compare_events(
        self, original_events: list[TraceEvent], replayed_events: list[TraceEvent]
    ) -> list[DriftFinding]:
        findings: list[DriftFinding] = []
        if len(original_events) != len(replayed_events):
            findings.append(
                DriftFinding(
                    severity="medium",
                    code="event_count_delta",
                    message="Original and replay event counts differ.",
                    original=len(original_events),
                    replayed=len(replayed_events),
                )
            )

        for idx, (original, replayed) in enumerate(zip(original_events, replayed_events, strict=False)):
            findings.extend(self._compare_event(idx, original, replayed))
        return findings

    def _compare_event(
        self, idx: int, original: TraceEvent, replayed: TraceEvent
    ) -> list[DriftFinding]:
        findings: list[DriftFinding] = []
        if original.phase != replayed.phase:
            findings.append(
                DriftFinding(
                    severity="high",
                    code="phase_mismatch",
                    message=f"Event {idx} phase differs.",
                    original=original.phase,
                    replayed=replayed.phase,
                )
            )
        if original.action_kind != replayed.action_kind:
            findings.append(
                DriftFinding(
                    severity="high",
                    code="action_kind_mismatch",
                    message=f"Event {idx} action kind differs.",
                    original=original.action_kind,
                    replayed=replayed.action_kind,
                )
            )
        findings.extend(_compare_match_payload(idx, original.payload, replayed.payload))
        return findings

    def _compare_candidates(
        self, original: list[ElementMatch], replayed: list[ElementMatch]
    ) -> list[DriftFinding]:
        if len(original) == len(replayed):
            return []
        return [
            DriftFinding(
                severity="low",
                code="candidate_count_delta",
                message="Original and replay candidate counts differ.",
                original=len(original),
                replayed=len(replayed),
            )
        ]


def _extract_trace(envelope: dict[str, Any]) -> RunTrace:
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ReplayError("Invalid envelope: missing payload object")
    raw_trace = payload.get("trace")
    if not isinstance(raw_trace, dict):
        raise ReplayError("Invalid envelope: missing payload.trace object")
    return RunTrace(**raw_trace)


def _deserialize_actions(envelope: dict[str, Any]) -> list[UIAction]:
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ReplayError("Invalid envelope: missing payload object")
    raw_actions = payload.get("actions")
    if not isinstance(raw_actions, list):
        raise ReplayError("Invalid envelope: missing payload.actions list")

    actions: list[UIAction] = []
    for raw in raw_actions:
        if not isinstance(raw, dict):
            raise ReplayError("Invalid action: expected object")
        kind = raw.get("kind")
        if kind == "click":
            actions.append(ClickAction(**raw))
        elif kind == "type":
            actions.append(TypeAction(**raw))
        elif kind == "press":
            actions.append(PressAction(**raw))
        else:
            raise ReplayError(f"Unknown action kind: {kind!r}")
    return actions


def _compare_match_payload(
    idx: int, original: dict[str, Any], replayed: dict[str, Any]
) -> list[DriftFinding]:
    findings: list[DriftFinding] = []

    original_element = original.get("element_id")
    replayed_element = replayed.get("element_id")
    if original_element and replayed_element and original_element != replayed_element:
        findings.append(
            DriftFinding(
                severity="critical",
                code="matched_element_drift",
                message=f"Event {idx} matched a different element.",
                original=original_element,
                replayed=replayed_element,
            )
        )

    original_confidence = original.get("confidence")
    replayed_confidence = replayed.get("confidence")
    if isinstance(original_confidence, int | float) and isinstance(replayed_confidence, int | float):
        delta = abs(float(original_confidence) - float(replayed_confidence))
        if delta >= 0.2:
            findings.append(
                DriftFinding(
                    severity="high",
                    code="confidence_drift_high",
                    message=f"Event {idx} confidence changed materially.",
                    original=original_confidence,
                    replayed=replayed_confidence,
                )
            )
        elif delta >= 0.05:
            findings.append(
                DriftFinding(
                    severity="low",
                    code="confidence_drift_low",
                    message=f"Event {idx} confidence changed slightly.",
                    original=original_confidence,
                    replayed=replayed_confidence,
                )
            )
    return findings


def _max_severity(findings: list[DriftFinding]) -> DriftSeverity:
    if not findings:
        return "none"
    order: dict[DriftSeverity, int] = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    return max((finding.severity for finding in findings), key=lambda item: order[item])
