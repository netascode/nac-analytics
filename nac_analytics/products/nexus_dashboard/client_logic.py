"""Pure Nexus Dashboard client helpers (snapshots, jobs, compliance checks).

HTTP transport lives in ``client.NDClient``; these functions are unit-tested
without mocks for every call path.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import httpx

from nac_analytics.core.exceptions import ApiError, AuthError, InputError, JobError

INFRA = "/api/v1/infra"
MANAGE = "/api/v1/manage"
ANALYZE = "/api/v1/analyze"

LOGIN_PATH = f"{INFRA}/login"
REFRESH_PATH = f"{INFRA}/refresh"
LOGIN_DOMAINS_PATH = f"{INFRA}/logindomains"

# /fabricSnapshots returns at most 50 records and ignores paging parameters.
# Use startDate/endDate to reach older snapshots.
SNAPSHOT_RECORD_CAP = 50

# Pre-change status values are lower case.
PRECHANGE_COMPLETED = "completed"
PRECHANGE_FAILED = frozenset({"failed", "stopped"})
# A draft that was saved but never submitted. It never becomes terminal.
PRECHANGE_DRAFT = "saved"

# Delta status values are upper case, and the success value is `COMPLETE`.
DELTA_JOB_TYPE = "EPOCH-DELTA-ANALYSIS"
DELTA_SUCCEEDED = "COMPLETE"
DELTA_FAILED = frozenset(
    {"FAILED", "STOPPED", "ABORTED", "PARTIALLY_FAILED", "UNAVAILABLE"}
)

# How long a job may stay absent before it is treated as non-existent.
# /jobs/summary returns HTTP 200 with an empty `entries` array for a job that
# does not exist, so absence is indistinguishable from a job not yet listed.
ABSENCE_GRACE_SECONDS = 60

# How far a compliance report's `collectionTimestamp` may sit from the one
# requested. The API resolves a requested timestamp to the nearest collection
# and returns all-zero counts for a meaningless one, so the returned value is
# compared against the request. 900s covers the lag between a snapshot and its
# compliance run.
COMPLIANCE_TIMESTAMP_TOLERANCE_SECONDS = 900

# Maximum fabric names listed in an unknown-fabric error.
FABRIC_NAME_LIST_LIMIT = 20

_LATEST_RE = re.compile(r"^latest(?:-(\d+))?$", re.IGNORECASE)


def as_dict(value: Any) -> dict[str, Any]:
    """Coerce a decoded JSON value to a mapping."""
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[dict[str, Any]]:
    """Coerce a decoded JSON value to a list of mappings."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def token_from_auth_response(body: dict[str, Any]) -> str:
    """Extract the session token from a login or refresh response.

    Login returns `jwttoken` and `token`; refresh returns `jwttoken` only.
    """
    token = body.get("jwttoken") or body.get("token")
    if not token:
        raise AuthError(
            "Nexus Dashboard accepted the credentials but returned no jwttoken."
        )
    return str(token)


def extract_api_error(response: httpx.Response) -> tuple[str, str]:
    """Return the `(code, message)` an error response carries.

    Endpoints use several envelopes, so each is tried in turn.
    """
    try:
        body = response.json()
    except ValueError:
        return "", response.text.strip()[:500]
    payload = as_dict(body)
    for key in ("error", "data"):
        nested = as_dict(payload.get(key))
        if nested.get("message") or nested.get("code"):
            payload = nested
            break
    else:
        errors = as_list(payload.get("errors"))
        if errors:
            payload = errors[0]
    code = payload.get("code", "")
    message = payload.get("message") or payload.get("detail") or ""
    if not message:
        return str(code or ""), response.text.strip()[:500]
    return str(code or ""), str(message)


