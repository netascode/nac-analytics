"""Gate command output and config scheme helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from nac_analytics.core.config import host_scheme
from nac_analytics.core.report import (
    DEFAULT_FAIL_ON,
    GATE_REPORT_FILES,
    Result,
    build_verdict,
    render,
)
from nac_analytics.products.nexus_dashboard.cli import (
    _emit_gate_result,
    _emit_snapshot,
    _resolve_pre_post,
)


def test_host_scheme_defaults_to_https() -> None:
    assert host_scheme("nd.example.com") == ("https", "nd.example.com")


def test_host_scheme_accepts_http_prefix() -> None:
    assert host_scheme("http://nd.example.com") == ("http", "nd.example.com")


def test_resolve_pre_post_prefers_positionals() -> None:
    pre, post = _resolve_pre_post(
        "a",
        "b",
        prior="c",
        later="d",
        default_pre="latest-1",
        default_post="latest",
    )
    assert (pre, post) == ("a", "b")


def test_resolve_pre_post_falls_back_to_deprecated_flags() -> None:
    pre, post = _resolve_pre_post(
        None,
        None,
        prior="snap-1",
        later="snap-2",
        default_pre="latest-1",
        default_post="latest",
    )
    assert (pre, post) == ("snap-1", "snap-2")


def test_emit_snapshot_text_prints_id_only(capsys: pytest.CaptureFixture[str]) -> None:
    _emit_snapshot(
        {"snapshotId": "abc-123", "collectionTimestamp": "2026-01-01T00:00:00Z"},
        "text",
    )
    assert capsys.readouterr().out.strip() == "abc-123"


def test_emit_gate_result_writes_junit_report(tmp_path: Path) -> None:
    result = Result(
        command="delta",
        fabric="FABRIC-A",
        verdict=build_verdict({"newAnomaliesCount": 0}, DEFAULT_FAIL_ON),
    )
    previous = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        _emit_gate_result(result, output="junit", report_file=None)
        report = tmp_path / GATE_REPORT_FILES["delta"]
        assert report.is_file()
        assert "<testsuites" in report.read_text(encoding="utf-8")
    finally:
        os.chdir(previous)


def test_emit_gate_result_text_on_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = Result(
        command="delta",
        fabric="FABRIC-A",
        details={"pre_snapshot_id": "a", "post_snapshot_id": "b"},
        verdict=build_verdict({"newAnomaliesCount": 0}, DEFAULT_FAIL_ON),
    )
    _emit_gate_result(result, output="text", report_file=None)
    out = capsys.readouterr().out
    assert "pre_snapshot_id" in out
    assert render(result, "text") in out
