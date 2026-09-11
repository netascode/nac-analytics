# Examples

Optional **lab reference material** for trying change-analysis workflows against a live fabric. Examples are organized by Cisco product under subdirectories; they are **not** installed by PyPI and **not** run by this repository's GitHub Actions CI.

| Product | Directory |
| --- | --- |
| Nexus Dashboard | [nexus_dashboard/README.md](nexus_dashboard/README.md) |

**Config templates** (required for use) live under each product's `config/` subdirectory — not optional lab material. For Nexus Dashboard, copy [config.example.yaml](nexus_dashboard/config/config.example.yaml) and [env.example](nexus_dashboard/config/env.example) to `nac-analytics.yaml` and `.env` in your working directory.

**Lab scripts** in the rest of this directory are optional. Install from PyPI and use the templates above; you do not need Terraform or pipeline scripts for normal use.

Future products will get their own subdirectories under `examples/` following the same layout.
