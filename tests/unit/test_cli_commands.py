"""End-to-end command bodies with an in-process mock transport.

These drive the Typer commands the way a user would, but route every HTTP
call through ``httpx.MockTransport`` so the CLI orchestration, the delta
pipeline and the compliance run path are all exercised without a network.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from nac_analytics.cli import app
from nac_analytics.core.exceptions import AnomalyThresholdError, InputError
from nac_analytics.products.nexus_dashboard import settings as nd_settings
from nac_analytics.products.nexus_dashboard.settings import (
    apply_settings,
    load_settings,
    select_product_section,
)
from tests.conftest import Lab, json_response
from tests.fixtures.env import ND_TEST_ENV
from tests.fixtures.nd_paths import (
    ANOMALY_DETAILS_PATH,
    COMPLIANCE_RULES_PATH,
    COMPLIANCE_SUMMARY_PATH,
    DELTA_CREATE_PATH,
    DELTA_POLICY_DIFF_PATH,
    DELTA_RESOURCES_PATH,
    DELTA_SUMMARY_PATH,
    FABRICS_PATH,
    JOBS_SUMMARY_PATH,
    LOGIN_DOMAINS_PATH,
    PRECHANGE_CREATE_PATH,
    PRECHANGE_JOB_PATH,
    PRECHANGE_LIST_PATH,
    SNAPSHOTS_PATH,
)

runner = CliRunner()

ENV = ND_TEST_ENV


@pytest.fixture(autouse=True)
def reset_nd_settings() -> Iterator[None]:
    saved = os.environ.copy()
    nd_settings._configured_fabrics = []
    nd_settings._loaded_config_path = None
    yield
    os.environ.clear()
    os.environ.update(saved)
    nd_settings._configured_fabrics = []
    nd_settings._loaded_config_path = None


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


def _write_config(
    tmp_path: Path,
    *,
    fabrics: list[str] | None = None,
    include_fabric: bool = True,
) -> None:
    lines = [
        "nexus_dashboard:",
        "  host: nd.test",
        "  verify_ssl: false",
    ]
    if include_fabric and fabrics is None:
        lines.append("  fabric: FABRIC-A")
    if fabrics is not None:
        lines.append("  fabrics:")
        lines.extend(f"    - {name}" for name in fabrics)
    (tmp_path / "nac-analytics.yaml").write_text("\n".join(lines) + "\n")


def _load_config(tmp_path: Path) -> None:
    path = tmp_path / "nac-analytics.yaml"
    apply_settings(select_product_section(load_settings(path), path=path), path=path)


def _compliance_route(*, violated_by_fabric: dict[str, int]) -> object:
    def handler(request: httpx.Request) -> httpx.Response:
        fabric = request.url.params.get("fabricName", "FABRIC-A")
        violated = violated_by_fabric.get(fabric, 0)
        timestamp = "2026-08-07T10:01:00Z"
        if request.url.path.endswith("/summary"):
            return json_response(_compliance_summary(timestamp, violated=violated))
        return json_response(
            {
                "collectionTimestamp": timestamp,
                "rules": [
                    {
                        "ruleName": "r1",
                        "ruleType": "configuration",
                        "violationsCount": violated,
                    }
                ],
            }
        )

    return handler


def build_multi_fabric_lab(*, violated_by_fabric: dict[str, int] | None = None) -> Lab:
    violated = violated_by_fabric or {"FABRIC-A": 0, "FABRIC-B": 0}
    return Lab(
        {
            FABRICS_PATH: json_response(
                {
                    "fabrics": [
                        {"name": "FABRIC-A", "management": {"type": "aci"}},
                        {"name": "FABRIC-B", "management": {"type": "aci"}},
                    ]
                }
            ),
            SNAPSHOTS_PATH: json_response({"snapshots": [SNAP_POST, SNAP_PRE]}),
            LOGIN_DOMAINS_PATH: json_response(
                {"defaultDomain": "DefaultAuth", "domains": [{"name": "DefaultAuth"}]}
            ),
            COMPLIANCE_SUMMARY_PATH: _compliance_route(violated_by_fabric=violated),
            COMPLIANCE_RULES_PATH: _compliance_route(violated_by_fabric=violated),
        }
    )


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


def test_compliance_all_reports_every_configured_fabric(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, fabrics=["FABRIC-A", "FABRIC-B"])
    _load_config(tmp_path)
    use_lab(build_multi_fabric_lab())

    result = runner.invoke(
        app, ["nd", "compliance", "--all", "--output", "json"], env=ENV
    )

    assert result.exit_code == 0, result.output
    assert "FABRIC-A" in result.output
    assert "FABRIC-B" in result.output


def test_compliance_all_fails_on_violations_when_any_fabric_violates(
    use_lab, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, fabrics=["FABRIC-A", "FABRIC-B"])
    _load_config(tmp_path)
    use_lab(build_multi_fabric_lab(violated_by_fabric={"FABRIC-A": 0, "FABRIC-B": 1}))

    result = runner.invoke(
        app, ["nd", "compliance", "--all", "--fail-on-violations"], env=ENV
    )

    assert result.exit_code == AnomalyThresholdError.exit_code
    assert "FABRIC-B" in result.output


def test_compliance_all_without_fabrics_exits_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, include_fabric=False)
    _load_config(tmp_path)
    env = {key: value for key, value in ENV.items() if key != "ND_FABRIC"}

    result = runner.invoke(app, ["nd", "compliance", "--all"], env=env)

    assert result.exit_code == InputError.exit_code
    assert "requires fabrics" in result.output
