class MacMaestroError(Exception):
    """Base exception for mac_maestro."""


class ElementNotFoundError(MacMaestroError):
    """Raised when no matching accessibility element is found."""


class ElementAmbiguousError(MacMaestroError):
    """Raised when more than one candidate matches with similar confidence."""


class ActionExecutionError(MacMaestroError):
    """Raised when an action cannot be executed on a matched element."""


class SafetyViolationError(MacMaestroError):
    """Raised when an action is blocked by safety policy."""


class ConfidenceBelowThresholdError(MacMaestroError):
    """Raised when the best element match is below the configured min_confidence threshold.

    Attributes:
        score: The best match score found.
        threshold: The required minimum threshold.
        candidates: All candidate matches found, in descending score order.
    """

    def __init__(
        self,
        score: float,
        threshold: float,
        candidates: list,
    ) -> None:
        self.score = score
        self.threshold = threshold
        self.candidates = candidates
        super().__init__(
            f"Best match score {score:.2f} is below min_confidence={threshold:.2f}. "
            f"{len(candidates)} candidate(s) found."
        )

