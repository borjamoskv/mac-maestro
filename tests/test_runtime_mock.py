from mac_maestro import (
    ClickAction,
    DoubleClickAction,
    HoverAction,
    MacMaestro,
    RightClickAction,
    ScrollAction,
)
from mac_maestro.backends.mock import MockBackend
from mac_maestro.models import AXNodeSnapshot


def test_runtime_click_flow() -> None:
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

    trace = maestro.run([ClickAction(role="AXButton", title="New Document")])

    assert trace.ok is True
    assert backend.executed[0]["kind"] == "click"
    assert backend.executed[0]["element_id"] == "btn_new"


def test_runtime_new_actions() -> None:
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

    # Double click
    trace = maestro.run([DoubleClickAction(role="AXButton", title="New Document")])
    assert trace.ok is True
    assert backend.executed[-1]["kind"] == "double_click"
    assert backend.executed[-1]["element_id"] == "btn_new"

    # Right click
    trace = maestro.run([RightClickAction(role="AXButton", title="New Document")])
    assert trace.ok is True
    assert backend.executed[-1]["kind"] == "right_click"
    assert backend.executed[-1]["element_id"] == "btn_new"

    # Hover
    trace = maestro.run([HoverAction(role="AXButton", title="New Document")])
    assert trace.ok is True
    assert backend.executed[-1]["kind"] == "hover"
    assert backend.executed[-1]["element_id"] == "btn_new"

    # Scroll with target
    scroll_action = ScrollAction(
        direction="down",
        amount=5,
        target=ClickAction(role="AXButton", title="New Document"),
    )
    trace = maestro.run([scroll_action])
    assert trace.ok is True
    assert backend.executed[-1]["kind"] == "scroll"
    assert backend.executed[-1]["direction"] == "down"
    assert backend.executed[-1]["amount"] == 5
    assert backend.executed[-1]["element_id"] == "btn_new"

    # Scroll without target
    trace = maestro.run([ScrollAction(direction="up", amount=2)])
    assert trace.ok is True
    assert backend.executed[-1]["kind"] == "scroll"
    assert backend.executed[-1]["direction"] == "up"
    assert backend.executed[-1]["amount"] == 2
    assert backend.executed[-1]["element_id"] is None

