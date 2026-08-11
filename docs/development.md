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

## CLI help in documentation

After changing Typer help strings, update the plain-text `--help` excerpts in [README.md](../README.md) and [docs/commands/README.md](commands/README.md) if the user-facing surface changed. Verb pages link to `--help` rather than embedding full flag lists.
