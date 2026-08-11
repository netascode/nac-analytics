# Nexus Dashboard commands

[← Command reference](../README.md) · [Documentation hub](../../README.md)

Change analysis for Cisco Nexus Dashboard 4.2.1+ (GA REST APIs, ACI). Invoke as `nac-analytics nexus-dashboard <verb>` or `nac-analytics nd <verb>`.

Product-level help (configuration variables and verb list) is in [Nexus Dashboard](../nexus-dashboard.md).

## Verbs

| Verb | Summary |
| --- | --- |
| [prechange](prechange.md) | Gate a planned change — Terraform plan JSON or APIC MO JSON |
| [delta](delta.md) | Post-change comparison between two snapshots |
| [snapshots](snapshots.md) | Print a snapshot ID for pipeline pinning |
| [compliance](compliance.md) | Fabric compliance rules; optional `--fail-on-violations` |
| [doctor](doctor.md) | Read-only connectivity and credential check |

Run `nac-analytics nd <verb> --help` for full flags and options.
