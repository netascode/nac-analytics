"""Assurance analysis trigger command."""

from __future__ import annotations

from typing import Annotated

import typer

from nac_analytics.core.exceptions import ApiError, InputError
from nac_analytics.core.progress import note
from nac_analytics.products.nexus_dashboard.config import DEFAULT_DOMAIN

from . import _helpers
from ._helpers import (
    CaBundleOpt,
    DomainOpt,
    FabricOpt,
    HostOpt,
    PasswordOpt,
    PollOpt,
    TimeoutOpt,
    UserOpt,
    VerboseOpt,
    VerifyOpt,
    _analysis_trigger_error,
    _build_config,
    _connect_message,
    _emit_notices,
    _emit_snapshot,
    run_command,
)


def analyze(
    host: HostOpt = None,
    username: UserOpt = None,
    password: PasswordOpt = None,
    domain: DomainOpt = DEFAULT_DOMAIN,
    fabric: FabricOpt = None,
    no_wait: Annotated[
        bool,
        typer.Option(
            "--no-wait",
            help=(
                "Print the analysis job ID and exit instead of waiting. This is "
                "a job ID, not a snapshotId; it cannot be passed to delta."
            ),
        ),
    ] = False,
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output format: text (snapshot ID only), json, or yaml.",
        ),
    ] = "text",
    timeout: TimeoutOpt = 30,
    poll_interval: PollOpt = 15,
    verify_ssl: VerifyOpt = True,
    ca_bundle: CaBundleOpt = None,
    verbose: VerboseOpt = False,
) -> None:
    """Trigger an assurance analysis and print the snapshot ID it produces."""

    def body() -> None:
        if output not in ("text", "json", "yaml"):
            raise InputError(
                f"Unknown output format '{output}'. Choose from: text, json, yaml."
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
        note(_connect_message(config))
        with _helpers.NDClient(config) as client:
            client.validate_fabric(config.fabric)
            # Taken before triggering so a snapshot that already existed can
            # never be mistaken for the one this run produces.
            baseline = (
                None if no_wait else client.latest_collection_timestamp(config.fabric)
            )
            note(f"Triggering an assurance analysis on {config.fabric}...")
            try:
                job_id = client.trigger_assurance_analysis(config.fabric)
            except ApiError as exc:
                raise _analysis_trigger_error(exc) from exc
            if no_wait:
                _emit_notices(client)
                typer.echo(job_id)
                return
            note(
                f"Waiting for analysis {job_id} to produce a snapshot "
                f"(up to {timeout} minutes)..."
            )
            record = client.wait_for_analysis_snapshot(
                config.fabric, job_id, baseline=baseline
            )
            _emit_notices(client)
        _emit_snapshot(record, output)

    run_command(verbose, body)
