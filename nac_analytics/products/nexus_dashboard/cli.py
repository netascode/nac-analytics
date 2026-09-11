"""Nexus Dashboard command group (entry layer).

Typer commands that orchestrate config, client calls, domain modules, and
reporting for `nac-analytics nexus-dashboard <verb>`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Optional

import typer
from typer._click.core import ParameterSource

from nac_analytics.core.config import DEFAULT_DOMAIN, normalize_host
from nac_analytics.core.exceptions import (
    AnomalyThresholdError,
    ApiError,
    AuthError,
    InputError,
)
from nac_analytics.core.progress import note
from nac_analytics.core.report import (
    DEFAULT_FAIL_ON,
    GATE_DEFAULT_OUTPUT,
    MultiFabricResult,
    Result,
    parse_fail_on,
    render_multi,
)
from nac_analytics.products.nexus_dashboard.cli_support import (
    GATE_OUTPUT_HELP,
    GENERAL_OUTPUT_HELP,
    auto_name,
    configure_cli_logging,
    emit,
    emit_snapshot,
    extend_warnings,
    handle_cli_errors,
    nd_session,
    prechange_result_from_job,
    resolve_pre_post,
    run_gate_command,
)
from nac_analytics.products.nexus_dashboard.client import (
    fabric_name,
    is_aci_fabric,
    resolve_snapshot_ids,
)
from nac_analytics.products.nexus_dashboard.compliance import (
    run_compliance_check,
    snapshot_details,
)
from nac_analytics.products.nexus_dashboard.delta import (
    DEFAULT_DELTA_DETAIL,
    DELTA_DETAIL_LEVELS,
    PRECHANGE_DEFAULT_DETAIL,
    normalize_delta_detail,
)
from nac_analytics.products.nexus_dashboard.pipeline import finish_delta_analysis
from nac_analytics.products.nexus_dashboard.settings import configured_fabrics
from nac_analytics.products.nexus_dashboard.tf_plan import prepare_prechange_content

logger = logging.getLogger(__name__)

# Precomputed so the option default is a plain value, not a function call.
FAIL_ON_DEFAULT = ",".join(DEFAULT_FAIL_ON)

ND_HELP = """\
Change analysis for Cisco Nexus Dashboard 4.2.1+ (GA REST APIs, ACI).

