"""Product registry: the Cisco products nac-analytics exposes as command groups.

Adding a product is deliberately small: build a
:class:`~nac_analytics.core.product.Product` in its package and list it in
:data:`REGISTRY`. The root CLI mounts everything here automatically.
"""

from __future__ import annotations

from nac_analytics.core.product import Product
from nac_analytics.products.nexus_dashboard import PRODUCT as NEXUS_DASHBOARD

REGISTRY: tuple[Product, ...] = (NEXUS_DASHBOARD,)


def resolve_product(token: str) -> Product | None:
    """Return the product a command token (name or alias) selects, if any."""
    for product in REGISTRY:
        if product.matches(token):
            return product
    return None
