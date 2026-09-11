"""Connectivity and credentials check command."""

from __future__ import annotations

from nac_analytics.core.exceptions import AuthError
from nac_analytics.core.progress import note
from nac_analytics.core.report import Result
from nac_analytics.products.nexus_dashboard.client import fabric_name, is_aci_fabric
from nac_analytics.products.nexus_dashboard.config import DEFAULT_DOMAIN, normalise_host

from . import _helpers
from ._helpers import (
    CaBundleOpt,
    DomainOpt,
    FabricOpt,
    HostOpt,
    OutputOpt,
    PasswordOpt,
    UserOpt,
    VerboseOpt,
    VerifyOpt,
    _build_config,
    _connect_message,
    _emit,
    run_command,
)


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

    def body() -> None:
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
        details: dict[str, object] = {
            "base_url": config.base_url,
            "normalised_host": normalise_host(host or ""),
            "tls_verification": "on" if verify_ssl or ca_bundle else "OFF",
        }
        warnings: list[str] = []
        note(_connect_message(config))
        with _helpers.NDClient(config) as client:
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
        _emit(
            Result(
                command="doctor",
                fabric=config.fabric,
                details=details,
                warnings=warnings,
            ),
            output,
        )

    run_command(verbose, body)
