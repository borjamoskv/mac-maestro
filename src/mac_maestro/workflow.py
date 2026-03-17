from __future__ import annotations

import time
from typing import Callable

from .errors import MacMaestroError
from .matcher import find_best_match
from .models import AXNodeSnapshot, ElementSelector, RunTrace, UIAction
from .runtime import MacMaestro


class MaestroWorkflow:
    """
    High-level orchestration for complex UI flows, including retries,
    waiting for elements, and condition-based execution.
    """

    def __init__(self, maestro: MacMaestro) -> None:
        self.maestro = maestro

    def wait_for(
        self,
        selector: ElementSelector,
        timeout: float = 10.0,
        interval: float = 0.5,
    ) -> AXNodeSnapshot:
        """
        Wait for an element to appear in the UI before proceeding.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                root = self.maestro.backend.snapshot(self.maestro.bundle_id)
                match = find_best_match(root, selector)
                return match.node
            except MacMaestroError:
                time.sleep(interval)

        raise MacMaestroError(f"Timeout waiting for element: {selector}")

    def run_with_retry(
        self,
        actions: list[UIAction],
        max_retries: int = 3,
        delay: float = 1.0,
    ) -> RunTrace:
        """
        Execute a sequence of actions with a retry mechanism.
        """
        last_trace = None
        for attempt in range(max_retries):
            trace = self.maestro.run(actions)
            if trace.ok:
                return trace
            last_trace = trace
            if attempt < max_retries - 1:
                time.sleep(delay)

        return last_trace or RunTrace(ok=False, events=[])

    def do_until(
        self,
        action_fn: Callable[[], RunTrace],
        condition_fn: Callable[[], bool],
        max_attempts: int = 5,
        interval: float = 1.0,
    ) -> bool:
        """
        Execute an action repeatedly until a condition is met.
        """
        for _ in range(max_attempts):
            action_fn()
            if condition_fn():
                return True
            time.sleep(interval)
        return False