Configuration:
  ND_HOST                 Nexus Dashboard hostname or IP
  ND_USER                 Login username
  ND_PASSWORD             Login password
  ND_DOMAIN               Login domain
  ND_FABRIC               Default ACI fabric name
  ND_VERIFY_SSL           Verify TLS certificate (ND_VERIFY_TLS accepted)
  ND_CA_BUNDLE            Path to CA bundle
  ND_JOB_TIMEOUT_MINUTES  Minutes to wait for analysis jobs
  ND_POLL_INTERVAL        Seconds between job status polls
  ND_DELTA_DETAIL         Default --detail for prechange and delta
  ND_CONFIG               Path to YAML config file

  In YAML, nest these under a `nexus_dashboard:` section. Settings load from
  CLI flags, then environment variables, nac-analytics.yaml, or .env."""

app = typer.Typer(
    help=ND_HELP,
    add_completion=False,
    no_args_is_help=True,
)


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
    typer.Option("--output", "-o", help=GENERAL_OUTPUT_HELP),
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
    typer.Option("--output", "-o", help=GATE_OUTPUT_HELP),
]


# -- commands --------------------------------------------------------------


@app.command()
def prechange(
    config_file: Annotated[
        Optional[Path],
        typer.Argument(
            # Typer's exists/dir_okay/readable checks exit 2, which is
            # reserved for a failed job. Input is validated below so it
            # exits 4.
            help=(
                "Candidate configuration: Terraform plan JSON "
                "(terraform show -json) or APIC MO JSON. Omit with --job-id."
            ),
        ),
    ] = None,
    baseline: Annotated[
        Optional[str],
        typer.Argument(
            help="Baseline snapshot: 'latest', 'latest-N', or a snapshotId.",
        ),
    ] = None,
    host: HostOpt = None,
    username: UserOpt = None,
    password: PasswordOpt = None,
    domain: DomainOpt = DEFAULT_DOMAIN,
    fabric: FabricOpt = None,
    name: Annotated[
        Optional[str], typer.Option("--name", help="Job name; generated when omitted.")
    ] = None,
    job_id: Annotated[
        Optional[str],
        typer.Option(
            "--job-id",
            help=(
                "Resume or fetch an existing pre-change analysis by job ID "
                "(no config upload)."
            ),
        ),
    ] = None,
    base_snapshot: Annotated[
        Optional[str],
        typer.Option(
            "--base-snapshot",
            hidden=True,
            help="Deprecated; use the baseline positional argument.",
        ),
    ] = None,
    fail_on: FailOnOpt = FAIL_ON_DEFAULT,
    include_acknowledged: AckOpt = False,
    since: SinceOpt = None,
    until: UntilOpt = None,
    cleanup: CleanupOpt = False,
    detail: DetailOpt = PRECHANGE_DEFAULT_DETAIL,
    output: GateOutputOpt = GATE_DEFAULT_OUTPUT,
    report_file: ReportFileOpt = None,
    verify_ssl: VerifyOpt = True,
    ca_bundle: CaBundleOpt = None,
    timeout: TimeoutOpt = 30,
    poll_interval: PollOpt = 15,
    verbose: VerboseOpt = False,
) -> None:
    """Analyse a candidate configuration against a fabric's current state.

    Accepts Terraform plan JSON from `terraform show -json plan.tfplan` as well
    as APIC managed-object JSON. Terraform plans are converted automatically.

    By default writes JUnit to prechange-report.xml and exits 3 when new
    critical/major anomalies would be introduced. Use --output text for a full
    human-readable report. Use --job-id to resume or fetch an existing analysis
    without uploading a config again.
    """
    configure_cli_logging(verbose)
    with handle_cli_errors(verbose):
        thresholds = parse_fail_on(fail_on)
        if job_id and config_file is not None:
            raise InputError("Pass a config file or --job-id, not both.")
        if not job_id and config_file is None:
            raise InputError("A config file is required unless --job-id is given.")
        baseline_selector = (
            baseline
            if baseline is not None
            else base_snapshot
            if base_snapshot is not None
            else "latest"
        )
        detail_level = normalize_delta_detail(detail)
        upload_content: bytes | None = None
        upload_name = ""
        if job_id:
            resume_id = job_id.strip()
            if not resume_id:
                raise InputError("--job-id must not be empty.")
        else:
            assert config_file is not None
            if not config_file.exists():
                raise InputError(f"{config_file} does not exist.")
            if not config_file.is_file():
                raise InputError(f"{config_file} is not a file.")
            try:
                content = config_file.read_bytes()
            except OSError as exc:
                raise InputError(
                    f"{config_file} cannot be read: {exc.strerror}."
                ) from exc
            if not content.strip():
                raise InputError(f"{config_file} is empty.")
            upload_content = prepare_prechange_content(content)
            upload_name = config_file.name
        with nd_session(
            host=host,
            username=username,
            password=password,
            domain=domain,
            fabric=fabric,
            verify_ssl=verify_ssl,
            ca_bundle=ca_bundle,
            timeout=timeout,
            poll_interval=poll_interval,
        ) as (config, client):
            if job_id:
                assert resume_id is not None
                note(f"Waiting for pre-change analysis {resume_id}...")
                job = client.wait_prechange_analysis(resume_id)
                job_name = name or str(job.get("name") or resume_id)
                result = prechange_result_from_job(
                    client,
                    config,
                    job=job,
                    job_id=resume_id,
                    job_name=job_name,
                    config_file=None,
                    thresholds=thresholds,
                    detail_level=detail_level,
                    include_acknowledged=include_acknowledged,
                    since=since,
                    until=until,
                )
            else:
                assert config_file is not None
                assert upload_content is not None
                job_name = name or auto_name("prechange")
                snapshot = client.resolve_snapshot(
                    config.fabric, baseline_selector, start_date=since, end_date=until
                )
                note("Submitting pre-change analysis...")
                created = client.create_prechange_analysis(
                    fabric=config.fabric,
                    name=job_name,
                    base_snapshot=snapshot,
                    file_name=upload_name,
                    content=upload_content,
                )
                new_job_id = str(created.get("jobId", ""))
                if not new_job_id:
                    raise ApiError(
                        "Nexus Dashboard accepted the upload but returned no jobId."
                    )
                note(f"Waiting for pre-change analysis {new_job_id}...")
                job = client.wait_prechange_analysis(new_job_id)
                result = prechange_result_from_job(
                    client,
                    config,
                    job=job,
                    job_id=new_job_id,
                    job_name=job_name,
                    config_file=config_file,
                    thresholds=thresholds,
                    detail_level=detail_level,
                    include_acknowledged=include_acknowledged,
                    since=since,
                    until=until,
                )
            extend_warnings(result, client)
            if cleanup:
                leftover = client.cleanup_prechange(config.fabric, job)
                if leftover:
                    result.warnings.append(
                        f"delta job(s) {', '.join(leftover)} survived cleanup"
                    )
                result.warnings.append(
                    "the pre-change snapshot this analysis created has no "
                    "DELETE route on the GA API and remains on the fabric"
                )
        run_gate_command(result, output=output, report_file=report_file)


@app.command()
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

    Usage: nac-analytics nd delta [pre] [post] — defaults to latest-1 vs latest.
    By default writes JUnit to delta-report.xml and exits 3 on critical/major.
    """
    configure_cli_logging(verbose)
    with handle_cli_errors(verbose):
        thresholds = parse_fail_on(fail_on)
        pre_selector, post_selector = resolve_pre_post(
            pre,
            post,
            prior=prior,
            later=later,
            default_pre="latest-1",
            default_post="latest",
        )
        job_name = name or auto_name("delta")
        with nd_session(
            host=host,
            username=username,
            password=password,
            domain=domain,
            fabric=fabric,
            verify_ssl=verify_ssl,
            ca_bundle=ca_bundle,
            timeout=timeout,
            poll_interval=poll_interval,
        ) as (config, client):
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
            extend_warnings(result, client)
            if cleanup:
                client.remove_delta_jobs(config.fabric, [job_id])
        run_gate_command(result, output=output, report_file=report_file)


