# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2.1] - 2026-03-17

### Changed
- **CI**: Install `pyobjc` frameworks in GitHub Actions runner so AXBackend mock-patched tests execute instead of being skipped.
- **README**: Full rewrite aligned with v0.2.0 feature surface — correct install commands, working MockBackend example, dry-run/thresholds/NDJSON documented.

### Fixed
- `pyproject.toml` version bumped to `0.2.1` (was still `0.1.0`).

## [v0.2.0] - 2026-03-17

### Added
- **AXBackend**: Native `AXPress` and `AXSetValue` for cursor-free UI automation.
- **Dry-run mode**: `maestro.run(actions, dry_run=True)` resolves elements without mutating UI.
- **Confidence thresholds**: `min_confidence` with `on_below_threshold` policies (`abort`, `fallback_exact`, `emit_candidates`).
- **NDJSON traces**: `trace.to_ndjson()` for streaming log ingestion.
- **`ConfidenceBelowThresholdError`**: Raised when best match is below threshold.
- **`find_all_matches()`**: Returns all scored candidates sorted by confidence.
- **SECURITY.md**: Vulnerability scope and disclosure policy.
- **`py.typed`**: PEP 561 marker for downstream type checking.

### Fixed
- Conditional import of `AXBackend` in `backends/__init__.py` — no longer crashes on platforms without pyobjc.
- `test_backend_ax.py` uses `try/except` + `pytestmark skipif` instead of bare import.

## [v0.1.0] - 2026-03-17

### Added
- **Core SDK**: Initial release of MacMaestro.
- **Semantic Automation**: `click`, `type_text`, `press`, `snapshot` via Accessibility API.
- **Safety Membrane**: Immutable `SafetyPolicy` blocks destructive UI interactions.
- **MCP Server**: Model Context Protocol via stdio for agent integration.
- **Observability**: Nested JSON `RunTrace` documenting every action and match.
