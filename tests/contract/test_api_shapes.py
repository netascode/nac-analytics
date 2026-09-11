"""Contract tests replay recorded Nexus Dashboard JSON through MockTransport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from nac_analytics.products.nexus_dashboard.client import NDClient
from tests.conftest import Lab, json_response
from tests.fixtures.nd_paths import (
    COMPLIANCE_SUMMARY_PATH,
    DELTA_SUMMARY_PATH,
    JOBS_SUMMARY_PATH,
    LOGIN_PATH,
    PRECHANGE_JOB_PATH,
    SNAPSHOTS_PATH,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_login_fixture_shape(config) -> None:
    payload = _load("login.json")
    lab = Lab({LOGIN_PATH: json_response(payload)})
    http = httpx.Client(transport=httpx.MockTransport(lab))
    with NDClient(config, http=http) as client:
        client.authenticate()
    assert client.token is not None


def test_delta_summary_fixture_parses(config, make_client) -> None:
    summary = _load("delta_summary.json")
    lab = Lab(
        {
            DELTA_SUMMARY_PATH: json_response(summary),
        }
    )
    client = make_client(lab)
    with client:
        result = client.delta_summary("delta-1")
    assert result["newAnomaliesCount"] == summary["newAnomaliesCount"]


def test_snapshots_list_fixture_resolves_latest(config, make_client) -> None:
    listing = _load("snapshots_list.json")
    lab = Lab(
        {
            SNAPSHOTS_PATH: json_response(listing),
        }
    )
    client = make_client(lab)
    with client:
        record = client.resolve_snapshot("FABRIC-A", "latest")
    assert record["snapshotId"] == "snap-1"


def test_compliance_summary_fixture_parses(config, make_client) -> None:
    summary = _load("compliance_summary.json")
    lab = Lab({COMPLIANCE_SUMMARY_PATH: json_response(summary)})
    client = make_client(lab)
    with client:
        result = client.compliance_summary("FABRIC-A")
    assert (
        result["ruleCountByStatus"]["violatedCount"]
        == summary["ruleCountByStatus"]["violatedCount"]
    )


def test_jobs_summary_fixture_lists_complete_job(config, make_client) -> None:
    payload = _load("jobs_summary_complete.json")
    lab = Lab({JOBS_SUMMARY_PATH: json_response(payload)})
    client = make_client(lab)
    with client:
        entries = client.job_summary(job_id="delta-1")
    assert entries[0]["status"] == "COMPLETE"


def test_prechange_job_fixture_parses(config, make_client) -> None:
    job = _load("prechange_job.json")
    lab = Lab({PRECHANGE_JOB_PATH: json_response(job)})
    client = make_client(lab)
    with client:
        result = client.get_prechange_analysis("pc-1")
    assert result["analysisStatus"] == job["analysisStatus"]
    assert result["baseSnapshotId"] == job["baseSnapshotId"]
