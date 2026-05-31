import pytest

from mac_maestro import (
    ClickAction,
    ElementSelector,
    MacMaestro,
    MacMaestroError,
    MaestroWorkflow,
)
from mac_maestro.backends.mock import MockBackend
from mac_maestro.models import AXNodeSnapshot


def test_workflow_wait_for() -> None:
    root = AXNodeSnapshot(
        element_id="root",
        role="AXWindow",
        title="Main",
        children=[
            AXNodeSnapshot(
                element_id="btn_new",
                role="AXButton",
                title="New Document",
            )
        ],
    )
    backend = MockBackend(root=root)
    maestro = MacMaestro(bundle_id="com.apple.TextEdit", backend=backend)
    workflow = MaestroWorkflow(maestro)

    # Success case
    node = workflow.wait_for(ElementSelector(role="AXButton", title="New Document"))
    assert node.element_id == "btn_new"

    # Timeout case
    with pytest.raises(MacMaestroError, match="Timeout waiting for element"):
        workflow.wait_for(
            ElementSelector(role="AXNonexistent", title="Nonexistent"),
            timeout=0.1,
            interval=0.02,
        )


def test_workflow_run_with_retry() -> None:
    root = AXNodeSnapshot(element_id="root", role="AXWindow", title="Main")
    backend = MockBackend(root=root)
    maestro = MacMaestro(bundle_id="com.apple.TextEdit", backend=backend)
    workflow = MaestroWorkflow(maestro)

    # Simple retry success
    trace = workflow.run_with_retry([ClickAction(role="AXWindow", title="Main")], max_retries=2)
    assert trace.ok is True


def test_workflow_do_until() -> None:
    root = AXNodeSnapshot(element_id="root", role="AXWindow", title="Main")
    backend = MockBackend(root=root)
    maestro = MacMaestro(bundle_id="com.apple.TextEdit", backend=backend)
    workflow = MaestroWorkflow(maestro)

    counter = 0

    def action():
        nonlocal counter
        counter += 1
        return maestro.run([])

    def condition():
        return counter >= 3

    success = workflow.do_until(action, condition, max_attempts=5, interval=0.01)
    assert success is True
    assert counter == 3


def test_workflow_wait_for_condition() -> None:
    root = AXNodeSnapshot(element_id="root", role="AXWindow", title="Main")
    backend = MockBackend(root=root)
    maestro = MacMaestro(bundle_id="com.apple.TextEdit", backend=backend)
    workflow = MaestroWorkflow(maestro)

    counter = 0

    def condition():
        nonlocal counter
        counter += 1
        return counter >= 3

    assert workflow.wait_for_condition(condition, timeout=1.0, interval=0.01) is True

    # Timeout case
    def always_false():
        return False

    with pytest.raises(MacMaestroError, match="Timeout waiting for custom condition"):
        workflow.wait_for_condition(always_false, timeout=0.05, interval=0.01)


def test_workflow_wait_for_active_window() -> None:
    root = AXNodeSnapshot(
        element_id="root",
        role="AXWindow",
        title="My App Window",
        children=[
            AXNodeSnapshot(
                element_id="child_win",
                role="AXWindow",
                title="Child Modal",
            )
        ],
    )
    backend = MockBackend(root=root)
    maestro = MacMaestro(bundle_id="com.apple.TextEdit", backend=backend)
    workflow = MaestroWorkflow(maestro)

    # Match root window
    node1 = workflow.wait_for_active_window("My App Window")
    assert node1.element_id == "root"

    # Match child window
    node2 = workflow.wait_for_active_window("Child Modal")
    assert node2.element_id == "child_win"

    # Timeout case
    with pytest.raises(MacMaestroError, match="Timeout waiting for window with title"):
        workflow.wait_for_active_window("Nonexistent", timeout=0.05, interval=0.01)
