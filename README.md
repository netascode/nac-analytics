# nac-analytics

> Today this tool covers Cisco ACI via Nexus Dashboard 4.2.1+; the intent is to grow beyond Nexus Dashboard and add support for additional Cisco products, so one tool can drive change analytics across platforms.

CLI for change analysis on Cisco ACI fabrics via Nexus Dashboard 4.2.1+.

Commands are grouped per Cisco product: `nac-analytics <product> <command>`.


## Example output

**delta** — compare snapshots after a change:

```bash
$ nac-analytics nd delta -output text

command: delta
fabric: FABRIC-A
pre_snapshot: snap-pre
post_snapshot: snap-post

=== Summary (/deltaAnalysis/summary) ===

New anomalies by severity:
  major     2

FAIL: New anomalies at or above the failure threshold: 2 major.

=== Resources (/deltaAnalysis/resources) ===
resourceType           new       removed       earlier         later
      tenant             1             0            12            13

=== Anomalies (/anomalies/details) ===
  severity     mnemonic                         resource              reason
  major        ENDPOINT_DUPLICATE_IP            web-epg              duplicate ip detected
```

**compliance** — rule status for the latest snapshot (by default, latest snapshot is used):

```bash
$ nac-analytics nd compliance -output text

command: compliance
fabric: FABRIC-A
snapshot: latest

Compliance:
  scope: latest snapshot
  enforced_rules: 42
  violated_rules: 1
  violating_rules:
    ruleName=no-open-tenant  ruleType=configuration  violationsCount=1
```

See [prechange](https://github.com/netascode/nac-analytics/blob/main/docs/commands/nexus-dashboard/prechange.md), [delta](https://github.com/netascode/nac-analytics/blob/main/docs/commands/nexus-dashboard/delta.md), and [compliance](https://github.com/netascode/nac-analytics/blob/main/docs/commands/nexus-dashboard/compliance.md) for usage.

## Installation

**Requirements:** Nexus Dashboard 4.2.1+, Python 3.10+, an ACI fabric registered in Nexus Dashboard.

Install from PyPI:

```bash
pip install nac-analytics
nac-analytics --help
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install nac-analytics
nac-analytics --help
```

## Quick start

```bash
nac-analytics init
# edit nac-analytics.yaml and .env
nac-analytics nd doctor
```

After `pip install`, `init` writes `./nac-analytics.yaml` and `./.env` from bundled templates. Git clone users can copy from [examples/nexus_dashboard/config/](https://github.com/netascode/nac-analytics/tree/main/examples/nexus_dashboard/config) instead. See [examples](https://github.com/netascode/nac-analytics/blob/main/examples/README.md) only for optional lab scripts (Terraform, CI walkthrough).


## Documentation

| Topic | Link |
| --- | --- |
| Documentation hub | [docs/README.md](https://github.com/netascode/nac-analytics/blob/main/docs/README.md) |
| Nexus Dashboard | [docs/nexus-dashboard.md](https://github.com/netascode/nac-analytics/blob/main/docs/nexus-dashboard.md) |
| Command reference | [docs/commands/README.md](https://github.com/netascode/nac-analytics/blob/main/docs/commands/README.md) |
| Exit codes | [docs/exit-codes.md](https://github.com/netascode/nac-analytics/blob/main/docs/exit-codes.md) |
| Configuration | [docs/configuration.md](https://github.com/netascode/nac-analytics/blob/main/docs/configuration.md) |
| Examples (optional lab scripts) | [examples/README.md](https://github.com/netascode/nac-analytics/blob/main/examples/README.md) |