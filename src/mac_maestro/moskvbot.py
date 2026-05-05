from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import ClickAction, PressAction, RunTrace, TypeAction, UIAction
from .runtime import MacMaestro


class TraceSink(Protocol):
    """Receives sealed MoskvBot trace envelopes."""

    def emit(self, envelope: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class BotGoal:
    """Persistent operator intent handled by MoskvBot."""

    intent: str
    max_steps: int = 1
    dry_run: bool = False


@dataclass(frozen=True)
class GovernorConfig:
    """Small PID-like stability governor for autonomous GUI execution."""

    confidence_floor: float = 0.72
    max_failures: int = 2
    min_dwell_ms: int = 250
    strict_after_failure: bool = True


@dataclass
class GovernorState:
    failures: int = 0
    last_step_ms: int = 0
    strict_mode: bool = False


class MoskvPlanner:
    """Deterministic intent -> action planner.

    This is intentionally small and auditable. Production callers can pass their
    own planner callable when they need LLM planning, retrieval, or app-specific
    workflows.
    """

    def __init__(self, routes: dict[str, list[UIAction]] | None = None) -> None:
        self.routes = routes or _default_routes()

    def plan(self, intent: str) -> list[UIAction]:
        normalized = intent.strip().lower()
        for key, actions in self.routes.items():
            if key in normalized:
                return list(actions)
        raise ValueError(f"No deterministic plan for intent: {intent!r}")


class CortexTraceSink:
    """Optional CORTEX sink.

    The import is lazy so mac-maestro stays lightweight and installable without
    CORTEX. The sink accepts any object exposing a store(...) method, which keeps
    it testable and avoids hard-coding a specific CORTEX package surface.
    """

    def __init__(self, cortex: Any | None = None) -> None:
        if cortex is None:
            try:
                from cortex import Cortex  # type: ignore
            except Exception:  # pragma: no cover - optional integration
                Cortex = None
            cortex = Cortex
        self.cortex = cortex

    def emit(self, envelope: dict[str, Any]) -> None:
        if self.cortex is None:
            return
        self.cortex.store(
            fact_type="agent:gui_action",
            payload=envelope,
            idempotency_key=envelope["trace_id"],
        )


@dataclass
class MoskvBot:
    """A minimal autonomous GUI agent substrate.

    MoskvBot adds three capabilities above MacMaestro:
    - deterministic intent planning,
    - sealed trace envelopes,
    - a small safety governor for repeated execution.
    """

    maestro: MacMaestro
    planner: MoskvPlanner | Callable[[str], Iterable[UIAction]] = field(
        default_factory=MoskvPlanner
    )
    sink: TraceSink | None = None
    governor_config: GovernorConfig = field(default_factory=GovernorConfig)
    agent_id: str = "moskvbot-01"
    state: GovernorState = field(default_factory=GovernorState)

    def step(self, intent: str, *, dry_run: bool = False) -> dict[str, Any]:
        self._enforce_dwell()
        actions = self._plan(intent)
        trace = self.maestro.run(actions, dry_run=dry_run or self.state.strict_mode)
        envelope = self._seal(intent=intent, actions=actions, trace=trace)
        self._govern(trace)
        if self.sink is not None:
            self.sink.emit(envelope)
        return envelope

    def run_goal(self, goal: BotGoal) -> list[dict[str, Any]]:
        envelopes: list[dict[str, Any]] = []
        for _ in range(goal.max_steps):
            envelope = self.step(goal.intent, dry_run=goal.dry_run)
            envelopes.append(envelope)
            if not envelope["ok"]:
                break
        return envelopes

    def _plan(self, intent: str) -> list[UIAction]:
        if isinstance(self.planner, MoskvPlanner):
            return self.planner.plan(intent)
        return list(self.planner(intent))

    def _seal(self, intent: str, actions: list[UIAction], trace: RunTrace) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        trace_payload = trace.model_dump(mode="json")
        action_payload = [action.model_dump(mode="json") for action in actions]
        payload = {
            "agent_id": self.agent_id,
            "intent": intent,
            "actions": action_payload,
            "trace": trace_payload,
            "governor": {
                "failures": self.state.failures,
                "strict_mode": self.state.strict_mode,
            },
        }
        payload_hash = _stable_hash(payload)
        return {
            "schema": "mac-maestro.moskvbot.trace.v1",
            "trace_id": str(uuid.uuid4()),
            "timestamp_ms": now_ms,
            "ok": trace.ok,
            "dry_run": trace.dry_run,
            "payload_hash": payload_hash,
            "payload": payload,
        }

    def _govern(self, trace: RunTrace) -> None:
        self.state.last_step_ms = int(time.time() * 1000)
        if trace.ok:
            self.state.failures = 0
            self.state.strict_mode = False
            return
        self.state.failures += 1
        if self.governor_config.strict_after_failure:
            self.state.strict_mode = True
        if self.state.failures > self.governor_config.max_failures:
            raise RuntimeError(
                f"MoskvBot halted after {self.state.failures} consecutive failures"
            )

    def _enforce_dwell(self) -> None:
        if self.state.last_step_ms <= 0:
            return
        elapsed = int(time.time() * 1000) - self.state.last_step_ms
        if elapsed < self.governor_config.min_dwell_ms:
            time.sleep((self.governor_config.min_dwell_ms - elapsed) / 1000)


def _default_routes() -> dict[str, list[UIAction]]:
    return {
        "save": [PressAction(key_code=1)],
        "cancel": [ClickAction(role="AXButton", title="Cancel")],
        "close": [ClickAction(role="AXButton", title="Close")],
        "confirm": [ClickAction(role="AXButton", title="OK")],
        "type": [TypeAction(text="")],
    }


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
