"""APIC managed-object tree helpers."""

from __future__ import annotations

from nac_analytics.products.nexus_dashboard.apic import ApicObject


def _node(
    dn: str,
    *,
    cl: str | None = None,
    children: list[ApicObject] | None = None,
) -> ApicObject:
    return ApicObject(cl, {"dn": dn}, children or [], None)


def test_insert_finds_existing_dn_and_updates() -> None:
    root = _node("uni")
    root.insert(_node("uni/tn-common", cl="fvTenant", children=[]))
    root.insert(_node("uni/tn-common", cl="fvTenant", children=[]))

    matches = root.find(dn="uni/tn-common")
    assert len(matches) == 1


def test_insert_creates_parent_placeholders_for_deep_dn() -> None:
    root = _node("uni")
    root.insert(_node("uni/tn-common/ap-app", cl="fvAp"))

    parent = root.find(dn="uni/tn-common")
    child = root.find(dn="uni/tn-common/ap-app")
    assert len(parent) == 1
    assert len(child) == 1
    assert child[0].cl == "fvAp"


def test_find_filters_by_class_name() -> None:
    root = _node("uni")
    root.insert(_node("uni/tn-common", cl="fvTenant"))
    root.insert(_node("uni/tn-other", cl="fvTenant"))

    assert len(root.find(cl="fvTenant")) == 2
    assert len(root.find(dn="uni/tn-common", cl="fvTenant")) == 1
