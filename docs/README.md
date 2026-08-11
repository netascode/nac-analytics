# Documentation

Reference material for **nac-analytics** — change analytics for Cisco products.

## Topics

| Topic | Description |
| --- | --- |
| [Command reference](commands/README.md) | Three-tier CLI help: global, product, and per-verb |
| [Configuration](configuration.md) | YAML layout, environment variables, precedence |
| [Development](development.md) | Tests, lint, and contributor workflow |
| [Examples](../examples/README.md) | Sample configs, Terraform pipeline, CI scripts |

## CLI shape

```
nac-analytics <product> <verb> [options]
nac-analytics version
```

Today the only product is **nexus-dashboard** (`nd`). Product groups carry their own configuration namespace and command set; see the [Nexus Dashboard commands](commands/nexus-dashboard/README.md) index.

Architecture notes for the multi-product CLI live in [superpowers/specs/multi-product-cli.md](superpowers/specs/multi-product-cli.md).
