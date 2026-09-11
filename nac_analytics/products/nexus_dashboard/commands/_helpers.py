"""Shared CLI options, helpers, and error handling for Nexus Dashboard commands."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Optional

import typer

from nac_analytics.core.exceptions import (
    AnomalyThresholdError,
    ApiError,
    AuthError,
    InputError,
    NacAnalyticsError,
)
from nac_analytics.core.log import configure_logging
from nac_analytics.core.progress import note
from nac_analytics.core.report import (
    DEFAULT_FAIL_ON,
    GATE_REPORT_FILES,
    OUTPUT_FORMATS,
    Result,
    render,
    serialize_structured,
)
from nac_analytics.products.nexus_dashboard.client import (
    NDClient,
    prechange_delta_job_id,
)
from nac_analytics.products.nexus_dashboard.compliance import (
    compliance_for_snapshot,
    prechange_job_details,
    snapshot_details,
)
from nac_analytics.products.nexus_dashboard.config import Config
from nac_analytics.products.nexus_dashboard.delta import (
    DELTA_DETAIL_LEVELS,
    PRECHANGE_DEFAULT_DETAIL,
)
from nac_analytics.products.nexus_dashboard.pipeline import finish_delta_analysis

logger = logging.getLogger(__name__)

# Precomputed so the option default is a plain value, not a function call.
FAIL_ON_DEFAULT = ",".join(DEFAULT_FAIL_ON)

# -- shared options --------------------------------------------------------

HostOpt = Annotated[
    Optional[str],
    typer.Option("--host", envvar="ND_HOST", help="Nexus Dashboard hostname or IP."),
]
UserOpt = Annotated[
    Optional[str],
    typer.Option("--username", "-u", envvar="ND_USER", help="Login username."),
]
PasswordOpt = Annotated[
    Optional[str],
    typer.Option("--password", envvar="ND_PASSWORD", help="Login password."),
]
DomainOpt = Annotated[
    str,
    typer.Option("--domain", envvar="ND_DOMAIN", help="Login domain; ND requires one."),
]
FabricOpt = Annotated[
    Optional[str],
    typer.Option(
        "--fabric",
        "-f",
        envvar="ND_FABRIC",
        help="ACI fabric name (or set via YAML `fabric` / ND_FABRIC).",
    ),
]
VerifyOpt = Annotated[
    bool,
    typer.Option(
        "--verify-ssl/--no-verify-ssl",
        envvar="ND_VERIFY_SSL",
        help="Verify the cluster's TLS certificate.",
    ),
]
CaBundleOpt = Annotated[
    Optional[str],
    typer.Option("--ca-bundle", envvar="ND_CA_BUNDLE", help="Path to a CA bundle."),
]
TimeoutOpt = Annotated[
    int,
    typer.Option(
        "--timeout",
        envvar="ND_JOB_TIMEOUT_MINUTES",
        help="Minutes to wait for an analysis job.",
    ),
]
PollOpt = Annotated[
    int,
    typer.Option(
        "--poll-interval",
        envvar="ND_POLL_INTERVAL",
        help="Seconds between job status polls.",
    ),
]
OutputOpt = Annotated[
    str,
    typer.Option(
        "--output",
        "-o",
        help=(
            f"Output format: {', '.join(OUTPUT_FORMATS)}. "
            "junit writes one test case per --fail-on severity (prechange/delta)."
        ),
    ),
]
VerboseOpt = Annotated[
    bool,
    typer.Option(
        "--verbose",
        "-v",
        help="Log each HTTP request and API call.",
    ),
]
FailOnOpt = Annotated[
    str,
    typer.Option(
        "--fail-on",
        help=(
            "Comma-separated severities whose new anomalies fail the run "
            f"(exit 3); default {FAIL_ON_DEFAULT}. Use 'none' to report only."
        ),
    ),
]
SinceOpt = Annotated[
    Optional[str],
    typer.Option(
        "--since",
        help=(
            "When resolving snapshots, only consider those collected on or "
            "after this ISO-8601 timestamp (works around the API's 50-record "
            "listing cap)."
        ),
    ),
]
UntilOpt = Annotated[
    Optional[str],
    typer.Option(
        "--until",
        help=(
            "When resolving snapshots, only consider those collected on or "
            "before this ISO-8601 timestamp."
        ),
    ),
]
CleanupOpt = Annotated[
    bool,
    typer.Option(
        "--cleanup/--keep",
        help=(
            "Delete analysis job(s) created by this run when finished. "
            "prechange also leaves its snapshot on the fabric."
        ),
    ),
]
AckOpt = Annotated[
    bool,
    typer.Option(
        "--include-acknowledged",
        help="Count anomalies that have been acknowledged in Nexus Dashboard.",
    ),
]
DetailOpt = Annotated[
    str,
    typer.Option(
        "--detail",
        envvar="ND_DELTA_DETAIL",
        help=(
            "Extra delta detail on prechange and delta beyond severity counts: "
            f"{', '.join(DELTA_DETAIL_LEVELS)}. "
            f"Default {PRECHANGE_DEFAULT_DETAIL} on prechange (resources on delta). "
            f"Legacy values 'all' and 'summary' map to full and none."
        ),
    ),
]
ReportFileOpt = Annotated[
    Optional[str],
    typer.Option(
        "--report-file",
        help=(
            "JUnit report path for prechange/delta (default: prechange-report.xml "
            "or delta-report.xml). Use '-' for stdout."
        ),
    ),
]
GateOutputOpt = Annotated[
    str,
    typer.Option(
        "--output",
        "-o",
        help=(
            f"Output format: {', '.join(OUTPUT_FORMATS)}. "
            "Gate commands default to junit (written to --report-file)."
        ),
    ),
]


# -- plumbing --------------------------------------------------------------


def _configure_logging(verbose: bool) -> None:
    configure_logging(verbose)


def _fail(exc: Exception, verbose: bool) -> typer.Exit:
    code = exc.exit_code if isinstance(exc, NacAnalyticsError) else 1
    if verbose:
        logger.exception("%s", exc)
    typer.secho(f"error (exit {code}): {exc}", fg=typer.colors.RED, err=True)
    return typer.Exit(code=code)


def run_command(verbose: bool, body: Callable[[], None]) -> None:
    """Configure logging, run ``body``, and map exceptions to Typer exits."""
    _configure_logging(verbose)
    try:
        body()
    except Exception as exc:
        raise _fail(exc, verbose) from exc


def _extend_warnings(result: Result, client: NDClient) -> None:
    if client.notices:
        result.warnings.extend(client.notices)


def _connect_message(config: Config) -> str:
    return f"Connecting to {config.host} as {config.username}..."


def _build_config(
    *,
    host: str | None,
    username: str | None,
    password: str | None,
    domain: str,
    fabric: str | None,
    verify_ssl: bool,
    ca_bundle: str | None,
    timeout: int,
    poll_interval: int,
) -> Config:
    if not fabric:
        raise InputError(
            "A fabric is required (--fabric, ND_FABRIC, or YAML `fabric`)."
        )
    return Config(
        host=host or "",
        username=username or "",
        password=password or "",
        domain=domain,
        fabric=fabric,
        verify_ssl=verify_ssl,
        ca_bundle=ca_bundle,
        request_timeout_seconds=60.0,
        poll_interval_seconds=poll_interval,
        job_timeout_minutes=timeout,
    )


def _auto_name(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"nac-analytics-{prefix}-{stamp}"


def _prechange_ui_url(base_url: str) -> str:
    """Nexus Dashboard Pre-Change Analysis page (same as nexus-pcv --output-url)."""
    return (
        f"{base_url}/appcenter/cisco/nexus-insights/ui/"
        "#/changeManagement/preChangeAnalysis"
    )


def _prechange_result_from_job(
    client: NDClient,
    config: Config,
    *,
    job: dict[str, Any],
    job_id: str,
    job_name: str,
    config_file: Path | None,
    thresholds: tuple[str, ...],
    detail_level: str,
    include_acknowledged: bool,
    since: str | None,
    until: str | None,
) -> Result:
    """Collect gate results from a finished pre-change analysis job."""
    job_fabric = str(job.get("fabricName", "")).strip()
    if job_fabric and job_fabric != config.fabric:
        raise InputError(
            f"Pre-change analysis {job_id} belongs to fabric {job_fabric!r}, "
            f"not {config.fabric!r}."
        )
    base_snapshot_id = str(job.get("baseSnapshotId", "")).strip()
    if not base_snapshot_id:
        raise InputError(
            f"Pre-change analysis {job_id} has no baseSnapshotId; "
            "cannot load baseline compliance."
        )
    snapshot = client.resolve_snapshot(
        config.fabric,
        base_snapshot_id,
        start_date=since,
        end_date=until,
    )
    delta_job_id = prechange_delta_job_id(job)
    note("Collecting change approval detail...")
    compliance = compliance_for_snapshot(
        client,
        config.fabric,
        snapshot,
        scope="baseline snapshot (before change)",
    )
    details: dict[str, object] = {
        "prechange_ui_url": _prechange_ui_url(config.base_url),
        "job_id": job_id,
        "delta_job_id": delta_job_id,
        **snapshot_details("base", snapshot),
        **prechange_job_details(job),
    }
    uploaded = str(job.get("uploadedFileName", ""))
    config_label = str(config_file) if config_file else uploaded
    if config_label:
        details["config_file"] = config_label
    return finish_delta_analysis(
        client,
        command="prechange",
        fabric=config.fabric,
        name=job_name,
        job_id=delta_job_id,
        thresholds=thresholds,
        detail_level=detail_level,
        include_acknowledged=include_acknowledged,
        details=details,
        compliance=compliance,
    )


def _emit(result: Result, output: str) -> None:
    typer.echo(render(result, output))


def _emit_gate_result(
    result: Result,
    *,
    output: str,
    report_file: str | None,
) -> None:
    """Write gate command output: JUnit to file by default, verdict on stderr."""
    if output == "junit":
        rendered = render(result, "junit")
        if report_file == "-":
            typer.echo(rendered)
        else:
            path = Path(report_file or GATE_REPORT_FILES[result.command])
            path.write_text(rendered, encoding="utf-8")
        if result.verdict is not None:
            status = "PASS" if result.verdict.passed else "FAIL"
            typer.secho(f"DECISION: {status} — {result.verdict.reason}", err=True)
        return
    typer.echo(render(result, output))


def _emit_snapshot(record: dict[str, object], output: str) -> None:
    if output == "text":
        typer.echo(str(record.get("snapshotId", "")))
        return
    typer.echo(serialize_structured(record, output))


def _emit_notices(client: NDClient) -> None:
    """Print a client's operational warnings to stderr, keeping stdout clean."""
    for warning in client.notices:
        typer.secho(f"warning: {warning}", fg=typer.colors.YELLOW, err=True)