@app.command()
def snapshots(
    selector: Annotated[
        str,
        typer.Argument(
            help="Snapshot to resolve: 'latest', 'latest-N', or a snapshotId.",
        ),
    ],
    host: HostOpt = None,
    username: UserOpt = None,
    password: PasswordOpt = None,
    domain: DomainOpt = DEFAULT_DOMAIN,
    fabric: FabricOpt = None,
    since: SinceOpt = None,
    until: UntilOpt = None,
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output format: text (snapshot ID only), json, or yaml.",
        ),
    ] = "text",
    verify_ssl: VerifyOpt = True,
    ca_bundle: CaBundleOpt = None,
    verbose: VerboseOpt = False,
) -> None:
    """Resolve a fabric snapshot and print its ID (for CI baseline pinning)."""
    configure_cli_logging(verbose)
    with handle_cli_errors(verbose):
        if output not in ("text", "json", "yaml"):
            raise InputError(
                f"Unknown output format '{output}'. Choose from: text, json, yaml."
            )
        with nd_session(
            host=host,
            username=username,
            password=password,
            domain=domain,
            fabric=fabric,
            verify_ssl=verify_ssl,
            ca_bundle=ca_bundle,
            timeout=30,
            poll_interval=15,
        ) as (config, client):
            record = client.resolve_snapshot(
                config.fabric, selector, start_date=since, end_date=until
            )
            snapshot_warnings = list(client.notices)
        emit_snapshot(record, output, warnings=snapshot_warnings)


