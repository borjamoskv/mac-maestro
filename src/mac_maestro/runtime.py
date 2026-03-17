from __future__ import annotations

from typing import Literal

from .backends.protocol import BackendProtocol
from .errors import ConfidenceBelowThresholdError, MacMaestroError
from .matcher import find_best_match, find_all_matches
from .models import ClickAction, ElementMatch, ElementSelector, PressAction, RunTrace, TypeAction, UIAction
from .safety import SafetyPolicy
from .trace import TraceCollector

# Threshold enforcement policies.
ThresholdPolicy = Literal["abort", "fallback_exact", "emit_candidates"]


class MacMaestro:
    def __init__(
        self,
        bundle_id: str,
        backend: BackendProtocol,
        safety_policy: SafetyPolicy | None = None,
        min_confidence: float = 0.0,
        on_below_threshold: ThresholdPolicy = "abort",
    ) -> None:
        self.bundle_id = bundle_id
        self.backend = backend
        self.safety_policy = safety_policy or SafetyPolicy()
        self.min_confidence = min_confidence
        self.on_below_threshold: ThresholdPolicy = on_below_threshold

    def run(
        self,
        actions: list[UIAction],
        *,
        dry_run: bool = False,
    ) -> RunTrace:
        """Execute a sequence of UI actions.

        Args:
            actions: Actions to perform in order.
            dry_run: If True, resolves and matches elements without mutating the UI.
                     The returned RunTrace will include candidate matches and scores.
        """
        trace = TraceCollector(dry_run=dry_run)
        action_kind = "unknown"
        idx = 0

        try:
            for idx, action in enumerate(actions):
                action_kind = getattr(action, "kind", action.__class__.__name__)

                root = self.backend.snapshot(self.bundle_id)
                trace.set_snapshot(root)
                trace.add(
                    phase="snapshot",
                    action_index=idx,
                    action_kind=action_kind,
                    message="Snapshot captured",
                    payload={"bundle_id": self.bundle_id},
                )

                self.safety_policy.validate(action)
                trace.add(
                    phase="safety",
                    action_index=idx,
                    action_kind=action_kind,
                    message="Safety check passed",
                )

                match action:
                    case ClickAction():
                        selector = ElementSelector(**action.model_dump(exclude={"kind"}))
                        matched = self._resolve_match(selector, idx, action_kind, trace)

                        trace.add(
                            phase="match",
                            action_index=idx,
                            action_kind=action_kind,
                            message="Element matched",
                            payload={
                                **matched.model_dump(mode="json"),
                                "dry_run": dry_run,
                            },
                        )

                        if not dry_run:
                            self.backend.click(matched)
                            trace.add(
                                phase="execute",
                                action_index=idx,
                                action_kind=action_kind,
                                message="Click executed",
                                payload={"element_id": matched.element_id},
                            )
                        else:
                            trace.add(
                                phase="execute",
                                action_index=idx,
                                action_kind=action_kind,
                                message="[dry_run] Click skipped — UI not mutated",
                                payload={"element_id": matched.element_id},
                            )

                    case TypeAction():
                        matched = None
                        if action.target is not None:
                            matched = self._resolve_match(action.target, idx, action_kind, trace)
                            trace.add(
                                phase="match",
                                action_index=idx,
                                action_kind=action_kind,
                                message="Type target matched",
                                payload={
                                    **matched.model_dump(mode="json"),
                                    "dry_run": dry_run,
                                },
                            )

                        if not dry_run:
                            self.backend.type_text(action, matched)
                            trace.add(
                                phase="execute",
                                action_index=idx,
                                action_kind=action_kind,
                                message="Type executed",
                                payload={"chars": len(action.text)},
                            )
                        else:
                            trace.add(
                                phase="execute",
                                action_index=idx,
                                action_kind=action_kind,
                                message="[dry_run] Type skipped — UI not mutated",
                                payload={"chars": len(action.text)},
                            )

                    case PressAction():
                        if not dry_run:
                            self.backend.press(action)
                            trace.add(
                                phase="execute",
                                action_index=idx,
                                action_kind=action_kind,
                                message="Key press executed",
                                payload={
                                    "key_code": action.key_code,
                                    "modifiers": [m.value for m in action.modifiers],
                                },
                            )
                        else:
                            trace.add(
                                phase="execute",
                                action_index=idx,
                                action_kind=action_kind,
                                message="[dry_run] Key press skipped — UI not mutated",
                                payload={
                                    "key_code": action.key_code,
                                    "modifiers": [m.value for m in action.modifiers],
                                },
                            )

                trace.add(
                    phase="result",
                    action_index=idx,
                    action_kind=action_kind,
                    message="Action completed",
                )

            return trace.success()

        except MacMaestroError as exc:
            trace.add(
                phase="error",
                action_index=idx,
                action_kind=action_kind,
                message=str(exc),
            )
            return trace.failure(error=str(exc))

    # -------------------------------------------------------------------------
    # Internal: semantic match with threshold enforcement
    # -------------------------------------------------------------------------

    def _resolve_match(
        self,
        selector: ElementSelector,
        idx: int,
        action_kind: str,
        trace: TraceCollector,
    ) -> ElementMatch:
        """Find best match; enforce min_confidence; apply on_below_threshold policy."""
        matched = find_best_match(root=trace.last_snapshot, selector=selector)
        all_candidates = _safe_find_all(trace.last_snapshot, selector)

        if self.min_confidence > 0.0 and matched.confidence < self.min_confidence:
            trace.add(
                phase="match",
                action_index=idx,
                action_kind=action_kind,
                message=(
                    f"Confidence {matched.confidence:.2f} below threshold "
                    f"{self.min_confidence:.2f} — applying policy '{self.on_below_threshold}'"
                ),
                payload={
                    "score": matched.confidence,
                    "threshold": self.min_confidence,
                    "policy": self.on_below_threshold,
                    "candidates": [c.model_dump(mode="json") for c in all_candidates],
                },
            )

            if self.on_below_threshold == "abort":
                raise ConfidenceBelowThresholdError(
                    score=matched.confidence,
                    threshold=self.min_confidence,
                    candidates=all_candidates,
                )

            if self.on_below_threshold == "emit_candidates":
                # Callers can inspect trace.candidates for the full set.
                trace.record_candidates(all_candidates)
                # Return best available without aborting — caller opts in to this risk.
                return matched

            # fallback_exact: attempt exact-only resolution (title/role exact match).
            exact = _try_exact_match(all_candidates)
            if exact is not None:
                return exact
            raise ConfidenceBelowThresholdError(
                score=matched.confidence,
                threshold=self.min_confidence,
                candidates=all_candidates,
            )

        return matched


def _safe_find_all(root: object, selector: ElementSelector) -> list[ElementMatch]:
    """Non-raising wrapper around find_all_matches for optional enrichment."""
    try:
        return list(find_all_matches(root, selector))  # type: ignore[arg-type]
    except Exception:
        return []


def _try_exact_match(candidates: list[ElementMatch]) -> ElementMatch | None:
    """Return a candidate where title and role are exact, or None."""
    for candidate in candidates:
        node = candidate.node
        reasons = candidate.reasons
        if any("exact" in r.lower() for r in reasons):
            return candidate
        if node.title and node.role:
            # Heuristic: exact title + role in reasons indicates high-fidelity match.
            if "exact title" in " ".join(reasons).lower():
                return candidate
    return None
