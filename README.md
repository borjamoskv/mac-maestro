# MacMaestro (MAC-MAESTRO-Ω v3.0)

Sovereign UI automation for macOS using the native Accessibility (AX) API. Designed for high-reliability, deterministic execution, and safety.

## Features

- **Semantic-First Matching**: Match elements by role, title, value, or description with a fuzzy scoring system.
- **Action Ladder**: Native AX actions (clicks, typing) with robust fallbacks to `CGEvent` mouse and keyboard events.
- **Safety Policy**: Built-in gating to prevent accidental clicks on dangerous UI elements (e.g., "Delete", "Format").
- **Structured Tracing**: Every run yields a comprehensive `RunTrace` with snapshots of the UI at each step, matched nodes, and detailed error logs.
- **High-Level Workflows**: Orchestration layer for handling retries, waiting for elements, and complex recovery logic.

## Installation

```bash
pip install -e ".[macos]"
```

*Note: Requires macOS and appropriate Accessibility permissions.*

## Quick Start

```python
from mac_maestro import MacMaestro, ClickAction, TypeAction, KeyModifier

# Initialize for a specific application
maestro = MacMaestro(bundle_id="com.apple.TextEdit")

# Define a sequence of actions
actions = [
    ClickAction(role="AXButton", title="New Document"),
    TypeAction(text="Hello, MacMaestro!", clear_first=True),
    # More complex matching
    ClickAction(role="AXMenuItem", title="Save", contains_text="Save"),
]

# Execute and get trace
trace = maestro.run(actions)

if trace.ok:
    print("Automation successful!")
else:
    print(f"Failed: {trace.error}")
    print(trace.to_json())
```

## Advanced Usage: Workflows

Use `MaestroWorkflow` for robust automation that handles UI delays.

```python
from mac_maestro import MacMaestro, MaestroWorkflow, ElementSelector

maestro = MacMaestro(bundle_id="com.apple.Music")
workflow = MaestroWorkflow(maestro)

# Wait for an element to appear (up to 10s)
workflow.wait_for(ElementSelector(role="AXButton", title="Play"))

# Run with retries
workflow.run_with_retry(actions, max_retries=3)
```

## Architecture

```mermaid
graph TD
    User([User Script]) --> Workflow[MaestroWorkflow]
    Workflow --> Runtime[MacMaestro Runtime]
    Runtime --> Safety[SafetyPolicy]
    Runtime --> Matcher[Semantic Matcher]
    Runtime --> Backend[AXBackend]
    Backend --> macOS[macOS Accessibility API]
    macOS --> Result[UI Mutation]
    Runtime --> Trace[RunTrace]
```

## License

Apache-2.0
