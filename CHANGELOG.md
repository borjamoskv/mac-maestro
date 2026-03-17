# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Real AX Backend implementation for actual macOS mutations.
- Multi-monitor support for UI snapshot bounds.
- Dry-run mode for testing automation sequences safely.

## [v0.1.0] - 2026-03-17

### Added
- **Core SDK**: Initial release of MacMaestro (MAC-MAESTRO-Ω v3.0).
- **Semantic Automation**: Capabilities for `get_ui_snapshot`, `click_element`, `type_in_app`, and raw keypresses via the native Accessibility (AX) API.
- **Safety Membrane**: Immutable `SafetyPolicy` that prevents unintended interactions with destructive UI components.
- **MCP Server**: Integrated Model Context Protocol via stdio to plug straight into agents like Claude Desktop and Cursor.
- **Observability**: Rich nested JSON traces documenting every action, matched element, validation, and error.
