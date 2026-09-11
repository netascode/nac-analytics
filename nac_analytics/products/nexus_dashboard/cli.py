"""Nexus Dashboard command group (entry layer).

Typer commands that orchestrate config, client calls, domain modules, and
reporting for `nac-analytics nexus-dashboard <verb>`.
"""

from __future__ import annotations

import typer

from nac_analytics.products.nexus_dashboard.commands import register_commands

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

register_commands(app)
