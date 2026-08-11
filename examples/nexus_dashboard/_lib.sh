# Shared helpers for Nexus Dashboard ci-pipeline scripts.
# Expects ROOT to be set to the repository root before sourcing.

: "${ROOT:?ROOT must be set before sourcing _lib.sh}"

DEFAULT_PLAN_FILE="$ROOT/examples/nexus_dashboard/terraform/plan.json"

# Resolve nac-analytics binary and append the Nexus Dashboard product token (nd).
# Override binary only with NAC_ANALYTICS_BIN (path to bare executable, not including nd).
resolve_nac_analytics() {
  if [[ -n "${NAC_ANALYTICS_BIN:-}" ]]; then
    NAC_ANALYTICS=("$NAC_ANALYTICS_BIN" nd)
  elif [[ -x "$ROOT/.venv/bin/nac-analytics" ]]; then
    NAC_ANALYTICS=("$ROOT/.venv/bin/nac-analytics" nd)
  else
    NAC_ANALYTICS=(uv run nac-analytics nd)
  fi
}
