"""
MacMaestro TextEdit Demo (v0.1.0)
---------------------------------
This script demonstrates the Semantic-first macOS GUI automation capabilities
of MacMaestro by opening TextEdit, creating a new document, typing a message,
and outputting the structured execution trace.
"""

import os
import sys
import subprocess
import time
from mac_maestro import MacMaestro, ClickAction, TypeAction

def ensure_textedit_running():
    # Attempt to open TextEdit so it's ready.
    subprocess.run(["open", "-a", "TextEdit"])
    time.sleep(1)  # Brief pause to let the app initialize and focus

def run_demo():
    print("🚀 Iniciando MacMaestro Demo en TextEdit...")
    ensure_textedit_running()

    # Initialize MacMaestro targeting TextEdit by bundle ID
    maestro = MacMaestro(bundle_id="com.apple.TextEdit")

    # Define the execution sequence
    actions = [
        # 1. Semantically find and click the "New Document" button
        ClickAction(role="AXButton", title="New Document"),
        
        # 2. Type our message directly into the focused window/document
        TypeAction(text="Semantic-first macOS GUI automation with safety gates and structured traces! 🚀", clear_first=False),
    ]

    print("🤖 Ejecutando acciones (AX API)...")
    # Run the sequence. MacMaestro handles the AX translation and safety gates.
    trace = maestro.run(actions)

    print("\n📝 Resultados (Execution Trace):")
    if trace.ok:
        print("✅ Demo exitosa. Revisa la ventana de TextEdit.")
    else:
        print(f"❌ Fallo en la automatización: {trace.error}")
        
    print("\n--- Trace Estructurado (JSON) ---")
    print(trace.to_json())
    
    # We exit cleanly.
    return 0 if trace.ok else 1

if __name__ == "__main__":
    sys.exit(run_demo())
