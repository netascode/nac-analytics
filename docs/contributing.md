# Contributing

[← Documentation hub](README.md)

## Setup

```bash
uv sync --locked --extra dev
pre-commit install
```

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy nac_analytics
uv run bandit -c pyproject.toml -r nac_analytics/
uv run pytest --cov --cov-fail-under=80
```

CI runs the same gates on pull requests and on release tags.

## Tests

Unit tests use `httpx.MockTransport` via the shared `Lab` fixture in `tests/conftest.py`. Add a route keyed by URL path, then drive `NDClient` or a CLI command.

Contract tests under `tests/contract/` replay sanitized JSON fixtures from `tests/contract/fixtures/`. Refresh fixtures manually from a lab Nexus Dashboard instance when API shapes change — they are not run against a live cluster in CI.

Bundled config templates live in `nac_analytics/products/nexus_dashboard/templates/` (used by `nac-analytics init`). After editing those files, sync copies to `examples/nexus_dashboard/config/`.

## Product layout

When adding a Cisco product:

```
products/<product>/
  config.py      # connection/settings dataclass for that product
  settings.py    # YAML/env bootstrap for its config section
  client.py      # API client
  cli.py         # Typer command group
```

Keep `nac_analytics/core/` product-neutral (exceptions, reporting, registry).

## Release

1. Update [CHANGELOG.md](../CHANGELOG.md) and [pyproject.toml](../pyproject.toml) version.
2. Merge to `main`.
3. Tag `v*` — [release.yml](../.github/workflows/release.yml) runs the full test workflow, builds the wheel, and publishes to PyPI via OIDC trusted publishing.

No live Nexus Dashboard is required for the default test run.
