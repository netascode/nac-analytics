# Nexus Dashboard

[← Documentation hub](README.md) · [Command reference](commands/README.md)

Change analysis for Cisco ACI fabrics via Nexus Dashboard 4.2.1+ (GA REST APIs).

Invoke as `nac-analytics nexus-dashboard <verb>` or `nac-analytics nd <verb>`. Verb-level usage: [Nexus Dashboard commands](commands/nexus-dashboard/README.md).

## Product help

```bash
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
  analyze     Trigger an assurance analysis and print the snapshot ID it produces.
  compliance  Report compliance rule status for a fabric (or every fabric with --all).
  doctor      Check connectivity, credentials, and fabric visibility.
```

## Output defaults

| Command kind | Default `--output` |
| --- | --- |
| Gate commands (`prechange`, `delta`) | `junit` → writes `prechange-report.xml` or `delta-report.xml` |
| Other commands (`doctor`, `compliance`, `snapshots`, `analyze`) | `text` |

Use `-output text` on gate commands for human-readable stdout. Quick-start examples use `nd`; reference tables use `nexus-dashboard`.

## Commands

Verb summaries and per-command guides: [Nexus Dashboard commands](commands/nexus-dashboard/README.md).
