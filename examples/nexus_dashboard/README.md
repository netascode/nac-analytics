# Nexus Dashboard examples

Sample configs and scripts for **Cisco Nexus Dashboard** change analysis — not generic `nac-analytics` usage. All CLI invocations use the product prefix:

```bash
nac-analytics nexus-dashboard <verb>   # or: nac-analytics nd <verb>
```

Verb reference: [docs/commands/nexus-dashboard/](../../docs/commands/nexus-dashboard/README.md).

| File / script | Purpose |
| --- | --- |
| `minimal-change.json` | Small APIC MO JSON for trying `nd prechange` without Terraform |
| `terraform/` | Minimal NAC-as-Code project — `data/tenant_nac_analytics_test.nac.yaml`, `env.example` |
| `ci-pipeline.sh` | Full lab pipeline: pin snapshot → prechange → terraform apply → delta |
| `_lib.sh` | Shared plan path and `nac-analytics nd` resolution (sourced by pipeline scripts) |

Do not commit real fabric plans or files that contain credentials or Terraform variable values.

## Terraform full pipeline

From the repo root:

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

Requires a configured `nac-analytics.yaml` and `.env` pointing at a live Nexus Dashboard fabric.

The sample tenant is `NAC_ANALYTICS_TEST` with a single VRF — safe for lab fabrics.
