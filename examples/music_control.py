import time
from mac_maestro import (
    MacMaestro,
    MaestroWorkflow,
    ClickAction,
    TypeAction,
    ElementSelector,
    KeyModifier,
    PressAction
)

def automate_music():
    """
    Demonstrates using MacMaestro to control the Music.app.
    """
    # 1. Initialize Maestro for Apple Music
    maestro = MacMaestro(bundle_id="com.apple.Music")
    workflow = MaestroWorkflow(maestro)

    print("🚀 Starting Apple Music Automation...")

    try:
        # 2. Ensure Music is open and focused
        print("⏳ Waiting for Music to load...")
        workflow.wait_for(ElementSelector(role="AXWindow"), timeout=10)

        # 3. Search for an artist
        print("🔍 Searching for 'Vetusta Morla'...")
        
        # We search for the search field. In Music.app it's often an AXTextField or AXStaticText in a toolbar.
        search_selector = ElementSelector(role="AXTextField", description="Search")
        
        actions = [
            ClickAction(role="AXTextField", description="Search"),
            TypeAction(text="Vetusta Morla", clear_first=True),
            PressAction(key_code=36),  # Return key to search
        ]
        
        trace = workflow.run_with_retry(actions)
        if not trace.ok:
            print(f"❌ Search failed: {trace.error}")
            return

        # 4. Wait for results and play a song
        print("🎵 Waiting for search results...")
        time.sleep(2) # Simple wait for results to populate (native AX can be fast)

        # Try to find a 'Play' button in the results
        play_btn = ElementSelector(role="AXButton", title="Play")
        try:
             workflow.wait_for(play_btn, timeout=5)
             maestro.run([ClickAction(role="AXButton", title="Play")])
             print("✅ Playing music!")
        except Exception:
             print("⚠️ Could not find play button, trying keyboard fallback...")
             maestro.run([PressAction(key_code=49)]) # Spacebar to play/pause

        # 5. Show progress
        print("✨ Automation sequence finished.")
        
    except Exception as e:
        print(f"💥 Fatal error: {e}")

if __name__ == "__main__":
    automate_music()
