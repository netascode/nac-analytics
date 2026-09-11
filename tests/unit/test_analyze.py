"""Triggering an assurance analysis and waiting for the snapshot it produces.

The endpoint, the ID vocabulary and the timing here were all confirmed against
a live ND 4.2.1 cluster: `POST /jobs/assuranceAnalysis` answers with a `jobId`
that reappears verbatim as the resulting snapshot's `analysisJobId`.
"""

from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from nac_analytics.cli import app
from nac_analytics.core.exceptions import AuthError, JobError
from nac_analytics.products.nexus_dashboard.client import (
    NDClient as RealNDClient,
)
from nac_analytics.products.nexus_dashboard.client import (
    analysis_job_id,
    snapshot_for_job,
    snapshot_newer_than,
)
from tests.conftest import Lab, json_response
from tests.fixtures.env import ND_TEST_ENV
from tests.fixtures.nd_paths import (
    ASSURANCE_TRIGGER_PATH,
    FABRICS_PATH,
    JOBS_SUMMARY_PATH,
    SNAPSHOTS_PATH,
)

runner = CliRunner()

TRIGGER_PATH = ASSURANCE_TRIGGER_PATH
SUMMARY_PATH = JOBS_SUMMARY_PATH

# The live prefix. The published spec's response example shortens it to
# `ANALYSIS-ACI-`, which does not match what the cluster returns.
JOB_ID = "ONLINE-ANALYSIS-ACI-c6ddb3c8-97b3-11f1-82e2-024ba9b9c180"
# The recurring scheduled analysis keeps one job ID across cycles, so this one
# names several snapshots collected hours apart.
RECURRING_JOB_ID = "ONLINE-ANALYSIS-ACI-c9635808-5e21-11f1-9161-62c5f98b2c1d"

BASELINE = "2026-08-14T07:29:57Z"

ENV = ND_TEST_ENV


def snapshot(
    snapshot_id: str,
    collected: str,
    *,
    job_id: str = RECURRING_JOB_ID,
    status: str = "finished",
) -> dict:
    return {
        "snapshotId": snapshot_id,
        "analysisJobId": job_id,
        "collectionTimestamp": collected,
        "analysisTimestamp": collected.replace(":57Z", ":59Z"),
        "snapshotType": "online",
        "status": status,
        "fabricName": "FABRIC-A",
    }


OLD = snapshot("snap-old", "2026-08-14T05:29:57Z")
BASE = snapshot("snap-base", BASELINE)
FRESH = snapshot("snap-fresh", "2026-08-14T07:46:36Z", job_id=JOB_ID)


def job(status: str, **extra: object) -> dict:
    return {
        "jobId": JOB_ID,
        "jobType": "ONLINE-ANALYSIS-ACI",
        "status": status,
        **extra,
    }


def analysis_lab(
    *,
    snapshots: list[dict] | list[list[dict]],
    jobs: list[dict] | None = None,
    trigger: httpx.Response | None = None,
) -> Lab:
    """A cluster that answers the trigger, the job poll and the snapshot list.

    `snapshots` may be a list of records, or a list of successive listings so a
    test can make a snapshot appear part-way through the polling. `jobs=[]`
    means the job summary knows nothing of the job; the default is a job that
    has already finished.
    """
    if snapshots and isinstance(snapshots[0], list):
        listings = [json_response({"snapshots": page}) for page in snapshots]
    else:
        listings = [json_response({"snapshots": snapshots})]
    entries = [job("COMPLETE")] if jobs is None else jobs
    return Lab(
        {
            FABRICS_PATH: json_response(
                {"fabrics": [{"name": "FABRIC-A", "management": {"type": "aci"}}]}
            ),
            TRIGGER_PATH: trigger or json_response({"jobId": JOB_ID}),
            SUMMARY_PATH: json_response({"entries": entries}),
            SNAPSHOTS_PATH: listings,
        }
    )


