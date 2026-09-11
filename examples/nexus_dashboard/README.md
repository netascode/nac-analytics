# Nexus Dashboard examples

[← Examples hub](../README.md)

> **Optional lab material.** Nothing here is required to use `nac-analytics` after `pip install`. These files are not bundled on PyPI and are not executed by [`.github/workflows/test.yml`](../../.github/workflows/test.yml).

Sample configs and scripts for **Cisco Nexus Dashboard** change analysis. All CLI invocations use the product prefix:

```bash
nac-analytics nexus-dashboard <verb>   # or: nac-analytics nd <verb>
```

Verb reference: [docs/commands/nexus-dashboard/](../../docs/commands/nexus-dashboard/README.md).

## Which path do you need?

| Path | When | Files from this directory |
| --- | --- | --- |
| **Normal use** | Production or your own CI pipeline | None — use `pip install`, `nac-analytics.yaml`, and `.env` only |
| **Quick try** | Exercise `prechange` without Terraform | [`minimal-change.json`](minimal-change.json) |
| **Full lab pipeline** | Walk through snapshot → prechange → apply → delta | [`terraform/`](terraform/), [`ci-pipeline.sh`](ci-pipeline.sh), [`_lib.sh`](_lib.sh) |

## Prerequisites

All paths require:

- Nexus Dashboard 4.2.1+ with an ACI fabric registered
- [`nac-analytics.yaml`](../../config.example.yaml) and [`.env`](../../.env.example) configured for your ND instance

The **full lab pipeline** additionally requires:

- Terraform installed
- APIC credentials for the sample tenant (separate from ND login — see [`terraform/env.example`](terraform/env.example))

## Files

| File / script | Required? | Purpose |
| --- | --- | --- |
| [`minimal-change.json`](minimal-change.json) | Optional | Static APIC MO JSON for `nd prechange` without generating a Terraform plan |
| [`terraform/`](terraform/) | Optional | Minimal NAC tenant (`NAC_ANALYTICS_TEST`); run `terraform plan` to produce `plan.json` for prechange |
| [`ci-pipeline.sh`](ci-pipeline.sh) | Optional | Interactive lab script: pin snapshot → prechange → you apply Terraform → delta |
| [`_lib.sh`](_lib.sh) | Internal | Helper sourced by `ci-pipeline.sh`; resolves `nac-analytics` from venv, `PATH`, or `uv run`. Do not run directly |

Do not commit real fabric plans or files that contain credentials or Terraform variable values.

## Quick try (no Terraform)

From the repo root, with ND configured:

```bash
nac-analytics nd prechange examples/nexus_dashboard/minimal-change.json -output text
```

## Full pipeline (Terraform + apply)

Generate a plan, then run the interactive pipeline script:

```bash
cp examples/nexus_dashboard/terraform/env.example examples/nexus_dashboard/terraform/env.sh
# edit env.sh — APIC URL and credentials (may differ from nac-analytics .env)
source examples/nexus_dashboard/terraform/env.sh

cd examples/nexus_dashboard/terraform
terraform init
terraform plan -out=plan.tfplan
terraform show -json plan.tfplan > plan.json
cd ../..

PLAN_FILE=examples/nexus_dashboard/terraform/plan.json ./examples/nexus_dashboard/ci-pipeline.sh
# When prompted: cd examples/nexus_dashboard/terraform && terraform apply plan.tfplan
# Then confirm with y for post-apply delta
```

The script pauses for you to apply the plan manually, then runs post-change delta. Gate commands write JUnit XML reports to the current directory by default.

## What this is not

- Not a production deployment pattern — for learning and lab validation only
- Not wired into `.github/workflows/` — repo CI runs unit tests and lint only
- Not a substitute for your own CI integration — copy the command sequence, not the shell script, into your pipeline

The sample tenant is `NAC_ANALYTICS_TEST` with a single VRF — safe for lab fabrics.