@app.command()
def compliance(
    ctx: typer.Context,
    host: HostOpt = None,
    username: UserOpt = None,
    password: PasswordOpt = None,
    domain: DomainOpt = DEFAULT_DOMAIN,
    fabric: FabricOpt = None,
    snapshot: Annotated[
        Optional[str],
        typer.Option(
            "--snapshot",
            help=(
                "Resolve this snapshot ('latest', 'latest-N', or an ID) and "
                "report compliance for its collection time instead of the "
                "newest run. Combine with --since/--until when needed."
            ),
        ),
    ] = None,
    fail_on_violations: Annotated[
        bool,
        typer.Option(
            "--fail-on-violations",
            help="Exit 3 when any compliance rule is violated.",
        ),
    ] = False,
    all_fabrics: Annotated[
        bool,
        typer.Option(
            "--all",
            help=(
                "Report compliance for every fabric in YAML `fabrics`, or the "
                "single YAML `fabric` / ND_FABRIC when no list is set."
            ),
        ),
    ] = False,
    since: SinceOpt = None,
    until: UntilOpt = None,
    output: OutputOpt = "text",
    verify_ssl: VerifyOpt = True,
    ca_bundle: CaBundleOpt = None,
    timeout: TimeoutOpt = 30,
    poll_interval: PollOpt = 15,
    verbose: VerboseOpt = False,
) -> None:
    """Report compliance rule status for a fabric (or every fabric with --all).

    Exits 3 with --fail-on-violations when any rule is violated.
    """
    configure_cli_logging(verbose)
    with handle_cli_errors(verbose):
        if (
            all_fabrics
            and ctx.get_parameter_source("fabric") == ParameterSource.COMMANDLINE
        ):
            raise InputError("--all cannot be combined with --fabric.")
        fabrics = configured_fabrics()
        if all_fabrics:
            if not fabrics:
                raise InputError(
                    "--all requires fabrics in YAML `fabrics`, YAML `fabric`, "
                    "or ND_FABRIC."
                )
            results: list[Result] = []
            failed: list[str] = []
            with nd_session(
                host=host,
                username=username,
                password=password,
                domain=domain,
                fabric=fabrics[0],
                verify_ssl=verify_ssl,
                ca_bundle=ca_bundle,
                timeout=timeout,
                poll_interval=poll_interval,
            ) as (_config, client):
                for name in fabrics:
                    note(f"Checking compliance for {name}...")
                    client.validate_fabric(name)
                    result, violated = run_compliance_check(
                        client,
                        name,
                        snapshot=snapshot,
                        since=since,
                        until=until,
                    )
                    extend_warnings(result, client)
                    results.append(result)
                    if violated:
                        failed.append(name)
            multi = MultiFabricResult(
                command="compliance",
                fabrics=results,
                failed_fabrics=failed,
            )
            typer.echo(render_multi(multi, output))
            if fail_on_violations and failed:
                raise AnomalyThresholdError(
                    f"Compliance rule(s) are violated on {', '.join(failed)}."
                )
            return

        with nd_session(
            host=host,
            username=username,
            password=password,
            domain=domain,
            fabric=fabric,
            verify_ssl=verify_ssl,
            ca_bundle=ca_bundle,
            timeout=timeout,
            poll_interval=poll_interval,
        ) as (config, client):
            note(f"Checking compliance for {config.fabric}...")
            result, violated = run_compliance_check(
                client,
                config.fabric,
                snapshot=snapshot,
                since=since,
                until=until,
            )
            extend_warnings(result, client)
        emit(result, output)
        if fail_on_violations and violated:
            raise AnomalyThresholdError(
                f"{violated} compliance rule(s) are violated on {config.fabric}."
            )


@app.command()
def doctor(
    host: HostOpt = None,
    username: UserOpt = None,
    password: PasswordOpt = None,
    domain: DomainOpt = DEFAULT_DOMAIN,
    fabric: FabricOpt = None,
    output: OutputOpt = "text",
    verify_ssl: VerifyOpt = True,
    ca_bundle: CaBundleOpt = None,
    verbose: VerboseOpt = False,
) -> None:
    """Check connectivity, credentials, and fabric visibility.

    Read-only; creates no jobs. Requires the same connection settings as other
    commands (--host, credentials, --fabric or ND_FABRIC).
    """
    configure_cli_logging(verbose)
    with handle_cli_errors(verbose):
        warnings: list[str] = []
        with nd_session(
            host=host,
            username=username,
            password=password,
            domain=domain,
            fabric=fabric,
            verify_ssl=verify_ssl,
            ca_bundle=ca_bundle,
            timeout=30,
            poll_interval=15,
        ) as (config, client):
            details: dict[str, object] = {
                "base_url": config.base_url,
                "normalized_host": normalize_host(host or ""),
                "tls_verification": "on" if verify_ssl or ca_bundle else "OFF",
            }
            domains = client.login_domains()
            known = [
                str(item.get("name", ""))
                for item in domains.get("domains") or []
                if isinstance(item, dict) and item.get("name")
            ]
            details["default_login_domain"] = domains.get("defaultDomain", "")
            details["login_domains"] = ", ".join(known)
            try:
                client.authenticate()
            except AuthError as exc:
                # /logindomains does not list `DefaultAuth`, which normally
                # authenticates, so an unlisted domain is only mentioned once
                # login has failed.
                if known and config.domain not in known:
                    raise AuthError(
                        f"{exc} This cluster advertises: {', '.join(known)}."
                    ) from exc
                raise
            details["authenticated_as"] = config.username
            fabrics = client.list_fabrics()
            aci = [fabric_name(item) for item in fabrics if is_aci_fabric(item)]
            details["fabrics_total"] = len(fabrics)
            details["aci_fabrics"] = ", ".join(sorted(aci)) or "(none)"
            client.validate_fabric(config.fabric)
            snapshots = client.list_snapshots(config.fabric)
            details["snapshots_visible"] = len(snapshots)
            details["newest_snapshot"] = (
                snapshots[0].get("collectionTimestamp", "") if snapshots else "(none)"
            )
            warnings.extend(client.notices)
        emit(
            Result(
                command="doctor",
                fabric=config.fabric,
                details=details,
                warnings=warnings,
            ),
            output,
        )
