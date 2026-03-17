# Contributing to MacMaestro

Thank you for your interest in contributing. *MacMaestro* is built with a primary focus on safety, determinism, and observable execution on macOS.

## Core Philosophy (The Axioms)

1. **Zero Black-Box Magic**. Every UI interaction must leave a trace.
2. **Safety First**. Never assume a destructive action is intended without explicitly bypassing the `SafetyPolicy`.
3. **Semantic Over Coordinate**. We rely on the Accessibility API (AX) first and foremost. Coordinates change; semantic roles persist.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/borjamoskv/mac-maestro.git
cd mac-maestro

# Install in editable mode with all dev dependencies
pip install -e ".[dev,mcp]"
```

## Pull Request Guidelines

- **Add Tests**: If you fix a bug or add a feature, it must have corresponding test coverage.
- **Maintain Traceability**: Any new action or interaction loop must yield data to the `RunTrace` output.
- **Update Documentation**: Update the README and docstrings if you change public-facing APIs.
- **Pass Linting**: Code should adhere to standard Ruff linting rules (`ruff check .`).

### Architecture Notice

MacMaestro treats macOS as a potentially hostile and chaotic environment. When you interact with the UI, assume the window might move, the element might disappear, or focus might be stolen. Avoid `time.sleep()` blocks for state propagation; use retry mechanics or explicit wait conditions via `MaestroWorkflow`.
