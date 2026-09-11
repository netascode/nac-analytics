"""Nexus Dashboard API path constants for tests."""

from __future__ import annotations

INFRA = "/api/v1/infra"
MANAGE = "/api/v1/manage"
ANALYZE = "/api/v1/analyze"

LOGIN_PATH = f"{INFRA}/login"
LOGIN_DOMAINS_PATH = f"{INFRA}/logindomains"

FABRICS_PATH = f"{MANAGE}/fabrics"

SNAPSHOTS_PATH = f"{ANALYZE}/fabricSnapshots"

ASSURANCE_TRIGGER_PATH = f"{ANALYZE}/jobs/assuranceAnalysis"
JOBS_SUMMARY_PATH = f"{ANALYZE}/jobs/summary"

PRECHANGE_CREATE_PATH = f"{ANALYZE}/jobs/prechangeAnalysis/file"
PRECHANGE_LIST_PATH = f"{ANALYZE}/jobs/prechangeAnalysis"
PRECHANGE_JOB_PATH = f"{ANALYZE}/jobs/prechangeAnalysis/pc-1"

DELTA_CREATE_PATH = f"{ANALYZE}/jobs/deltaAnalysis"
DELTA_SUMMARY_PATH = f"{ANALYZE}/deltaAnalysis/summary"
DELTA_RESOURCES_PATH = f"{ANALYZE}/deltaAnalysis/resources"
DELTA_POLICY_DIFF_PATH = f"{ANALYZE}/deltaAnalysis/policyDiff"

ANOMALY_DETAILS_PATH = f"{ANALYZE}/anomalies/details"

COMPLIANCE_SUMMARY_PATH = f"{ANALYZE}/complianceReport/summary"
COMPLIANCE_RULES_PATH = f"{ANALYZE}/complianceReport/ruleDetails"
