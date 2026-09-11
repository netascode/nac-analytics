"""Register Nexus Dashboard CLI commands on the Typer app."""

from __future__ import annotations

import typer

from .analyze import analyze
from .compliance import compliance
from .delta import delta
from .doctor import doctor
from .prechange import prechange
from .snapshots import snapshots


def register_commands(app: typer.Typer) -> None:
    app.command()(doctor)
    app.command()(snapshots)
    app.command()(analyze)
    app.command()(prechange)
    app.command()(delta)
    app.command()(compliance)