@pytest.fixture(autouse=True)
def virtual_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sleeping advance a fake clock instead of doing nothing.

    The shared `no_sleep` fixture alone would leave a wait that never succeeds
    spinning against the mock cluster for a real timeout's worth of seconds.
    Here a poll costs its own interval and nothing else, so the timeout
    branches are both instant and exact.
    """
    now = [0.0]

    def advance(seconds: float) -> None:
        now[0] += seconds

    monkeypatch.setattr(
        "nac_analytics.products.nexus_dashboard.client.time.monotonic",
        lambda: now[0],
    )
    monkeypatch.setattr(
        "nac_analytics.products.nexus_dashboard.client.time.sleep", advance
    )


# -- the trigger -----------------------------------------------------------


def test_the_trigger_posts_only_the_fabric_name(make_client) -> None:
    lab = analysis_lab(snapshots=[FRESH])
    client = make_client(lab)

    assert client.trigger_assurance_analysis("FABRIC-A") == JOB_ID

    request = lab.requests_to(TRIGGER_PATH)[0]
    assert request.method == "POST"
    assert json.loads(request.content) == {"fabricName": "FABRIC-A"}


def test_a_response_without_a_job_id_is_a_job_error() -> None:
    with pytest.raises(JobError, match="returned no jobId"):
        analysis_job_id({})


def test_the_job_id_is_read_verbatim() -> None:
    assert analysis_job_id({"jobId": JOB_ID}) == JOB_ID


# -- matching a job to its snapshot ----------------------------------------


def test_the_snapshot_is_matched_on_analysis_job_id() -> None:
    found = snapshot_for_job([BASE, FRESH, OLD], JOB_ID, newer_than=BASELINE)

    assert found is not None
    assert found["snapshotId"] == "snap-fresh"


def test_the_newest_snapshot_wins_when_a_job_id_names_several() -> None:
    """The recurring analysis reuses one job ID, so a match is not unique."""
    newer = snapshot("snap-newer", "2026-08-14T09:29:57Z")

    found = snapshot_for_job([OLD, newer, BASE], RECURRING_JOB_ID, newer_than=BASELINE)

    assert found is not None
    assert found["snapshotId"] == "snap-newer"


def test_a_matching_snapshot_older_than_the_baseline_is_refused() -> None:
    """Guards the stale-snapshot bug this command exists to prevent.

    Were a trigger ever coalesced into an already-running scheduled job, its
    ID would match snapshots collected before the trigger.
    """
    assert snapshot_for_job([OLD, BASE], RECURRING_JOB_ID, newer_than=BASELINE) is None


def test_any_snapshot_qualifies_when_the_fabric_had_none() -> None:
    found = snapshot_for_job([FRESH], JOB_ID, newer_than=None)

    assert found is not None
    assert found["snapshotId"] == "snap-fresh"


def test_the_newest_snapshot_past_the_baseline_is_the_fallback() -> None:
    assert snapshot_newer_than([OLD, BASE], BASELINE) is None
    found = snapshot_newer_than([OLD, BASE, FRESH], BASELINE)
    assert found is not None
    assert found["snapshotId"] == "snap-fresh"


# -- waiting ---------------------------------------------------------------


def test_the_job_is_polled_by_id_and_not_by_type(make_client) -> None:
    """`jobType` varies with the fabric, so only the ID is a reliable filter."""
    client = make_client(analysis_lab(snapshots=[FRESH, BASE]))

    client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)

    params = lab_params(client, SUMMARY_PATH)
    assert params["jobId"] == JOB_ID
    assert "jobTypes" not in params


def lab_params(client, path: str) -> httpx.QueryParams:
    transport = client.client._transport
    lab = transport.handler
    return lab.requests_to(path)[0].url.params


@pytest.mark.parametrize("status", ["COMPLETE", "SUCCESS"])
def test_both_success_values_are_accepted(make_client, status: str) -> None:
    lab = analysis_lab(snapshots=[FRESH, BASE], jobs=[job(status)])
    client = make_client(lab)

    record = client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)

    assert record["snapshotId"] == "snap-fresh"


def test_a_failed_job_reports_the_api_error_message(make_client) -> None:
    lab = analysis_lab(
        snapshots=[BASE],
        jobs=[job("FAILED", errorMessage="leaf-101 unreachable")],
    )
    client = make_client(lab)

    with pytest.raises(JobError, match="leaf-101 unreachable"):
        client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)


def test_a_partial_collection_explains_why_its_snapshot_is_unusable(
    make_client,
) -> None:
    lab = analysis_lab(snapshots=[BASE], jobs=[job("PARTIALLY_FAILED")])
    client = make_client(lab)

    with pytest.raises(JobError, match="not 'finished'"):
        client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)


def test_a_job_that_is_never_listed_is_a_job_error(make_client) -> None:
    """/jobs/summary answers 200 with no entries for a job that does not exist."""
    lab = analysis_lab(snapshots=[BASE], jobs=[])
    client = make_client(lab)

    with pytest.raises(JobError, match="never reported"):
        client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)


def test_the_wait_continues_until_the_snapshot_lands(make_client) -> None:
    """No snapshot is visible until the job is terminal, so the list lags."""
    lab = analysis_lab(snapshots=[[BASE], [BASE], [FRESH, BASE]])
    client = make_client(lab)

    record = client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)

    assert record["snapshotId"] == "snap-fresh"
    assert len(lab.requests_to(SNAPSHOTS_PATH)) == 3


def test_an_unfinished_snapshot_is_never_returned(make_client) -> None:
    running = snapshot(
        "snap-running", "2026-08-14T07:46:36Z", job_id=JOB_ID, status="inProgress"
    )
    lab = analysis_lab(snapshots=[running, BASE])
    client = make_client(lab, job_timeout_minutes=1, poll_interval_seconds=30)

    with pytest.raises(JobError, match="did not produce a finished snapshot"):
        client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)


def test_the_timeout_message_suggests_raising_it(make_client) -> None:
    lab = analysis_lab(snapshots=[BASE])
    client = make_client(lab, job_timeout_minutes=1, poll_interval_seconds=30)

    with pytest.raises(JobError, match="raise --timeout"):
        client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)


def test_an_unmatched_but_newer_snapshot_is_reported_with_a_warning(
    make_client,
) -> None:
    """Belt-and-braces: live runs match exactly, but a mismatch must be loud."""
    stranger = snapshot("snap-stranger", "2026-08-14T07:46:36Z", job_id="OTHER-JOB")
    lab = analysis_lab(snapshots=[stranger, BASE])
    client = make_client(lab)

    record = client.wait_for_analysis_snapshot("FABRIC-A", JOB_ID, baseline=BASELINE)

    assert record["snapshotId"] == "snap-stranger"
    assert any("OTHER-JOB" in item and JOB_ID in item for item in client.notices)


# -- the command -----------------------------------------------------------


@pytest.fixture
def use_lab(monkeypatch: pytest.MonkeyPatch) -> object:
    def install(lab: Lab) -> None:
        def factory(config: object, **_: object) -> RealNDClient:
            http = httpx.Client(transport=httpx.MockTransport(lab))
            return RealNDClient(config, http=http)  # type: ignore[arg-type]

        monkeypatch.setattr(
            "nac_analytics.products.nexus_dashboard.commands._helpers.NDClient",
            factory,
        )

    return install


def test_analyze_prints_only_the_snapshot_id(use_lab, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    # The first listing is the pre-trigger baseline; the analysis lands after.
    use_lab(analysis_lab(snapshots=[[BASE], [FRESH, BASE]]))

    result = runner.invoke(app, ["nd", "analyze"], env=ENV)

    assert result.exit_code == 0, result.output
    assert result.output.strip().splitlines()[-1] == "snap-fresh"


def test_analyze_emits_the_whole_record_as_json(use_lab, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(analysis_lab(snapshots=[[BASE], [FRESH, BASE]]))

    result = runner.invoke(app, ["nd", "analyze", "-o", "json"], env=ENV)

    assert result.exit_code == 0, result.output
    assert JOB_ID in result.output


def test_a_snapshot_that_already_existed_is_never_reported(
    use_lab, tmp_path, monkeypatch
) -> None:
    """The baseline is read before the trigger, so `latest` cannot satisfy it."""
    monkeypatch.chdir(tmp_path)
    use_lab(analysis_lab(snapshots=[FRESH, BASE]))

    result = runner.invoke(app, ["nd", "analyze"], env=ENV)

    assert result.exit_code == JobError.exit_code
    assert "did not produce a finished snapshot" in result.output


def test_no_wait_prints_the_job_id_without_polling(
    use_lab, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    lab = analysis_lab(snapshots=[FRESH, BASE])
    use_lab(lab)

    result = runner.invoke(app, ["nd", "analyze", "--no-wait"], env=ENV)

    assert result.exit_code == 0, result.output
    assert result.output.strip().splitlines()[-1] == JOB_ID
    assert lab.requests_to(SUMMARY_PATH) == []
    # Only the fabric validation reads snapshots; no baseline, no polling.
    assert lab.requests_to(SNAPSHOTS_PATH) == []


def test_a_forbidden_trigger_names_the_roles_required(
    use_lab, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    use_lab(
        analysis_lab(
            snapshots=[BASE],
            trigger=json_response({"message": "access denied"}, 403),
        )
    )

    result = runner.invoke(app, ["nd", "analyze"], env=ENV)

    assert result.exit_code == AuthError.exit_code
    assert "fabric-admin" in result.output
    assert "observer" in result.output
