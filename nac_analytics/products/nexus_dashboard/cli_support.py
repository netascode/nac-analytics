"""Shared Nexus Dashboard CLI helpers (config, emit, gate orchestration)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import typer

from nac_analytics.core.config import Config
from nac_analytics.core.exceptions import (
    AnomalyThresholdError,
    InputError,
    NacAnalyticsError,
)
from nac_analytics.core.log import configure_logging
from nac_analytics.core.progress import note
from nac_analytics.core.report import (
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
from nac_analytics.products.nexus_dashboard.pipeline import finish_delta_analysis

logger = logging.getLogger(__name__)

KNOWN_CLI_ERRORS = (NacAnalyticsError, httpx.HTTPError, OSError)

GATE_OUTPUT_HELP = (
    f"Output format: {', '.join(OUTPUT_FORMATS)}. "
    "Gate commands default to junit (written to --report-file)."
)
GENERAL_OUTPUT_HELP = (
    f"Output format: {', '.join(OUTPUT_FORMATS)}. "
    "junit writes one test case per --fail-on severity (prechange/delta)."
)


def prechange_ui_url(base_url: str) -> str:
    """Nexus Dashboard Pre-Change Analysis page (same as nexus-pcv --output-url)."""
    return (
        f"{base_url}/appcenter/cisco/nexus-insights/ui/"
        "#/changeManagement/preChangeAnalysis"
    )


def configure_cli_logging(verbose: bool) -> None:
    configure_logging(verbose)


def extend_warnings(result: Result, client: NDClient) -> None:
    if client.notices:
        result.warnings.extend(client.notices)


def connect_message(config: Config) -> str:
    return f"Connecting to {config.host} as {config.username}..."


def fail(exc: Exception, verbose: bool) -> typer.Exit:
    code = exc.exit_code if isinstance(exc, NacAnalyticsError) else 1
    if verbose:
        logger.exception("%s", exc)
    typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
    return typer.Exit(code=code)


def build_config(
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


def auto_name(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"nac-analytics-{prefix}-{stamp}"


def prechange_result_from_job(
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
        "prechange_ui_url": prechange_ui_url(config.base_url),
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


def emit(result: Result, output: str) -> None:
    typer.echo(render(result, output))


def emit_gate_result(
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


def emit_snapshot(
    record: dict[str, object], output: str, *, warnings: list[str]
) -> None:
    if output == "text":
        lines = [f"warning: {warning}" for warning in warnings]
        lines.append(str(record.get("snapshotId", "")))
        typer.echo("\n".join(lines) if lines else "")
        return
    payload: dict[str, object] = dict(record)
    if warnings:
        payload["warnings"] = warnings
    typer.echo(serialize_structured(payload, output))


def resolve_pre_post(
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


def enforce(verdict_result: Result) -> None:
    verdict = verdict_result.verdict
    if verdict is not None and not verdict.passed:
        raise AnomalyThresholdError(f"DECISION: FAIL — {verdict.reason}")


def run_gate_command(
    result: Result,
    *,
    output: str,
    report_file: str | None,
) -> None:
    """Emit gate output and raise when the verdict fails."""
    emit_gate_result(result, output=output, report_file=report_file)
    enforce(result)


@contextmanager
def nd_session(
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
    validate: bool = True,
) -> Iterator[tuple[Config, NDClient]]:
    """Build config, connect, optionally validate fabric, yield client."""
    config = build_config(
        host=host,
        username=username,
        password=password,
        domain=domain,
        fabric=fabric,
        verify_ssl=verify_ssl,
        ca_bundle=ca_bundle,
        timeout=timeout,
        poll_interval=poll_interval,
    )
    note(connect_message(config))
    with NDClient(config) as client:
        if validate:
            client.validate_fabric(config.fabric)
        yield config, client


@contextmanager
def handle_cli_errors(verbose: bool) -> Iterator[None]:
    """Map known CLI failures to exit codes; let unexpected errors propagate."""
    try:
        yield
    except KNOWN_CLI_ERRORS as exc:
        raise fail(exc, verbose) from exc
