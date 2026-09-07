"""End-to-end command bodies with an in-process mock transport.

These drive the Typer commands the way a user would, but route every HTTP
call through ``httpx.MockTransport`` so the CLI orchestration, the delta
pipeline and the compliance run path are all exercised without a network.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from nac_analytics.cli import app
from nac_analytics.core.exceptions import AnomalyThresholdError
from nac_analytics.products.nexus_dashboard.client import NDClient as RealNDClient
from tests.conftest import Lab, json_response

runner = CliRunner()

ENV = {
    "ND_HOST": "nd.example.com",
    "ND_USER": "admin",
    "ND_PASSWORD": "s3cr3t",
    "ND_FABRIC": "FABRIC-A",
    "ND_VERIFY_SSL": "false",
}

FABRICS_PATH = "/api/v1/manage/fabrics"
SNAPSHOTS_PATH = "/api/v1/analyze/fabricSnapshots"
LOGIN_DOMAINS_PATH = "/api/v1/infra/logindomains"
PRECHANGE_CREATE_PATH = "/api/v1/analyze/jobs/prechangeAnalysis/file"
PRECHANGE_JOB_PATH = "/api/v1/analyze/jobs/prechangeAnalysis/pc-1"
PRECHANGE_LIST_PATH = "/api/v1/analyze/jobs/prechangeAnalysis"
DELTA_CREATE_PATH = "/api/v1/analyze/jobs/deltaAnalysis"
JOBS_SUMMARY_PATH = "/api/v1/analyze/jobs/summary"
DELTA_SUMMARY_PATH = "/api/v1/analyze/deltaAnalysis/summary"
DELTA_RESOURCES_PATH = "/api/v1/analyze/deltaAnalysis/resources"
DELTA_POLICY_DIFF_PATH = "/api/v1/analyze/deltaAnalysis/policyDiff"
ANOMALY_DETAILS_PATH = "/api/v1/analyze/anomalies/details"
COMPLIANCE_SUMMARY_PATH = "/api/v1/analyze/complianceReport/summary"
COMPLIANCE_RULES_PATH = "/api/v1/analyze/complianceReport/ruleDetails"

SNAP_PRE = {
    "snapshotId": "snap-pre",
    "collectionTimestamp": "2026-08-07T10:00:00Z",
    "analysisTimestamp": "2026-08-07T10:01:00Z",
    "status": "finished",
    "snapshotType": "online",
}
SNAP_POST = {
    "snapshotId": "snap-post",
    "collectionTimestamp": "2026-08-07T12:00:00Z",
    "analysisTimestamp": "2026-08-07T12:01:00Z",
    "status": "finished",
    "snapshotType": "online",
}


def _summary(new_critical: int = 0) -> dict:
    severities = ("critical", "major", "minor", "warning", "info", "unknown")
    return {
        "newAnomaliesCount": new_critical,
        "anomalyCountBySeverity": [
            {
                "severity": severity,
                "newCount": new_critical if severity == "critical" else 0,
                "clearedCount": 0,
                "unchangedCount": 0,
                "earlierCount": 0,
                "laterCount": 0,
            }
            for severity in severities
        ],
    }


def _compliance_summary(timestamp: str, *, violated: int = 0) -> dict:
    return {
        "collectionTimestamp": timestamp,
        "ruleCountByStatus": {"enforcedCount": 5, "violatedCount": violated},
        "ruleCountByType": {"communication": 2, "configuration": 3},
    }


def build_lab(*, new_critical: int = 0, violated: int = 0) -> Lab:
    prechange_job = {
        "jobId": "pc-1",
        "name": "pc-1",
        "fabricName": "FABRIC-A",
        "analysisStatus": "completed",
        "analysisScheduleId": "sched-1",
        "baseSnapshotId": "snap-pre",
        "spanshotDeltaJobId": "delta-1",
        "uploadedFileName": "plan.json",
    }
    return Lab(
        {
            FABRICS_PATH: json_response(
                {"fabrics": [{"name": "FABRIC-A", "management": {"type": "aci"}}]}
            ),
            SNAPSHOTS_PATH: json_response({"snapshots": [SNAP_POST, SNAP_PRE]}),
            LOGIN_DOMAINS_PATH: json_response(
                {"defaultDomain": "DefaultAuth", "domains": [{"name": "DefaultAuth"}]}
            ),
            PRECHANGE_CREATE_PATH: json_response({"data": {"jobId": "pc-1"}}),
            PRECHANGE_LIST_PATH: json_response({"entries": []}),
            PRECHANGE_JOB_PATH: json_response(prechange_job),
            DELTA_CREATE_PATH: json_response({"jobId": "delta-1"}),
            JOBS_SUMMARY_PATH: json_response(
                {"entries": [{"jobId": "delta-1", "status": "COMPLETE"}]}
            ),
            DELTA_SUMMARY_PATH: json_response(_summary(new_critical)),
            DELTA_RESOURCES_PATH: json_response(
                {"resources": [{"resourceType": "fvBD", "new": 1, "removed": 0}]}
            ),
            DELTA_POLICY_DIFF_PATH: json_response({"lines": []}),
            ANOMALY_DETAILS_PATH: json_response({"anomalies": []}),
            COMPLIANCE_SUMMARY_PATH: json_response(
                _compliance_summary("2026-08-07T10:01:00Z", violated=violated)
            ),
            COMPLIANCE_RULES_PATH: json_response(
                {
                    "collectionTimestamp": "2026-08-07T10:01:00Z",
                    "rules": [
                        {
                            "ruleName": "r1",
                            "ruleType": "configuration",
                            "violationsCount": violated,
                        }
                    ],
                }
            ),
        }
    )


@pytest.fixture
def use_lab(monkeypatch: pytest.MonkeyPatch) -> object:
    """Patch the CLI's client so every request routes through a Lab."""

    def install(lab: Lab) -> None:
        def factory(config: object, **_: object) -> RealNDClient:
            http = httpx.Client(transport=httpx.MockTransport(lab))
            return RealNDClient(config, http=http)  # type: ignore[arg-type]

        monkeypatch.setattr(
            "nac_analytics.products.nexus_dashboard.cli.NDClient", factory
        )

    return install


