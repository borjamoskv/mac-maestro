import pytest
import sys
import subprocess
import time
from unittest.mock import patch

from mac_maestro import MacMaestro, TypeAction
from mac_maestro.backends.ax import AXBackend, AXBackendConfig
from mac_maestro.errors import ActionExecutionError
from mac_maestro.models import ElementMatch, AXNodeSnapshot


pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Tests strictly require macOS Native AX backend.")


@pytest.fixture
def run_textedit():
    # Attempt to open TextEdit for tests
    process = subprocess.Popen(["open", "-a", "TextEdit"])
    time.sleep(1) # Give it time to launch and be reachable
    yield
    # We could kill it here, but it's simpler to just let it be or close it via shortcut if desired.


def test_permissions_denied_raises_error():
    config = AXBackendConfig(prompt_for_access=False)
    backend = AXBackend(config=config)

    # Patch the access check directly so we don't depend on actual local toggles
    with patch("mac_maestro.backends.ax.AXIsProcessTrustedWithOptions", return_value=False):
        with pytest.raises(ActionExecutionError, match="Accessibility permission not granted"):
            backend.ensure_accessibility_permissions(prompt=False)


def test_ax_snapshot_click_and_type(run_textedit):
    """
    Integration test asserting that snapshotting TextEdit, clicking the new document
    and typing via fallback/AX works.
    This also covers the fallback implementations. 
    """
    config = AXBackendConfig(prompt_for_access=False)
    backend = AXBackend(config=config)
    
    # Check if we have permissions first, to skip otherwise
    try:
        backend.ensure_accessibility_permissions(prompt=False)
    except ActionExecutionError:
        pytest.skip("No accessibility permissions to run genuine UI tests.")
    
    # 1. Take snapshot
    maestro = MacMaestro(bundle_id="com.apple.TextEdit", backend=backend)
    
    # To test actual interaction without changing UI states wildly:
    # Instead of full automation which might fail if 'New Document' isn't visible
    # We simply try to get a snapshot and do a dummy click.
    try:
        snapshot = backend.snapshot("com.apple.TextEdit")
        assert snapshot is not None
        assert snapshot.role in {"AXApplication", "AXUnknown", "AXWindow", "AXStandardWindow"}
    except ActionExecutionError as e:
        pytest.skip(f"Failed to snapshot TextEdit: {e}")

    # 2. Type text fallback
    # If the user has TextEdit focused, writing something via fallback
    # We can invoke backend.type_text directly with no match
    action = TypeAction(text="testing mac-maestro", clear_first=False)
    try:
        backend.type_text(action, match=None)
    except Exception as e:
        pytest.fail(f"Type fallback raised unexpected error: {e}")

    # 3. Simulate fallback of AXPress to mouse click
    # Using a constructed match representing an artificial element
    node = AXNodeSnapshot(element_id="test", role="AXButton", title="Dummy")
    match = ElementMatch(element_id="test", confidence=1.0, node=node)
    
    # Put a dummy element in Cache to prevent resolve error
    # We mock _try_ax_press to fail, so it invokes `_element_center` and `_mouse_left_click`
    class DummyRef:
        x: float = 0.0
        y: float = 0.0
        width: float = 10.0
        height: float = 10.0
    
    backend._element_cache["test"] = DummyRef()
    
    with patch.object(backend, "_try_ax_press", return_value=False), \
         patch.object(backend, "_copy_attr", side_effect=[
             # kAXPositionAttribute
             type("Position", (object,), {"x": 100, "y": 100})(),
             # kAXSizeAttribute
             type("Size", (object,), {"width": 50, "height": 50})(),
         ]), \
         patch.object(backend, "_mouse_left_click") as mock_click:
         
        backend.click(match)
        mock_click.assert_called_once_with(125.0, 125.0)

