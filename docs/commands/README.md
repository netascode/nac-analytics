# Command reference

[← Documentation hub](../README.md)

The CLI exposes help at three levels. Run `--help` at each tier, or see the excerpts below.

| Level | Invocation | Document |
| --- | --- | --- |
| 1 — Global | `nac-analytics --help` | This page |
| 2 — Product | `nac-analytics nexus-dashboard --help` | [README § Nexus Dashboard](../../README.md#nexus-dashboard-commands) |
| 3 — Verb | `nac-analytics nexus-dashboard <verb> --help` | [Nexus Dashboard commands](nexus-dashboard/README.md) |

## Global help

```
$ nac-analytics --help

Usage: nac-analytics [OPTIONS] COMMAND [ARGS]...

Change analytics for Cisco products.

Run a product group followed by a command, for example:

  nac-analytics nexus-dashboard doctor      (alias: nd)

Each product carries its own commands and configuration; see
`nac-analytics <product> --help`. Products available today are listed below;
more Cisco products are planned.

Options:
  --help          Show this message and exit.

Commands:
  version          Print the version and exit.
  nexus-dashboard  Change analysis for Cisco Nexus Dashboard 4.2.1+ (GA REST APIs, ACI).
```

## Nexus Dashboard verbs

| Verb | Purpose |
| --- | --- |
| [prechange](nexus-dashboard/prechange.md) | Analyse a candidate config against current fabric state |
| [delta](nexus-dashboard/delta.md) | Compare two snapshots and report changes |
| [snapshots](nexus-dashboard/snapshots.md) | Resolve a snapshot ID (CI baseline pinning) |
| [compliance](nexus-dashboard/compliance.md) | Report compliance rule status |
| [doctor](nexus-dashboard/doctor.md) | Check connectivity, credentials, fabric visibility |
