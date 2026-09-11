# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-09-11

### Added

- `nac-analytics init` writes `nac-analytics.yaml` and `.env` from bundled templates (PyPI-friendly setup).
- Contract tests with recorded JSON fixtures under `tests/contract/`.
- `docs/contributing.md`, `SECURITY.md`, and pre-commit hooks mirroring CI.
- Release workflow now runs the full test suite before building and publishing.

### Changed

- Config templates moved to `examples/nexus_dashboard/config/`.
- Nexus Dashboard connection settings moved from `nac_analytics.core.config` to `nac_analytics.products.nexus_dashboard.config`.
- Base exception renamed to `NacAnalyticsError` (beta breaking change for code importing the old name).
- `resolve_snapshot` with no finished snapshots now exits 4 (`InputError`) instead of 2.
- Nexus Dashboard CLI split into `commands/` subpackage; gate failures print `error (exit N):` on stderr.
- Minimum coverage floor raised to 80%.
- Hatch sdist excludes tests, examples, docs, and CI workflows.

## [0.1.1] - 2026-09-11

### Fixed

- PyPI README links now use absolute GitHub URLs so documentation and examples resolve correctly from pypi.org.
- PyPI project documentation URL now points at the documentation hub.

## [0.1.0] - 2026-09-11

### Added

- Initial release of the `nac-analytics` CLI for Cisco ACI change analysis via Nexus Dashboard 4.2.1+.
- Nexus Dashboard product commands: `doctor`, `prechange`, `delta`, `compliance`, and `analyze`.
- YAML, environment, and CLI configuration with redaction-safe reporting.
