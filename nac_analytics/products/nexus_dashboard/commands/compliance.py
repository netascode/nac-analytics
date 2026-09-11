"""Compliance reporting command."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from typer._click.core import ParameterSource

from nac_analytics.core.exceptions import AnomalyThresholdError, InputError
from nac_analytics.core.progress import note
from nac_analytics.core.report import MultiFabricResult, Result, render_multi
from nac_analytics.products.nexus_dashboard.compliance import run_compliance_check
from nac_analytics.products.nexus_dashboard.config import DEFAULT_DOMAIN
from nac_analytics.products.nexus_dashboard.settings import configured_fabrics

from . import _helpers
from ._helpers import (
    CaBundleOpt,
    DomainOpt,
    FabricOpt,
    HostOpt,
    OutputOpt,
    PasswordOpt,
    PollOpt,
    SinceOpt,
    TimeoutOpt,
    UntilOpt,
    UserOpt,
    VerboseOpt,
    VerifyOpt,
    _build_config,
    _connect_message,
    _emit,
    _extend_warnings,
    run_command,
)


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

    def body() -> None:
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
            config = _build_config(
                host=host,
                username=username,
                password=password,
                domain=domain,
                fabric=fabrics[0],
                verify_ssl=verify_ssl,
                ca_bundle=ca_bundle,
                timeout=timeout,
                poll_interval=poll_interval,
            )
            results: list[Result] = []
            failed: list[str] = []
            note(_connect_message(config))
            with _helpers.NDClient(config) as client:
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
                    _extend_warnings(result, client)
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
            note(f"Checking compliance for {config.fabric}...")
            result, violated = run_compliance_check(
                client,
                config.fabric,
                snapshot=snapshot,
                since=since,
                until=until,
            )
            _extend_warnings(result, client)
        _emit(result, output)
        if fail_on_violations and violated:
            raise AnomalyThresholdError(
                f"{violated} compliance rule(s) are violated on {config.fabric}."
            )

    run_command(verbose, body)
