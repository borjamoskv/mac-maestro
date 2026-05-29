# CONTRIBUTING.md — C5-REAL DIRECTIVES

**Reality Level: C5-REAL**

*MacMaestro* operates as a sovereign entity on macOS. Development focuses on safety, determinism, and observable execution.

## 01 · Axioms of Interaction

1. **Zero Black-Box Magic**: Every UI interaction must yield a deterministic trace.
2. **Safety Membrane First**: Never bypass the `SafetyPolicy` implicitly. Destructive actions demand explicit clearance.
3. **Semantic Over Coordinate**: Coordinates mutate; semantic roles persist. AX data is the only source of truth.

## 02 · Forging Substrate

```bash
git clone https://github.com/borjamoskv/mac-maestro.git
cd mac-maestro

# Install strictly in editable mode with dev payloads
pip install -e ".[dev,mcp]"
```

## 03 · Pull Request Sentinel

- **Test Coverage**: Bug fixes or features lacking coverage will be rejected.
- **Trace Continuity**: New execution loops must yield structured data to `RunTrace`.
- **Documentation Parity**: API changes require immediate `README.md` and docstring updates.
- **Linting Compliance**: Execute `ruff check .` before submission.

## 04 · Architecture Epistemology

MacMaestro treats macOS as a high-entropy, chaotic environment. Assume windows move, elements vanish, and focus is stolen.
- **Do not use `time.sleep()` blocks** for state propagation.
- **Enforce retry mechanics** or explicit wait conditions via `MaestroWorkflow`.