def _analysis_trigger_error(exc: ApiError) -> Exception:
    """Explain a refused assurance analysis trigger.

    Triggering needs the super-admin, fabric-admin or support-engineer role, so
    a 403 is an RBAC fact the operator can act on rather than a transport
    failure, and it exits as an auth error.
    """
    if "HTTP 403" not in str(exc):
        return exc
    return AuthError(
        "Not permitted to trigger an assurance analysis. This API requires the "
        "super-admin, fabric-admin or support-engineer role; an observer "
        f"account can read snapshots but cannot start one. ({exc})"
    )


def _resolve_pre_post(
    pre: str | None,
    post: str | None,
    *,
    prior: str | None,
    later: str | None,
    default_pre: str,
    default_post: str,
) -> tuple[str, str]:
    """Merge positional pre/post selectors with deprecated --prior/--later flags."""
    if pre is not None:
        pre_selector = pre
    elif prior is not None:
        pre_selector = prior
    else:
        pre_selector = default_pre
    if post is not None:
        post_selector = post
    elif later is not None:
        post_selector = later
    else:
        post_selector = default_post
    return pre_selector, post_selector


def _enforce(verdict_result: Result) -> None:
    verdict = verdict_result.verdict
    if verdict is not None and not verdict.passed:
        raise AnomalyThresholdError(f"DECISION: FAIL — {verdict.reason}")
