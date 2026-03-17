from __future__ import annotations

from .models import AXNodeSnapshot, ElementMatch, RunTrace, TraceEvent


class TraceCollector:
    def __init__(self, dry_run: bool = False) -> None:
        self._events: list[TraceEvent] = []
        self._dry_run = dry_run
        self._candidates: list[ElementMatch] = []
        self.last_snapshot: AXNodeSnapshot | None = None

    def add(
        self,
        *,
        phase: str,
        action_index: int,
        action_kind: str,
        message: str,
        payload: dict | None = None,
    ) -> None:
        event = TraceEvent(
            phase=phase,  # type: ignore[arg-type]
            action_index=action_index,
            action_kind=action_kind,
            message=message,
            payload=payload or {},
        )
        self._events.append(event)

        # Track the latest snapshot for _resolve_match access.
        if phase == "snapshot" and payload and "bundle_id" in payload:
            pass  # snapshot stored by runtime directly on last_snapshot

    def set_snapshot(self, snapshot: AXNodeSnapshot) -> None:
        """Store the most recent AX snapshot for matcher access."""
        self.last_snapshot = snapshot

    def record_candidates(self, candidates: list[ElementMatch]) -> None:
        """Store candidate set for emit_candidates policy."""
        self._candidates.extend(candidates)

    def success(self) -> RunTrace:
        return RunTrace(
            ok=True,
            dry_run=self._dry_run,
            events=self._events,
            candidates=self._candidates,
        )

    def failure(self, error: str | None = None) -> RunTrace:
        return RunTrace(
            ok=False,
            dry_run=self._dry_run,
            error=error,
            events=self._events,
            candidates=self._candidates,
        )
