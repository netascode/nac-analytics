"""Delta analysis command."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from nac_analytics.core.progress import note
from nac_analytics.core.report import GATE_DEFAULT_OUTPUT, parse_fail_on
from nac_analytics.products.nexus_dashboard.client import resolve_snapshot_ids
from nac_analytics.products.nexus_dashboard.compliance import snapshot_details
from nac_analytics.products.nexus_dashboard.config import DEFAULT_DOMAIN
from nac_analytics.products.nexus_dashboard.delta import (
    DEFAULT_DELTA_DETAIL,
    normalize_delta_detail,
)
from nac_analytics.products.nexus_dashboard.pipeline import finish_delta_analysis

from . import _helpers
from ._helpers import (
    FAIL_ON_DEFAULT,
    AckOpt,
    CaBundleOpt,
    CleanupOpt,
    DetailOpt,
    DomainOpt,
    FabricOpt,
    FailOnOpt,
    GateOutputOpt,
    HostOpt,
    PasswordOpt,
    PollOpt,
    ReportFileOpt,
    SinceOpt,
    TimeoutOpt,
    UntilOpt,
    UserOpt,
    VerboseOpt,
    VerifyOpt,
    _auto_name,
    _build_config,
    _connect_message,
    _emit_gate_result,
    _enforce,
    _extend_warnings,
    _resolve_pre_post,
    run_command,
)


def delta(
    pre: Annotated[
        Optional[str],
        typer.Argument(
            help="Pre-change snapshot: 'latest', 'latest-N', or a snapshotId.",
        ),
    ] = None,
    post: Annotated[
        Optional[str],
        typer.Argument(
            help="Post-change snapshot: 'latest', 'latest-N', or a snapshotId.",
        ),
    ] = None,
    host: HostOpt = None,
    username: UserOpt = None,
    password: PasswordOpt = None,
    domain: DomainOpt = DEFAULT_DOMAIN,
    fabric: FabricOpt = None,
    prior: Annotated[
        Optional[str],
        typer.Option(
            "--prior",
            hidden=True,
            help="Deprecated; use the pre positional argument.",
        ),
    ] = None,
    later: Annotated[
        Optional[str],
        typer.Option(
            "--later",
            hidden=True,
            help="Deprecated; use the post positional argument.",
        ),
    ] = None,
    name: Annotated[
        Optional[str], typer.Option("--name", help="Job name; generated when omitted.")
    ] = None,
    fail_on: FailOnOpt = FAIL_ON_DEFAULT,
    include_acknowledged: AckOpt = False,
    since: SinceOpt = None,
    until: UntilOpt = None,
    cleanup: CleanupOpt = False,
    detail: DetailOpt = DEFAULT_DELTA_DETAIL,
    output: GateOutputOpt = GATE_DEFAULT_OUTPUT,
    report_file: ReportFileOpt = None,
    verify_ssl: VerifyOpt = True,
    ca_bundle: CaBundleOpt = None,
    timeout: TimeoutOpt = 30,
    poll_interval: PollOpt = 15,
    verbose: VerboseOpt = False,
) -> None:
    """Compare two snapshots of a fabric and report what changed.

    Usage: nac-analytics delta [pre] [post] — defaults to latest-1 vs latest.
    By default writes JUnit to delta-report.xml and exits 3 on critical/major.
    """

    def body() -> None:
        thresholds = parse_fail_on(fail_on)
        pre_selector, post_selector = _resolve_pre_post(
            pre,
            post,
            prior=prior,
            later=later,
            default_pre="latest-1",
            default_post="latest",
        )
        config = _build_config(
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
        job_name = name or _auto_name("delta")
        note(_connect_message(config))
        with _helpers.NDClient(config) as client:
            client.validate_fabric(config.fabric)
            pre_snapshot = client.resolve_snapshot(
                config.fabric, pre_selector, start_date=since, end_date=until
            )
            post_snapshot = client.resolve_snapshot(
                config.fabric, post_selector, start_date=since, end_date=until
            )
            pre_id, post_id = resolve_snapshot_ids(pre_snapshot, post_snapshot)
            note("Starting delta analysis...")
            job_id = client.create_delta_job(
                fabric=config.fabric,
                job_name=job_name,
                prior_id=pre_id,
                later_id=post_id,
            )
            note(f"Waiting for delta analysis {job_id}...")
            # Returns only on COMPLETE, so the summary below is never read
            # from an unfinished job.
            client.wait_delta_job(job_id)
            detail_level = normalize_delta_detail(detail)
            result = finish_delta_analysis(
                client,
                command="delta",
                fabric=config.fabric,
                name=job_name,
                job_id=job_id,
                thresholds=thresholds,
                detail_level=detail_level,
                include_acknowledged=include_acknowledged,
                details={
                    "job_id": job_id,
                    **snapshot_details("pre", pre_snapshot),
                    **snapshot_details("post", post_snapshot),
                },
            )
            _extend_warnings(result, client)
            if cleanup:
                client.remove_delta_jobs(config.fabric, [job_id])
        _emit_gate_result(result, output=output, report_file=report_file)
        _enforce(result)

    run_command(verbose, body)
