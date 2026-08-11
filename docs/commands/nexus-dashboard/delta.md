# delta

[← Nexus Dashboard commands](README.md) · [Command reference](../README.md)

Compare two snapshots of a fabric and report what changed. With no arguments, defaults to **latest-1** vs **latest**. Writes JUnit to `delta-report.xml` by default and exits **3** on new critical/major anomalies.

Pin snapshots in CI: capture IDs with [snapshots](snapshots.md), apply your change, then pass both IDs to delta.

## Examples

```bash
nac-analytics nd delta                         # latest-1 vs latest
nac-analytics nd delta abc-123                 # pinned pre, post = latest
nac-analytics nd delta abc-123 def-456         # both pinned
nac-analytics nd delta -output text abc def
```

Run `nac-analytics nd delta --help` for all flags and options.
