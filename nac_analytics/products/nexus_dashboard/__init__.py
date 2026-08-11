"""Cisco Nexus Dashboard product package.

Exposes :data:`PRODUCT`, the :class:`~nac_analytics.core.product.Product` the
root CLI mounts as the ``nexus-dashboard`` (alias ``nd``) command group.
"""

from __future__ import annotations

from nac_analytics.core.product import Product
from nac_analytics.products.nexus_dashboard.cli import app
from nac_analytics.products.nexus_dashboard.settings import (
    apply_legacy_env_aliases,
    bootstrap_settings,
)

PRODUCT = Product(
    key="nexus_dashboard",
    cli_name="nexus-dashboard",
    aliases=("nd",),
    app=app,
    bootstrap=bootstrap_settings,
    apply_legacy_env=apply_legacy_env_aliases,
)
