# prechange

[← Nexus Dashboard commands](README.md) · [Command reference](../README.md)

Analyse a candidate configuration against a fabric's current state. Accepts Terraform plan JSON (`terraform show -json plan.tfplan`) or APIC managed-object JSON; Terraform plans are converted automatically.

By default writes JUnit to `prechange-report.xml` and exits **3** when new critical/major anomalies would be introduced. Use `-output text` for a full human-readable report, or `-job-id` to resume an existing analysis without re-uploading.

## Examples

```bash
terraform show -json plan.tfplan > plan.json
nac-analytics nd prechange plan.json
nac-analytics nd prechange plan.json latest-2    # explicit baseline snapshot
nac-analytics nd prechange -output text plan.json
```

Run `nac-analytics nd prechange --help` for all flags and options.
