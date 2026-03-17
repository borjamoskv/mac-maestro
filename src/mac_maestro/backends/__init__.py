from __future__ import annotations

import sys

from .mock import MockBackend

__all__ = ["MockBackend"]

# AXBackend requires macOS-only frameworks (pyobjc: ApplicationServices, Quartz).
# Import conditionally to allow the package to load on Linux/CI runners.
if sys.platform == "darwin":
    try:
        from .ax import AXBackend, AXBackendConfig

        __all__ += ["AXBackend", "AXBackendConfig"]
    except ImportError:
        pass
