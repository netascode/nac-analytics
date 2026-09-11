"""Snapshot resolution command."""

from __future__ import annotations

from typing import Annotated

import typer

from nac_analytics.core.exceptions import InputError
from nac_analytics.core.progress import note
from nac_analytics.products.nexus_dashboard.config import DEFAULT_DOMAIN

from . import _helpers
from ._helpers import (
    CaBundleOpt,
    DomainOpt,
    FabricOpt,
    HostOpt,
    PasswordOpt,
    SinceOpt,
    UntilOpt,
    UserOpt,
    VerboseOpt,
    VerifyOpt,
    _build_config,
    _connect_message,
    _emit_notices,
    _emit_snapshot,
    run_command,
)


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
            timeout=30,
            poll_interval=15,
        )
        note(_connect_message(config))
        with _helpers.NDClient(config) as client:
            client.validate_fabric(config.fabric)
            record = client.resolve_snapshot(
                config.fabric, selector, start_date=since, end_date=until
            )
            _emit_notices(client)
        _emit_snapshot(record, output)

    run_command(verbose, body)
