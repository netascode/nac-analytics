# Exit codes

[← Documentation hub](README.md)

The CLI uses specific exit codes so CI can distinguish error types.

| Code | Meaning |
| --- | --- |
| 0 | Success; threshold not breached |
| 1 | Unexpected error |
| 2 | Analysis job failed, stopped, vanished, or timed out |
| 3 | New anomalies at `--fail-on` (or compliance violations with `--fail-on-violations`) |
| 4 | Bad input, config, or configuration rejected by Nexus Dashboard |
| 5 | Authentication or authorisation failure |

Gate commands (`prechange`, `delta`) default to JUnit on stdout and write reports to `prechange-report.xml` / `delta-report.xml`. Use `-output text` for human-readable output like the examples in the [README](../README.md#example-output).
