from mac_maestro import ClickAction, MacMaestro, PressAction, TypeAction
from mac_maestro.backends import AXBackend
from mac_maestro.models import ElementSelector

backend = AXBackend()
maestro = MacMaestro(
    bundle_id="com.apple.TextEdit",
    backend=backend,
)

trace = maestro.run(
    [
        ClickAction(role="AXButton", title="New Document"),
        TypeAction(
            text="hola desde mac-maestro",
            target=ElementSelector(role="AXTextArea"),
        ),
        PressAction(key_code=36),  # Enter
    ]
)

print(trace.to_json())