def parse_timestamp(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp, tolerating the `Z` suffix ND emits."""
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def fabric_name(fabric: dict[str, Any]) -> str:
    """Return a fabric inventory record's name.

    /manage/fabrics spells this field `name`; other endpoints use `fabricName`.
    """
    return str(fabric.get("name", ""))


def is_aci_fabric(fabric: dict[str, Any]) -> bool:
    """True if this inventory record describes an ACI fabric."""
    return str(as_dict(fabric.get("management")).get("type", "")).lower() == "aci"


def format_fabric_names(names: list[str], limit: int = FABRIC_NAME_LIST_LIMIT) -> str:
    """Render known fabric names for an error message, capping a long list."""
    ordered = sorted(names)
    if len(ordered) <= limit:
        return ", ".join(ordered)
    return f"{', '.join(ordered[:limit])} (+{len(ordered) - limit} more)"


def sort_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order snapshots newest first.

    The API does not guarantee an order. `collectionTimestamp` is ISO-8601, so
    lexicographic ordering is chronological.
    """
    return sorted(
        snapshots,
        key=lambda record: str(record.get("collectionTimestamp", "")),
        reverse=True,
    )


def finished_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only snapshots whose assurance analysis finished.

    `status` is returned lower case, so the comparison is case-insensitive.
    """
    return [
        record
        for record in snapshots
        if str(record.get("status", "")).lower() == "finished"
    ]


def select_snapshot(snapshots: list[dict[str, Any]], selector: str) -> dict[str, Any]:
    """Resolve `latest`, `latest-N` or an explicit snapshot ID.

    `latest` is the newest snapshot, `latest-1` the one before it, and so on.
    """
    ordered = sort_snapshots(snapshots)
    wanted = selector.strip()
    match = _LATEST_RE.match(wanted)
    if match:
        offset = int(match.group(1) or 0)
        if offset >= len(ordered):
            raise InputError(
                f"Cannot select '{wanted}': only {len(ordered)} finished "
                "snapshot(s) are available. Widen the window with --since, or "
                "choose a smaller offset."
            )
        return ordered[offset]
    for record in ordered:
        if str(record.get("snapshotId", "")) == wanted:
            return record
    raise InputError(
        f"Snapshot '{wanted}' was not found among the {len(ordered)} finished "
        "snapshot(s) available. Use 'latest', 'latest-N' or a snapshotId from "
        "an earlier run."
    )


def resolve_snapshot_ids(
    prior: dict[str, Any], later: dict[str, Any]
) -> tuple[str, str]:
    """Map two snapshot records to the IDs `POST /jobs/deltaAnalysis` expects.

    `priorEpochUuid` and `laterEpochUuid` take the `snapshotId` verbatim.
    """
    prior_id = str(prior.get("snapshotId", ""))
    later_id = str(later.get("snapshotId", ""))
    if not prior_id or not later_id:
        raise InputError("Both snapshots must carry a snapshotId to compare them.")
    if prior_id == later_id:
        raise InputError(
            "The pre and post snapshots are the same "
            f"({prior_id}); there is nothing to compare."
        )
    return prior_id, later_id


def prechange_delta_job_id(job: dict[str, Any]) -> str:
    """Return the delta job ID of a completed pre-change analysis.

    /deltaAnalysis/summary reads as all zeros while a job is still running, so
    the status is checked first.
    """
    status = str(job.get("analysisStatus", "")).lower()
    if status != PRECHANGE_COMPLETED:
        raise JobError(
            f"Pre-change analysis is '{status or 'unknown'}', not "
            f"'{PRECHANGE_COMPLETED}'. Its anomaly summary reads as all-zero "
            "until the analysis finishes and must not be used as a verdict."
        )
    # The API spells this field `spanshotDeltaJobId`.
    delta_job_id = job.get("spanshotDeltaJobId")
    if not delta_job_id:
        raise JobError(
            "The completed pre-change analysis carries no spanshotDeltaJobId, "
            "so its anomaly summary cannot be located."
        )
    return str(delta_job_id)


def select_job(entries: list[dict[str, Any]], job_id: str) -> dict[str, Any] | None:
    """Pick the `/jobs/summary` entry for `job_id`.

    The server is asked to filter by job ID; the match is re-checked here.
    """
    for entry in entries:
        if str(entry.get("jobId", "")) == job_id:
            return entry
    return None


class AbsenceWindow:
    """Bounds how long a job may stay absent before it is called non-existent.

    Counts consecutive absences, so one missing poll does not trip the window.
    """

    def __init__(self, poll_interval_seconds: int) -> None:
        self.interval = max(1, poll_interval_seconds)
        # Derived from the poll interval so the window stays close to
        # ABSENCE_GRACE_SECONDS, with a floor of two polls.
        self.limit = max(2, -(-ABSENCE_GRACE_SECONDS // self.interval))
        self.polls = 0

    @property
    def approx_seconds(self) -> int:
        return self.polls * self.interval

    def seen(self) -> None:
        self.polls = 0

    def missing(self) -> bool:
        """Record an absence; True once the grace window is exhausted."""
        self.polls += 1
        return self.polls >= self.limit


def compliance_timestamp_drift(requested: str, returned: str) -> float | None:
    """Seconds between the compliance report asked for and the one returned.

    None if either timestamp is unparseable.
    """
    asked = parse_timestamp(requested)
    got = parse_timestamp(returned)
    if asked is None or got is None:
        return None
    return abs((got - asked).total_seconds())


def check_compliance_timestamp(
    requested: str,
    report: dict[str, Any],
    tolerance_seconds: float = COMPLIANCE_TIMESTAMP_TOLERANCE_SECONDS,
) -> None:
    """Fail unless the compliance report describes the moment that was asked for.

    The API resolves a requested timestamp to the nearest collection and
    returns all-zero counts for a meaningless one, so the returned timestamp
    is compared against the requested one.
    """
    returned = str(report.get("collectionTimestamp", ""))
    drift = compliance_timestamp_drift(requested, returned)
    if drift is None:
        raise ApiError(
            "Could not verify which compliance collection was returned "
            f"(requested {requested!r}, got {returned!r}). Refusing to report "
            "a compliance verdict that cannot be attributed to a snapshot."
        )
    if drift > tolerance_seconds:
        raise ApiError(
            f"Nexus Dashboard returned the compliance report for {returned}, "
            f"{drift:.0f}s away from the requested {requested}. This is a "
            "different compliance collection, and its counts do not describe "
            "the snapshot that was asked about."
        )
