# mac-maestro — technical specification

Status: alpha. This document describes the Python implementation, not a certification or formal proof.

## Execution model

```text
UIAction / ElementSelector
        |
        v
MacMaestro.run -> AX snapshot -> selector safety policy
        |                         |
        |                         v
        |                    semantic matcher (when targeted)
        v                         |
        +-------------------------+
        |
        v
backend operation (skipped in dry run) -> structured RunTrace
```

The backend protocol separates real macOS Accessibility operations from the in-memory mock. Each action captures a fresh snapshot. Selectors match role, title, description and other properties using weighted scores; ambiguous matches can raise an error. Confidence thresholds and below-threshold behavior are configurable, not a guarantee of correct intent.

## Implemented components

| Component | Responsibility |
| --- | --- |
| `models.py` | Pydantic action, selector, snapshot and trace models |
| `backends/ax.py` | macOS Accessibility integration; bounded snapshot depth and children per node |
| `backends/mock.py` | In-memory action recording for tests |
| `matcher.py` | Weighted semantic matching and ambiguity detection |
| `runtime.py` | Sequential execution, matching, safety checks and dry-run traces |
| `safety.py` | Basic action validation; not a comprehensive policy engine |
| `trace.py` | Structured trace collection |
| `workflow.py` | Waiting, retry and condition-based helpers |
| `replay.py`, `invariants.py` | Replay, drift comparison and invariant evaluation utilities |
| `mcp_server.py` | Experimental MCP adapter; integration validation pending |

## Operational and trust boundaries

- Real AX access requires a local macOS session, installed PyObjC frameworks, and user-granted Accessibility permission.
- The operating system, current application state and user authorization are outside the matcher. A selected element or successful trace is not a proof of authorized intent.
- Dry runs skip backend action methods. They can still read application data and, depending on backend configuration, prompt for Accessibility access. They do not simulate UI state transitions.
- Traces may include UI values and matched nodes. They are not inherently redacted, cryptographically authenticated or tamper-evident.
- A multi-action run is not transactional. An unsuccessful result does not imply earlier actions were rolled back.
- Local GUI automation is not OS sandboxing, Byzantine fault tolerance, zero-latency execution, or a formally verified security boundary.

## Verification

Use the mock backend and the existing pytest suite for reproducible checks. Real AX behavior depends on the OS, application version, permissions and locale and must be validated separately against an explicitly authorized test application. MCP import, initialization and end-to-end interoperability remain separate acceptance criteria.

See [README](../README.md) for setup and [SECURITY](../SECURITY.md) for vulnerability reporting.
