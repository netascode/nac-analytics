#!/usr/bin/env bash
# Nexus Dashboard full change-analysis pipeline (live ND + terraform apply).
# Uses nac-analytics nd (via _lib.sh) for snapshots, prechange, and delta.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=examples/nexus_dashboard/_lib.sh
source "$ROOT/examples/nexus_dashboard/_lib.sh"

PLAN="${PLAN_FILE:-$DEFAULT_PLAN_FILE}"

resolve_nac_analytics

if [[ ! -f "$PLAN" ]]; then
  echo "error: plan file not found: $PLAN" >&2
  echo "Generate from examples/nexus_dashboard/terraform:" >&2
  echo "  cd examples/nexus_dashboard/terraform && terraform plan -out=plan.tfplan" >&2
  echo "  terraform show -json plan.tfplan > plan.json" >&2
  echo "Then: PLAN_FILE=examples/nexus_dashboard/terraform/plan.json $0" >&2
  exit 1
fi

echo "==> pin baseline (latest, before apply)"
SNAPSHOT_ID=$("${NAC_ANALYTICS[@]}" snapshots latest)
test -n "$SNAPSHOT_ID"
echo "snapshot_id=$SNAPSHOT_ID"

echo "==> prechange gate"
"${NAC_ANALYTICS[@]}" prechange "$PLAN"
test -f prechange-report.xml

echo "==> apply (in examples/nexus_dashboard/terraform: terraform apply plan.tfplan, then confirm)"
read -r -p "Apply complete? [y/N] " confirm
if [[ "$confirm" != [yY] ]]; then
  echo "Aborted."
  exit 1
fi

echo "==> post-apply delta"
"${NAC_ANALYTICS[@]}" delta "$SNAPSHOT_ID"
test -f delta-report.xml

echo "PASS: full pipeline complete"
