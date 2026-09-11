"""Nexus Dashboard 4.2.1+ GA REST client.

`/api/v1/infra` serves authentication, `/api/v1/manage` fabric inventory and
`/api/v1/analyze` everything else. Pure helpers live in ``client_logic``;
this module owns HTTP transport via ``NDClient``.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from nac_analytics.core.config import Config
from nac_analytics.core.exceptions import ApiError, AuthError, InputError, JobError
from nac_analytics.core.log import is_verbose
from nac_analytics.products.nexus_dashboard.client_logic import (
    ANALYZE,
    DELTA_FAILED,
    DELTA_JOB_TYPE,
    DELTA_SUCCEEDED,
    LOGIN_DOMAINS_PATH,
    LOGIN_PATH,
    MANAGE,
    PRECHANGE_COMPLETED,
    PRECHANGE_DRAFT,
    PRECHANGE_FAILED,
    REFRESH_PATH,
    SNAPSHOT_RECORD_CAP,
    AbsenceWindow,
    as_dict,
    as_list,
    check_compliance_timestamp,
    compliance_timestamp_drift,
    extract_api_error,
    fabric_name,
    finished_snapshots,
    format_fabric_names,
    is_aci_fabric,
    parse_timestamp,
    prechange_delta_job_id,
    resolve_snapshot_ids,
    select_job,
    select_snapshot,
    sort_snapshots,
    token_from_auth_response,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ANALYZE",
    "AbsenceWindow",
    "NDClient",
    "as_dict",
    "as_list",
    "check_compliance_timestamp",
    "compliance_timestamp_drift",
    "extract_api_error",
    "fabric_name",
    "finished_snapshots",
    "format_fabric_names",
    "is_aci_fabric",
    "parse_timestamp",
    "prechange_delta_job_id",
    "resolve_snapshot_ids",
    "select_job",
    "select_snapshot",
    "sort_snapshots",
    "token_from_auth_response",
]


def _warn_on_snapshot_cap(
    client: NDClient,
    body: dict[str, Any],
    records: list[dict[str, Any]],
    snapshot_type: str,
) -> None:
    """Record when the 50-record cap is hiding snapshots."""
    remaining = as_dict(as_dict(body.get("meta")).get("counts")).get("remaining")
    if len(records) >= SNAPSHOT_RECORD_CAP and remaining:
        client.notice(
            "%s more '%s' snapshot(s) exist but this endpoint returns at most "
            "%d and ignores every paging parameter. Use --since / --until to "
            "reach the older ones.",
            remaining,
            snapshot_type,
            SNAPSHOT_RECORD_CAP,
        )


class NDClient:
    """HTTP client for one Nexus Dashboard.

    Authentication is lazy, so constructing a client performs no I/O.
    """

    def __init__(self, config: Config, *, http: httpx.Client | None = None) -> None:
        self.config = config
        self.token: str | None = None
        self.notices: list[str] = []
        if http is not None:
            self.client = http
            return
        verify: bool | str = config.ca_bundle or config.verify_ssl
        if not config.verify_ssl and not config.ca_bundle:
            self.notice(
                "TLS certificate verification is disabled. Set ND_VERIFY_SSL=true "
                "and ND_CA_BUNDLE to the cluster's CA in production."
            )
        self.client = httpx.Client(
            verify=verify, timeout=config.request_timeout_seconds
        )

    def close(self) -> None:
        self.client.close()

    def notice(self, message: str, *args: object) -> None:
        """Record an operational warning for the result or log it when verbose."""
        text = message % args if args else message
        if is_verbose():
            logger.warning(text)
        elif text not in self.notices:
            self.notices.append(text)

    def __enter__(self) -> NDClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # -- authentication ----------------------------------------------------

    def authenticate(self) -> None:
        """Log in and store the session token."""
        logger.debug("Authenticating at %s (domain=%s)", LOGIN_PATH, self.config.domain)
        try:
            resp = self.client.post(
                f"{self.config.base_url}{LOGIN_PATH}",
                json={
                    "userName": self.config.username,
                    "userPasswd": self.config.password,
                    # Required. An empty or absent domain returns HTTP 500.
                    "domain": self.config.domain,
                },
            )
        except httpx.HTTPError as exc:
            raise AuthError(f"Could not reach {self.config.base_url}: {exc}") from exc
        if resp.status_code != 200:
            code, message = extract_api_error(resp)
            detail = f" {code}: {message}" if code else f" {message}" if message else ""
            raise AuthError(
                f"Login failed as '{self.config.username}' in domain "
                f"'{self.config.domain}' (HTTP {resp.status_code}).{detail}"
            )
        try:
            body = as_dict(resp.json())
        except ValueError as exc:
            raise AuthError(f"{LOGIN_PATH} returned a non-JSON response.") from exc
        self._apply_token(token_from_auth_response(body))
        logger.debug("Authenticated as %s", self.config.username)

    def refresh(self) -> None:
        """Renew the session token, falling back to a full login."""
        resp = self.client.post(f"{self.config.base_url}{REFRESH_PATH}")
        if resp.status_code != 200:
            logger.debug("Token refresh returned HTTP %s", resp.status_code)
            self.authenticate()
            return
        try:
            body = as_dict(resp.json())
        except ValueError:
            self.authenticate()
            return
        # Refresh returns `jwttoken` only, so the login reader is reused.
        self._apply_token(token_from_auth_response(body))

    def login_domains(self) -> dict[str, Any]:
        """Return the cluster's login domains. Public: no token required."""
        resp = self.client.get(f"{self.config.base_url}{LOGIN_DOMAINS_PATH}")
        if resp.status_code != 200:
            raise ApiError(
                f"{LOGIN_DOMAINS_PATH} returned HTTP {resp.status_code}; this "
                "endpoint is public, so the host or its TLS setup is wrong."
            )
        return as_dict(resp.json())

    def _apply_token(self, token: str) -> None:
        self.token = token
        # The token travels as `Cookie: AuthCookie=<jwttoken>`. An `Authcookie:`
        # header returns 401.
        self.client.headers["Cookie"] = f"AuthCookie={token}"

    def _ensure_auth(self) -> None:
        if self.token is None:
            self.authenticate()

    # -- HTTP --------------------------------------------------------------

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        self._ensure_auth()
        url = f"{self.config.base_url}{path}"
        logger.debug("%s %s", method, path)
        resp = self.client.request(method, url, **kwargs)
        if resp.status_code == 401:
            logger.debug("Received 401; renewing the session token")
            self.refresh()
            # The retry replays `kwargs` verbatim, so any body must be
            # re-readable. Uploads pass `content=`/`files=` as bytes (not a
            # file handle), which re-send cleanly on this second attempt.
            resp = self.client.request(method, url, **kwargs)
        if resp.status_code == 401:
            raise AuthError(
                f"Not authorized for {method} {path}. Check the account's RBAC "
                "role on this Nexus Dashboard."
            )
        return resp

    def get_json(self, path: str, **kwargs: Any) -> dict[str, Any]:
        resp = self.request("GET", path, **kwargs)
        self._raise_for_status(resp, "GET", path)
        return as_dict(resp.json())

    def post_json(self, path: str, **kwargs: Any) -> dict[str, Any]:
        resp = self.request("POST", path, **kwargs)
        self._raise_for_status(resp, "POST", path)
        try:
            return as_dict(resp.json())
        except ValueError:
            return {}

    @staticmethod
    def _raise_for_status(resp: httpx.Response, method: str, path: str) -> None:
        if resp.status_code < 400:
            return
        code, message = extract_api_error(resp)
        detail = f" [{code}]" if code else ""
        raise ApiError(
            f"{method} {path} failed: HTTP {resp.status_code}{detail} {message}".strip()
        )

    # -- fabric inventory --------------------------------------------------

    def list_fabrics(self) -> list[dict[str, Any]]:
        """Return the fabrics this Nexus Dashboard manages.

        Records carry no id, so everything downstream keys on the fabric name.
        `meta` here is flat, unlike the nested `meta.counts` analyze uses.
        """
        return as_list(self.get_json(f"{MANAGE}/fabrics").get("fabrics"))

    def aci_fabric_names(self) -> list[str]:
        """Return the names of the ACI fabrics."""
        names: list[str] = []
        for fabric in self.list_fabrics():
            name = fabric_name(fabric)
            if name and is_aci_fabric(fabric):
                names.append(name)
        return names

    def validate_fabric(self, fabric: str) -> None:
        """Raise `InputError` if `fabric` is not an ACI fabric on this cluster."""
        try:
            names = self.aci_fabric_names()
        except ApiError as exc:
            # An unreadable inventory is not evidence the fabric is wrong, so
            # validation is skipped rather than failed. AuthError is not
            # caught: bad credentials are fatal.
            self.notice(
                "Could not read the fabric inventory (%s); skipping fabric validation",
                exc,
            )
            return
        if not names:
            self.notice(
                "No ACI fabrics reported by %s/fabrics; skipping validation",
                MANAGE,
            )
            return
        if fabric in names:
            return
        raise InputError(
            f"'{fabric}' is not an ACI fabric on this Nexus Dashboard. "
            f"Known ACI fabrics: {format_fabric_names(names)}"
        )

    # -- snapshots ---------------------------------------------------------

    def list_snapshots(
        self,
        fabric: str,
        *,
        snapshot_types: tuple[str, ...] = ("online",),
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """List a fabric's snapshots, newest first.

        Omitting `snapshotType` returns `online` only, so each type is
        requested explicitly. An unrecognised type returns HTTP 500.
        """
        collected: dict[str, dict[str, Any]] = {}
        for snapshot_type in snapshot_types:
            params: dict[str, str] = {
                "fabricName": fabric,
                "snapshotType": snapshot_type,
            }
            if start_date:
                params["startDate"] = start_date
            if end_date:
                params["endDate"] = end_date
            body = self.get_json(f"{ANALYZE}/fabricSnapshots", params=params)
            records = as_list(body.get("snapshots"))
            _warn_on_snapshot_cap(self, body, records, snapshot_type)
            for record in records:
                snapshot_id = str(record.get("snapshotId", ""))
                if snapshot_id:
                    collected[snapshot_id] = record
        return sort_snapshots(list(collected.values()))

    def resolve_snapshot(
        self,
        fabric: str,
        selector: str,
        *,
        snapshot_types: tuple[str, ...] = ("online",),
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Resolve a snapshot selector against a fabric's finished snapshots."""
        snapshots = finished_snapshots(
            self.list_snapshots(
                fabric,
                snapshot_types=snapshot_types,
                start_date=start_date,
                end_date=end_date,
            )
        )
        if not snapshots:
            raise JobError(
                f"Fabric '{fabric}' has no finished snapshots to analyse against."
            )
        return select_snapshot(snapshots, selector)

    # -- pre-change analysis -----------------------------------------------

    def create_prechange_analysis(
        self,
        *,
        fabric: str,
        name: str,
        base_snapshot: dict[str, Any],
        file_name: str,
        content: bytes,
    ) -> dict[str, Any]:
        """Upload a candidate configuration and start a pre-change analysis."""
        payload = {
            "name": name,
            "fabricName": fabric,
            "baseSnapshotId": str(base_snapshot.get("snapshotId", "")),
            "baseSnapshotCollectionDate": str(
                base_snapshot.get("collectionTimestamp", "")
            ),
            "analysisSubmissionTime": int(time.time() * 1000),
            "allowUnsupportedObjectModification": True,
            "uploadedFileName": file_name,
            # Required, and must be a JSON array; `{}` returns HTTP 500. The
            # changes travel in the `file` part.
            "objectCollection": [],
        }
        resp = self.request(
            "POST",
            f"{ANALYZE}/jobs/prechangeAnalysis/file",
            params={"fabricName": fabric},
            data={
                "data": json.dumps(payload),
                "qqfilename": file_name,
                "qqtotalfilesize": str(len(content)),
            },
            files={"file": (file_name, content, "application/json")},
        )
        if resp.status_code == 400:
            # Nexus Dashboard names the object that failed validation. That is
            # passed through as bad input (exit 4).
            code, message = extract_api_error(resp)
            qualifier = f" (code {code})" if code else ""
            raise InputError(
                f"Nexus Dashboard rejected the configuration{qualifier}: {message}"
            )
        self._raise_for_status(resp, "POST", f"{ANALYZE}/jobs/prechangeAnalysis/file")
        # The create response wraps the job in `data`; the single-job GET does
        # not, so they are unwrapped separately.
        return as_dict(as_dict(resp.json()).get("data"))

    def get_prechange_analysis(self, job_id: str) -> dict[str, Any]:
        """Fetch one pre-change analysis job.

        Returned bare, with no `data` wrapper.
        """
        path = f"{ANALYZE}/jobs/prechangeAnalysis/{job_id}"
        resp = self.request("GET", path)
        if resp.status_code in (400, 404) and "not found" in resp.text.lower():
            # A job can be discarded server-side. That state is terminal, so
            # retrying only delays the same answer.
            raise JobError(
                f"Pre-change analysis {job_id} no longer exists on this Nexus "
                "Dashboard. Jobs that never leave 'submitted' can be discarded "
                "server-side; re-run the analysis."
            )
        self._raise_for_status(resp, "GET", path)
        return as_dict(resp.json())

    def wait_prechange_analysis(self, job_id: str) -> dict[str, Any]:
        """Poll a pre-change analysis until it reaches a terminal state."""
        deadline = time.monotonic() + self.config.job_timeout_minutes * 60
        while True:
            job = self.get_prechange_analysis(job_id)
            status = str(job.get("analysisStatus", "")).lower()
            if status == PRECHANGE_COMPLETED:
                return job
            if status in PRECHANGE_FAILED:
                parts = [f"Pre-change analysis {job_id} {status}."]
                message = str(job.get("errorMessage", "")).strip()
                if message:
                    parts.append(message)
                if status == "stopped":
                    # A stopped analysis examined nothing, so it must not
                    # produce a clean verdict.
                    parts.append(
                        "A stopped analysis examined nothing and cannot "
                        "vouch for the change."
                    )
                raise JobError(" ".join(parts))
            if status == PRECHANGE_DRAFT:
                # A saved draft never progresses, so waiting on one only
                # burns the timeout.
                raise JobError(
                    f"Pre-change analysis {job_id} is a saved draft that was "
                    "never submitted, so it will never produce a result."
                )
            if time.monotonic() > deadline:
                raise JobError(
                    f"Pre-change analysis {job_id} was still '{status}' after "
                    f"{self.config.job_timeout_minutes} minutes."
                )
            logger.debug("Pre-change analysis %s is %s...", job_id, status or "pending")
            time.sleep(self.config.poll_interval_seconds)

    def delete_prechange_analysis(self, job_id: str) -> None:
        """Delete a pre-change analysis. Only legal once the job is terminal."""
        resp = self.request("DELETE", f"{ANALYZE}/jobs/prechangeAnalysis/{job_id}")
        if resp.status_code >= 400:
            _, message = extract_api_error(resp)
            logger.warning(
                "Could not delete pre-change analysis %s (HTTP %s) %s",
                job_id,
                resp.status_code,
                message,
            )

    # -- delta analysis ----------------------------------------------------

    def create_delta_job(
        self, *, fabric: str, job_name: str, prior_id: str, later_id: str
    ) -> str:
        body = self.post_json(
            f"{ANALYZE}/jobs/deltaAnalysis",
            json={
                "fabricName": fabric,
                "jobName": job_name,
                "priorEpochUuid": prior_id,
                "laterEpochUuid": later_id,
            },
        )
        job_id = body.get("jobId")
        if not job_id:
            raise JobError("Delta analysis was created but returned no jobId.")
        logger.debug("Delta analysis %s started", job_id)
        return str(job_id)

    def job_summary(
        self,
        *,
        job_id: str | None = None,
        job_type: str | None = None,
        fabric: str | None = None,
    ) -> list[dict[str, Any]]:
        """List job summary entries.

        /jobs/summary returns HTTP 200 with an empty `entries` array for a job
        that does not exist, so callers test the list, not the status code.
        """
        params: dict[str, str] = {}
        if job_id:
            params["jobId"] = job_id
        if job_type:
            params["jobTypes"] = job_type
        if fabric:
            params["fabricName"] = fabric
        body = self.get_json(f"{ANALYZE}/jobs/summary", params=params)
        return as_list(body.get("entries"))

    def wait_delta_job(self, job_id: str) -> dict[str, Any]:
        """Poll a delta analysis until it reaches a terminal state."""
        deadline = time.monotonic() + self.config.job_timeout_minutes * 60
        window = AbsenceWindow(self.config.poll_interval_seconds)
        while True:
            entries = self.job_summary(job_id=job_id, job_type=DELTA_JOB_TYPE)
            job = select_job(entries, job_id)
            if job is not None:
                window.seen()
                # Delta status values are upper case.
                status = str(job.get("status", "")).upper()
                if status == DELTA_SUCCEEDED:
                    return job
                if status in DELTA_FAILED:
                    parts = [f"Delta analysis {job_id} ended {status}."]
                    message = str(job.get("errorMessage", "")).strip()
                    if message:
                        parts.append(message)
                    if status == "STOPPED":
                        parts.append(
                            "A stopped job analysed nothing, so its results "
                            "cannot validate a change."
                        )
                    raise JobError(" ".join(parts))
                logger.debug("Delta analysis %s is %s...", job_id, status or "pending")
            elif window.missing():
                raise JobError(
                    f"Delta analysis {job_id} was never reported by "
                    f"{ANALYZE}/jobs/summary after {window.polls} polls "
                    f"(~{window.approx_seconds}s). The endpoint answers 200 "
                    "with no entries for a job that does not exist."
                )
            else:
                logger.debug(
                    "Delta analysis %s not visible yet (%d/%d)...",
                    job_id,
                    window.polls,
                    window.limit,
                )
            if time.monotonic() > deadline:
                raise JobError(
                    f"Delta analysis {job_id} did not finish within "
                    f"{self.config.job_timeout_minutes} minutes."
                )
            time.sleep(self.config.poll_interval_seconds)

    def remove_delta_jobs(self, fabric: str, job_ids: list[str]) -> None:
        if not job_ids:
            return
        self.post_json(
            f"{ANALYZE}/jobs/deltaAnalysis/actions/remove",
            json={"fabricName": fabric, "jobIdCollection": job_ids},
        )

    def delta_summary(
        self, delta_job_id: str, *, include_acknowledged: bool = False
    ) -> dict[str, Any]:
        """Fetch the anomaly summary for a delta analysis job.

        This reads as all zeros while a job is still running, so callers must
        check the job status first. Acknowledged anomalies are excluded
        server-side by default.
        """
        return self.get_json(
            f"{ANALYZE}/deltaAnalysis/summary",
            params={
                "jobId": delta_job_id,
                "includeAcknowledged": str(include_acknowledged).lower(),
            },
        )

    def delta_resources(
        self, delta_job_id: str, *, include_acknowledged: bool = False
    ) -> dict[str, Any]:
        """Fetch per-resource-type impact counts for a delta analysis job."""
        return self.get_json(
            f"{ANALYZE}/deltaAnalysis/resources",
            params={
                "jobId": delta_job_id,
                "includeAcknowledged": str(include_acknowledged).lower(),
            },
        )

    def delta_policy_diff(self, delta_job_id: str) -> dict[str, Any]:
        """Fetch the configuration diff between the two snapshots."""
        return self.get_json(
            f"{ANALYZE}/deltaAnalysis/policyDiff",
            params={"jobId": delta_job_id},
        )

    def anomaly_details(
        self,
        fabric: str,
        *,
        job_id: str,
        include_acknowledged: bool = False,
        max_records: int = 200,
    ) -> dict[str, Any]:
        """Fetch individual anomaly records scoped to a fabric and delta job."""
        return self.get_json(
            f"{ANALYZE}/anomalies/details",
            params={
                "fabricName": fabric,
                "jobId": job_id,
                "max": str(max_records),
                "includeAcknowledged": str(include_acknowledged).lower(),
            },
        )

    # -- cleanup -----------------------------------------------------------

    def find_prechange_delta_jobs(
        self, fabric: str, analysis_schedule_id: str
    ) -> list[str]:
        """Find every delta job a pre-change analysis spawned.

        An analysis can spawn more than one `EPOCH-DELTA-ANALYSIS` child and
        `spanshotDeltaJobId` names only one, so children are found by matching
        `configName` against the parent's `analysisScheduleId`.
        """
        if not analysis_schedule_id:
            return []
        found: list[str] = []
        for entry in self.job_summary(fabric=fabric, job_type=DELTA_JOB_TYPE):
            if str(entry.get("configName", "")) != analysis_schedule_id:
                continue
            job_id = str(entry.get("jobId", ""))
            if job_id:
                found.append(job_id)
        return found

    def cleanup_prechange(self, fabric: str, job: dict[str, Any]) -> list[str]:
        """Remove a pre-change analysis and the delta jobs it spawned.

        Deleting the parent does not remove the children, so they go first and
        their removal is re-checked because it is asynchronous. The pre-change
        snapshot the analysis created has no DELETE route and remains.
        """
        job_id = str(job.get("jobId", ""))
        schedule_id = str(job.get("analysisScheduleId", ""))
        children = self.find_prechange_delta_jobs(fabric, schedule_id)
        if children:
            self.remove_delta_jobs(fabric, children)
        if job_id:
            self.delete_prechange_analysis(job_id)
        if children:
            time.sleep(self.config.poll_interval_seconds)
            leftover = self.find_prechange_delta_jobs(fabric, schedule_id)
            if leftover:
                logger.warning(
                    "Delta job(s) %s survived cleanup; remove them from the "
                    "Nexus Dashboard UI.",
                    ", ".join(leftover),
                )
                return leftover
        return []

    # -- compliance --------------------------------------------------------

    def compliance_summary(
        self, fabric: str, *, collection_timestamp: str | None = None
    ) -> dict[str, Any]:
        """Fetch a fabric's compliance summary.

        `collection_timestamp` is an inclusive upper bound, and a compliance
        run lands about a minute after the snapshot it describes. Pass a
        snapshot's `analysisTimestamp`, not its `collectionTimestamp`.
        """
        params = {"fabricName": fabric}
        if collection_timestamp:
            params["collectionTimestamp"] = collection_timestamp
        report = self.get_json(f"{ANALYZE}/complianceReport/summary", params=params)
        if collection_timestamp:
            check_compliance_timestamp(collection_timestamp, report)
        return report

    def compliance_rule_details(
        self, fabric: str, *, collection_timestamp: str | None = None
    ) -> dict[str, Any]:
        """Fetch per-rule compliance detail.

        Each rule carries a violation count; individual violations are not
        enumerable on the GA API.
        """
        params = {"fabricName": fabric}
        if collection_timestamp:
            params["collectionTimestamp"] = collection_timestamp
        report = self.get_json(f"{ANALYZE}/complianceReport/ruleDetails", params=params)
        if collection_timestamp:
            check_compliance_timestamp(collection_timestamp, report)
        return report
