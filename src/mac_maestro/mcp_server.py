import asyncio
from typing import Any

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server

from mac_maestro import (
    ClickAction,
    DoubleClickAction,
    ElementSelector,
    HoverAction,
    MacMaestro,
    PressAction,
    RightClickAction,
    ScrollAction,
    TypeAction,
)
from mac_maestro.errors import MacMaestroError


# Initialize MacMaestro with default config
# We don't specify bundle_id here as tools will take it as an argument
def get_maestro(bundle_id: str) -> MacMaestro:
    return MacMaestro(bundle_id=bundle_id)

server = Server("mac-maestro")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for macOS automation."""
    return [
        types.Tool(
            name="get_ui_snapshot",
            description="Captures the UI accessibility tree for a given application.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_id": {
                        "type": "string",
                        "description": (
                            "The bundle identifier of the app (e.g., com.apple.TextEdit)."
                        ),
                    },
                },
                "required": ["bundle_id"],
            },
        ),
        types.Tool(
            name="click_element",
            description="Performs a semantic click on a UI element.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "role": {
                        "type": "string",
                        "description": "AXRole of the element (e.g., AXButton).",
                    },
                    "title": {"type": "string", "description": "Title or label of the element."},
                    "description": {
                        "type": "string",
                        "description": "AXDescription of the element.",
                    },
                },
                "required": ["bundle_id"],
            },
        ),
        types.Tool(
            name="type_in_app",
            description=(
                "Types text into the application. If a selector is provided, "
                "it tries to focus it first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "text": {"type": "string"},
                    "role": {"type": "string"},
                    "title": {"type": "string"},
                    "clear_first": {"type": "boolean", "default": True},
                },
                "required": ["bundle_id", "text"],
            },
        ),
        types.Tool(
            name="press_key",
            description="Sends a raw key press to the application.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "key_code": {"type": "integer", "description": "Virtual key code."},
                    "modifiers": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["command", "shift", "option", "control"],
                        },
                    },
                },
                "required": ["bundle_id", "key_code"],
            },
        ),
        types.Tool(
            name="double_click_element",
            description="Performs a double click on a UI element.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "role": {
                        "type": "string",
                        "description": "AXRole of the element (e.g., AXButton).",
                    },
                    "title": {"type": "string", "description": "Title of the element."},
                    "description": {
                        "type": "string",
                        "description": "AXDescription of the element.",
                    },
                },
                "required": ["bundle_id"],
            },
        ),
        types.Tool(
            name="right_click_element",
            description="Performs a right click on a UI element.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "role": {
                        "type": "string",
                        "description": "AXRole of the element (e.g., AXButton).",
                    },
                    "title": {"type": "string", "description": "Title of the element."},
                    "description": {
                        "type": "string",
                        "description": "AXDescription of the element.",
                    },
                },
                "required": ["bundle_id"],
            },
        ),
        types.Tool(
            name="hover_element",
            description="Hovers the mouse pointer over a UI element.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "role": {
                        "type": "string",
                        "description": "AXRole of the element (e.g., AXButton).",
                    },
                    "title": {"type": "string", "description": "Title of the element."},
                    "description": {
                        "type": "string",
                        "description": "AXDescription of the element.",
                    },
                },
                "required": ["bundle_id"],
            },
        ),
        types.Tool(
            name="scroll_in_app",
            description=(
                "Scrolls in a specified direction within the application, "
                "optionally targeting a UI element."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                        "default": "down",
                    },
                    "amount": {"type": "integer", "default": 3},
                    "role": {
                        "type": "string",
                        "description": "AXRole of the target scrollable container element.",
                    },
                    "title": {"type": "string", "description": "Title of the target element."},
                },
                "required": ["bundle_id"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    if not arguments:
        raise ValueError("Missing arguments")

    bundle_id = arguments.get("bundle_id")
    if not bundle_id:
        raise ValueError("Missing bundle_id")

    maestro = get_maestro(bundle_id)

    try:
        if name == "get_ui_snapshot":
            snapshot = maestro.backend.snapshot(bundle_id)
            return [types.TextContent(type="text", text=snapshot.model_dump_json(indent=2))]

        elif name == "click_element":
            selector = ElementSelector(
                role=arguments.get("role"),
                title=arguments.get("title"),
                description=arguments.get("description"),
            )
            trace = maestro.run([ClickAction(selector=selector)])
            return [types.TextContent(type="text", text=trace.model_dump_json(indent=2))]

        elif name == "type_in_app":
            selector = None
            if arguments.get("role") or arguments.get("title"):
                selector = ElementSelector(
                    role=arguments.get("role"),
                    title=arguments.get("title"),
                )
            
            action = TypeAction(
                text=arguments.get("text", ""),
                selector=selector,
                clear_first=arguments.get("clear_first", True),
            )
            trace = maestro.run([action])
            return [types.TextContent(type="text", text=trace.model_dump_json(indent=2))]

        elif name == "double_click_element":
            selector = ElementSelector(
                role=arguments.get("role"),
                title=arguments.get("title"),
                description=arguments.get("description"),
            )
            trace = maestro.run([DoubleClickAction(selector=selector)])
            return [types.TextContent(type="text", text=trace.model_dump_json(indent=2))]

        elif name == "right_click_element":
            selector = ElementSelector(
                role=arguments.get("role"),
                title=arguments.get("title"),
                description=arguments.get("description"),
            )
            trace = maestro.run([RightClickAction(selector=selector)])
            return [types.TextContent(type="text", text=trace.model_dump_json(indent=2))]

        elif name == "hover_element":
            selector = ElementSelector(
                role=arguments.get("role"),
                title=arguments.get("title"),
                description=arguments.get("description"),
            )
            trace = maestro.run([HoverAction(selector=selector)])
            return [types.TextContent(type="text", text=trace.model_dump_json(indent=2))]

        elif name == "scroll_in_app":
            target = None
            if arguments.get("role") or arguments.get("title"):
                target = ElementSelector(
                    role=arguments.get("role"),
                    title=arguments.get("title"),
                )
            action = ScrollAction(
                direction=arguments.get("direction", "down"),
                amount=arguments.get("amount", 3),
                target=target,
            )
            trace = maestro.run([action])
            return [types.TextContent(type="text", text=trace.model_dump_json(indent=2))]

        elif name == "press_key":
            action = PressAction(
                key_code=arguments.get("key_code", 0),
                modifiers=arguments.get("modifiers", []),
            )
            trace = maestro.run([action])
            return [types.TextContent(type="text", text=trace.model_dump_json(indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except MacMaestroError as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Unexpected error: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mac-maestro",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    from mcp.server.models import InitializationOptions
    asyncio.run(main())
