# mac-maestro

mac-maestro is an alpha Python library for automating macOS applications through the Accessibility (AX) API. It matches UI elements by properties such as role and title, applies a safety policy, and returns a structured execution trace. A mock backend supports development without controlling a real application.

## Install with your coding agent

Ask an agent running on your own Mac:

> Install mac-maestro from https://github.com/borjamoskv/mac-maestro in an isolated Python virtual environment. Inspect the checked-out revision and its dependencies before installation. Follow AGENTS.md, run the mock smoke test and the test suite, and report the commit SHA, Python version, dependency check and test results. Do not request Accessibility access or operate real applications during setup. Stop if dependency resolution or tests fail.

The agent needs a local terminal, Git and Python 3.11+. A cloud-only agent cannot control your Mac's desktop. Use a reviewed revision; the dependency update in [PR #9](https://github.com/borjamoskv/mac-maestro/pull/9) is not part of main until merged.

## Requirements and installation

- Python 3.11 or later.
- macOS, the optional PyObjC dependencies, and Accessibility permission for the real AX backend.
- The target application must be running and expose the elements you want to control through Accessibility.

```bash
git clone https://github.com/borjamoskv/mac-maestro.git
cd mac-maestro
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,macos]'
python -m pip check
python -m pytest -q
git rev-parse HEAD
```

For mock-only development, omit the `macos` extra. Keep Accessibility disabled during installation and mock tests.

Only after deciding to use the real backend, manually grant Accessibility access to the application launching Python in **System Settings → Privacy & Security → Accessibility**. The backend can prompt for permission when it first takes a snapshot. Labels and available AX elements vary by application and language.

## Try the mock backend

This example runs without interacting with a real application:

```python
from mac_maestro import AXNodeSnapshot, ClickAction, MacMaestro
from mac_maestro.backends.mock import MockBackend

root = AXNodeSnapshot(
    element_id="root",
    role="AXWindow",
    children=[AXNodeSnapshot(element_id="new", role="AXButton", title="New Document")],
)
backend = MockBackend(root)
maestro = MacMaestro(bundle_id="com.apple.TextEdit", backend=backend)
actions = [ClickAction(role="AXButton", title="New Document")]
preview = maestro.run(actions, dry_run=True)
assert preview.ok, preview.error
assert not backend.executed

trace = maestro.run(actions)
assert trace.ok, trace.error
assert backend.executed == [{"kind": "click", "element_id": "new"}]
print("mock smoke test: PASS")
```

For a real application, instantiate `AXBackend` from `mac_maestro.backends` and pass it as `backend`. `maestro.run(actions, dry_run=True)` resolves actions and produces a trace without executing UI actions. Inspect `trace.ok` and `trace.error` before relying on a result. See [the TextEdit example](examples/textedit_ax.py) for an AX-backed sequence; it requires a suitable TextEdit window and matching element labels.

## Scope and limitations

The runtime supports clicks, double and right clicks, hovering, scrolling, typing, and key presses. The default safety policy blocks a small set of exact destructive target titles and limits text length; it is not a general guarantee that an action is safe. Test selectors with `dry_run=True` and review actions before running them against real applications. A dry run does not simulate future UI states and is not authorization for a later action. Accessibility snapshots and traces can contain private application data; do not publish them without review. Workflows can partially succeed before failing; do not automatically retry non-idempotent actions.

The repository also contains an MCP server, but its current entry point and backend initialization require fixes before it can be used as a supported integration. The Python API and mock backend are the recommended starting point.

## Development

```bash
python -m pip install -e '.[dev,macos]'
python -m pytest -x --tb=short
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [the technical specification](docs/TECHNICAL_SPEC.md), and [SECURITY.md](SECURITY.md). Licensed under [Apache-2.0](LICENSE).
