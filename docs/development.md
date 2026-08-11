# Development

[← Documentation hub](README.md)

## Setup

```bash
git clone https://github.com/netascode/nac-analytics.git
cd nac-analytics
uv sync --group dev
```

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy nac_analytics
uv run pytest
```

## Captured CLI help

Colourised `--help` output is checked into markdown via [scripts/capture-help.py](../scripts/capture-help.py). After changing Typer help strings:

```bash
uv run python scripts/capture-help.py
```

CI runs `uv run python scripts/capture-help.py --check` to fail on drift.

**Destinations:** product-tier help → [README.md](../README.md); global help → [commands/README.md](commands/README.md); verb help → [commands/nexus-dashboard/](commands/nexus-dashboard/).
