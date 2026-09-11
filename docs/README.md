# Documentation

Reference material for **nac-analytics** — change analytics for Cisco products.

## Topics

| Topic | Description |
| --- | --- |
| [Nexus Dashboard](nexus-dashboard.md) | Product overview, `--help`, and command index |
| [Command reference](commands/README.md) | Global CLI help and per-verb guides |
| [Exit codes](exit-codes.md) | CI exit codes for gate and compliance commands |
| [Configuration](configuration.md) | YAML layout, environment variables, precedence |
| [Contributing](contributing.md) | Development setup, tests, and releases |
| [Examples](../examples/README.md) | Optional lab scripts and sample configs (not required for normal use) |

## CLI shape

```bash
nac-analytics <product> <verb> [options]
nac-analytics version
```

Today the only product is **nexus-dashboard** (`nd`). Product groups carry their own configuration namespace and command set.