def test_doctor_reports_connectivity(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(build_lab())

    result = runner.invoke(app, ["nd", "doctor", "--output", "json"], env=ENV)

    assert result.exit_code == 0, result.output
    assert "authenticated_as" in result.output


def test_snapshots_prints_id_only(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(build_lab())

    result = runner.invoke(app, ["nd", "snapshots", "latest"], env=ENV)

    assert result.exit_code == 0, result.output
    # stderr progress notes are merged into output; the ID is the last line.
    assert result.output.strip().splitlines()[-1] == "snap-post"


def test_delta_writes_report_and_passes(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(build_lab())

    result = runner.invoke(app, ["nd", "delta"], env=ENV)

    assert result.exit_code == 0, result.output
    assert (tmp_path / "delta-report.xml").is_file()
    assert "DECISION: PASS" in result.output


def test_delta_fails_on_new_critical(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(build_lab(new_critical=2))

    result = runner.invoke(app, ["nd", "delta"], env=ENV)

    assert result.exit_code == AnomalyThresholdError.exit_code
    assert "DECISION: FAIL" in result.output


def test_prechange_via_job_id_writes_report(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(build_lab())

    result = runner.invoke(app, ["nd", "prechange", "--job-id", "pc-1"], env=ENV)

    assert result.exit_code == 0, result.output
    report = tmp_path / "prechange-report.xml"
    assert report.is_file()
    assert "pc-1" in report.read_text(encoding="utf-8")


def test_prechange_uploads_a_plan(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(build_lab())
    plan = tmp_path / "plan.json"
    plan.write_text('{"imdata": [{"fvTenant": {"attributes": {"name": "X"}}}]}')

    result = runner.invoke(app, ["nd", "prechange", str(plan)], env=ENV)

    assert result.exit_code == 0, result.output
    assert (tmp_path / "prechange-report.xml").is_file()


def test_compliance_single_fabric(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(build_lab())

    result = runner.invoke(app, ["nd", "compliance", "--output", "json"], env=ENV)

    assert result.exit_code == 0, result.output
    assert "violated_rules" in result.output


def test_compliance_fails_on_violations(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(build_lab(violated=1))

    result = runner.invoke(app, ["nd", "compliance", "--fail-on-violations"], env=ENV)

    assert result.exit_code == AnomalyThresholdError.exit_code
