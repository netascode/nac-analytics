# nac-analytics

> **In development** — install from source today; PyPI release planned.
> Formerly **nac-nd**. Today it covers Cisco ACI via Nexus Dashboard 4.2.1+; the intent is to grow beyond Nexus Dashboard and add support for additional Cisco products, so one tool can drive change analytics across platforms.

CLI for change analysis on Cisco ACI fabrics via Nexus Dashboard 4.2.1+.

Commands are grouped per Cisco product: `nac-analytics <product> <command>`.
Today the product is `nexus-dashboard` (alias `nd`); more products are planned.

## Installation

**Requirements:** Nexus Dashboard 4.2.1+, Python 3.10+, an ACI fabric registered in Nexus Dashboard.

```bash
git clone https://github.com/netascode/nac-analytics.git
cd nac-analytics
uv sync --group dev
uv run nac-analytics --help
```

## Quick start

```bash
cp config.example.yaml nac-analytics.yaml   # edit host, fabric, domain
cp .env.example .env                 # set ND_USER and ND_PASSWORD
uv run nac-analytics nd doctor
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success; threshold not breached |
| 1 | Unexpected error |
| 2 | Analysis job failed, stopped, vanished, or timed out |
| 3 | New anomalies at `--fail-on` (or compliance violations with `--fail-on-violations`) |
| 4 | Bad input, config, or configuration rejected by Nexus Dashboard |
| 5 | Authentication or authorisation failure |

## Nexus Dashboard commands

```
$ nac-analytics nexus-dashboard --help

Usage: nac-analytics nexus-dashboard [OPTIONS] COMMAND [ARGS]...

Change analysis for Cisco Nexus Dashboard 4.2.1+ (GA REST APIs, ACI).

Configuration:
 ND_HOST                 Nexus Dashboard hostname or IP
 ND_USER                 Login username
 ND_PASSWORD             Login password
 ND_DOMAIN               Login domain
 ND_FABRIC               Default ACI fabric name
 ND_VERIFY_SSL           Verify TLS certificate (ND_VERIFY_TLS accepted)
 ND_CA_BUNDLE            Path to CA bundle
 ND_JOB_TIMEOUT_MINUTES  Minutes to wait for analysis jobs
 ND_POLL_INTERVAL        Seconds between job status polls
 ND_DELTA_DETAIL         Default --detail for prechange and delta
 ND_CONFIG               Path to YAML config file

In YAML, nest these under a `nexus_dashboard:` section. Settings load from
CLI flags, then environment variables, nac-analytics.yaml, or .env.

Options:
  --help          Show this message and exit.

Commands:
  prechange   Analyse a candidate configuration against a fabric's current state.
  delta       Compare two snapshots of a fabric and report what changed.
  snapshots   Resolve a fabric snapshot and print its ID (for CI baseline pinning).
  compliance  Report compliance rule status for a fabric (or every fabric with --all).
  doctor      Check connectivity, credentials, and fabric visibility.
```

Verb-level usage and examples: [command reference](docs/commands/README.md).

## Configuration

Precedence: CLI flags → environment variables → YAML → `.env` in cwd.

Settings are scoped per product. See [config.example.yaml](config.example.yaml) and [Configuration](docs/configuration.md) for the full variable list and YAML layout.

## Documentation

| Topic | Link |
| --- | --- |
| Documentation hub | [docs/README.md](docs/README.md) |
| Command reference (global + verbs) | [docs/commands/README.md](docs/commands/README.md) |
| Configuration | [docs/configuration.md](docs/configuration.md) |
| Development | [docs/development.md](docs/development.md) |
| Examples & CI pipeline | [examples/README.md](examples/README.md) |

## Development

Contributors: see [Development](docs/development.md).
