"""The seam every product plugs into.

A :class:`Product` bundles a product's Typer sub-app with the small amount of
metadata the root CLI needs to mount it (`nac-analytics <product> <verb>`) and
to load its scoped configuration. Adding a Cisco product to nac-analytics means
building one of these and registering it in ``nac_analytics.products`` — no
changes to the root CLI.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import typer


@dataclass(frozen=True)
class Product:
    """One Cisco product exposed as a `nac-analytics` command group."""

    key: str
    """Canonical identifier, also the YAML config section (e.g. ``nexus_dashboard``)."""

    cli_name: str
    """Primary command token (e.g. ``nexus-dashboard``)."""

    app: typer.Typer
    """The product's Typer sub-app, holding its verbs.

    Its ``help`` first line becomes the product's short description in the root
    ``--help`` command list.
    """

    aliases: tuple[str, ...] = ()
    """Extra command tokens that resolve to this product (e.g. ``nd``)."""

    bootstrap: Callable[[list[str]], list[str]] | None = None
    """Load this product's scoped config into the environment; return remaining argv."""

    apply_legacy_env: Callable[[], None] | None = None
    """Optional hook to map retired environment variable names, run after ``.env``."""

    tokens: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tokens", (self.cli_name, *self.aliases))

    def matches(self, token: str) -> bool:
        return token in self.tokens
