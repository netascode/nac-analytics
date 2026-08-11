"""Root command line interface.

`nac-analytics` is organised as `nac-analytics <product> <verb>`: each Cisco
product is a command group (see ``nac_analytics.products``), plus global
commands like ``version``. This module mounts the registered product groups and
routes pre-Typer configuration loading to the selected product.
"""

from __future__ import annotations

import sys

import typer
from dotenv import find_dotenv, load_dotenv

from nac_analytics import __version__
from nac_analytics.core.cli_args import strip_config_option
from nac_analytics.core.exceptions import InputError
from nac_analytics.core.product import Product
from nac_analytics.products import REGISTRY, resolve_product

ROOT_HELP = """\
Change analytics for Cisco products.

Run a product group followed by a command, for example:

  nac-analytics nexus-dashboard doctor      (alias: nd)

Each product carries its own commands and configuration; see
`nac-analytics <product> --help`. Products available today are listed below;
more Cisco products are planned."""

app = typer.Typer(
    help=ROOT_HELP,
    add_completion=False,
    no_args_is_help=True,
)

# Mount every registered product as `nac-analytics <cli_name> ...`, with any
# short aliases hidden from the help so the surface stays uncluttered.
for _product in REGISTRY:
    app.add_typer(_product.app, name=_product.cli_name)
    for _alias in _product.aliases:
        app.add_typer(_product.app, name=_alias, hidden=True)


@app.command()
def version() -> None:
    """Print the version and exit."""
    typer.echo(f"nac-analytics {__version__}")


def _active_product(args: list[str]) -> Product | None:
    """Return the product the invocation selects, ignoring a leading --config."""
    _, rest = strip_config_option(args)
    for token in rest:
        if token.startswith("-"):
            return None
        return resolve_product(token)
    return None


def _wants_help(args: list[str]) -> bool:
    """Return True when the invocation only resolves or prints help.

    Config must not be loaded or validated in this case. ``--help`` is an
    eager Click option that short-circuits (printing help and exiting) before
    any command runs, so loading config first would let an invalid or
    flat/unscoped ``nac-analytics.yaml`` break a plain ``--help``. A product
    group invoked with no verb likewise falls back to printing its group help
    (``no_args_is_help``), so a bare product token counts as a help request
    too. Real command execution always carries a verb and no help flag, and
    still triggers the strict config bootstrap below.
    """
    _, rest = strip_config_option(args)
    if "--help" in rest or "-h" in rest:
        return True
    non_flags = [token for token in rest if not token.startswith("-")]
    return len(non_flags) == 1 and resolve_product(non_flags[0]) is not None


def main() -> None:
    args = sys.argv[1:]
    product = _active_product(args)
    load_config = (
        product is not None and product.bootstrap is not None and not _wants_help(args)
    )
    try:
        if load_config:
            assert product is not None and product.bootstrap is not None
            remaining = product.bootstrap(args)
        else:
            _, remaining = strip_config_option(args)
    except InputError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise SystemExit(InputError.exit_code) from exc
    sys.argv = [sys.argv[0], *remaining]
    # `.env` is read after YAML so a real environment variable or CLI flag still
    # wins. Values already in `os.environ` are left untouched.
    load_dotenv(find_dotenv(usecwd=True))
    if product is not None and product.apply_legacy_env is not None:
        product.apply_legacy_env()
    app()
