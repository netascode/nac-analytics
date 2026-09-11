# Development

[← Documentation hub](README.md)

## Setup

```bash
git clone https://github.com/netascode/nac-analytics.git
cd nac-analytics
uv sync --extra dev
```

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy nac_analytics
uv run pytest
```

## Releasing to PyPI

Version is defined in `pyproject.toml`. The installed package exposes it via `nac_analytics.__version__` (from package metadata).

1. Update `version` in `pyproject.toml` and add an entry to [CHANGELOG.md](../CHANGELOG.md).
2. Commit, tag `vX.Y.Z`, and push the tag.
3. GitHub Actions (`.github/workflows/release.yml`) builds the wheel, smoke-tests it, and publishes to PyPI via [trusted publishing](https://docs.pypi.org/trusted-publishers/).

### One-time PyPI setup (trusted publishing)

`nac-analytics` is not on PyPI yet, so register a **pending** trusted publisher before the first release. This creates the PyPI project automatically on first upload — no manual upload or API token required.

1. Sign in to [pypi.org](https://pypi.org) with 2FA enabled (use the same account/org approach as [nac-validate](https://pypi.org/project/nac-validate/)).
2. Open [Account settings → Publishing](https://pypi.org/manage/account/publishing/) (or a project's **Publishing** tab after the project exists).
3. Add a **pending publisher** for GitHub Actions with these values:

   | Field | Value |
   | --- | --- |
   | PyPI project name | `nac-analytics` |
   | Owner | `netascode` |
   | Repository name | `nac-analytics` |
   | Workflow name | `release.yml` |
   | Environment name | *(leave blank)* |

   The workflow filename is `release.yml` only (not the full path).

4. Tag and push. The first successful publish converts the pending publisher to a normal one and creates the project.

**Important:** the `name` in `pyproject.toml` must be exactly `nac-analytics` — it must match the pending publisher's project name or the upload will fail.

### Troubleshooting

- **`invalid-pending-publisher` / `invalid-publisher`:** check owner, repository, and workflow filename for typos; leave environment blank on PyPI if the workflow has no `environment:` block.
- **Wrong project created:** if metadata name and pending publisher name differ, delete the mistaken PyPI project and re-register the pending publisher with the correct name ([PyPI docs](https://docs.pypi.org/trusted-publishers/troubleshooting/)).
- **Reusable workflows:** the workflow that calls `uv publish` must live in this repository (`release.yml`); reusable workflows are not supported as the trusted workflow.

## CLI help in documentation

After changing Typer help strings, update the plain-text `--help` excerpts in [nexus-dashboard.md](nexus-dashboard.md) and [commands/README.md](commands/README.md) if the user-facing surface changed. Verb pages link to `--help` rather than embedding full flag lists.
