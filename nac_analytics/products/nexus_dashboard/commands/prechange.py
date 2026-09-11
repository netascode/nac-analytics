"""Pre-change analysis command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from nac_analytics.core.exceptions import ApiError, InputError
from nac_analytics.core.progress import note
from nac_analytics.core.report import GATE_DEFAULT_OUTPUT, parse_fail_on
from nac_analytics.products.nexus_dashboard.config import DEFAULT_DOMAIN
from nac_analytics.products.nexus_dashboard.delta import (
    PRECHANGE_DEFAULT_DETAIL,
    normalize_delta_detail,
)
from nac_analytics.products.nexus_dashboard.tf_plan import prepare_prechange_content

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
    _prechange_result_from_job,
    run_command,
)


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

    def body() -> None:
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
        detail_level = normalize_delta_detail(detail)
        upload_content: bytes | None = None
        upload_name = ""
        resume_id: str | None = None
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
        note(_connect_message(config))
        with _helpers.NDClient(config) as client:
            client.validate_fabric(config.fabric)
            if job_id:
                assert resume_id is not None
                note(f"Waiting for pre-change analysis {resume_id}...")
                job = client.wait_prechange_analysis(resume_id)
                job_name = name or str(job.get("name") or resume_id)
                result = _prechange_result_from_job(
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
                job_name = name or _auto_name("prechange")
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
                result = _prechange_result_from_job(
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
            _extend_warnings(result, client)
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
        _emit_gate_result(result, output=output, report_file=report_file)
        _enforce(result)

    run_command(verbose, body)
