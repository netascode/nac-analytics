"""RN prefix to APIC class resolution."""

from __future__ import annotations

from nac_analytics.products.nexus_dashboard.apic import ApicObject
from nac_analytics.products.nexus_dashboard.rn_mappings import (
    RN_PREFIX_CLASSNAME_MAPPINGS,
)
from nac_analytics.products.nexus_dashboard.tf_plan import _resolve_static_classnames


def test_tn_prefix_maps_to_fv_tenant_with_name_attribute() -> None:
    root = ApicObject(None, {"dn": "uni/tn-common"}, [], None)
    _resolve_static_classnames(root)

    assert root.cl == RN_PREFIX_CLASSNAME_MAPPINGS["tn"]["class"]
    assert root.attributes["name"] == "common"


def test_bracketed_subnet_ip_is_extracted() -> None:
    root = ApicObject(
        None,
        {"dn": "uni/tn-common/subnet-[10.1.1.1-24]"},
        [],
        None,
    )
    _resolve_static_classnames(root)

    assert root.cl == RN_PREFIX_CLASSNAME_MAPPINGS["subnet"]["class"]
    assert root.attributes["ip"] == "10.1.1.1-24"
