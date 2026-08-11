# compliance

[← Nexus Dashboard commands](README.md) · [Command reference](../README.md)

Report compliance rule status for a fabric. Use `--all` to check every fabric listed in YAML `fabrics` (or the single default fabric). Exits **3** with `--fail-on-violations` when any rule is violated.

## Examples

```bash
nac-analytics nd compliance
nac-analytics nd compliance --all --fail-on-violations
nac-analytics nd compliance -snapshot latest-1 -output junit
```

Run `nac-analytics nd compliance --help` for all flags and options.
