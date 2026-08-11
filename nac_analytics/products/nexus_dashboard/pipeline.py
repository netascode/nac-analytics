"""Shared post-job delta analysis steps (domain layer).

Used by prechange and delta commands after the analysis job completes.
"""

from __future__ import annotations

from typing import Any

from nac_analytics.core.report import Result, build_verdict
from nac_analytics.products.nexus_dashboard.client import NDClient
from nac_analytics.products.nexus_dashboard.delta import (
    collect_delta_detail_warnings,
    fetch_delta_details,
)
from nac_analytics.products.nexus_dashboard.delta_format import render_delta_detail_text


def finish_delta_analysis(
    client: NDClient,
    *,
    command: str,
    fabric: str,
    name: str,
    job_id: str,
    thresholds: tuple[str, ...],
    detail_level: str,
    include_acknowledged: bool,
    details: dict[str, object],
    compliance: dict[str, Any] | None = None,
) -> Result:
    """Fetch delta summary and detail, then build a command ``Result``."""
    summary = client.delta_summary(job_id, include_acknowledged=include_acknowledged)
    delta_detail = fetch_delta_details(
        client,
        fabric=fabric,
        job_id=job_id,
        detail=detail_level,
        include_acknowledged=include_acknowledged,
    )
    result = Result(
        command=command,
        fabric=fabric,
        name=name,
        details=details,
        anomaly_summary=summary,
        delta_detail=delta_detail,
        detail_lines=render_delta_detail_text(
            delta_detail,
            detail_level=detail_level,
            anomaly_summary=summary or None,
        ),
        detail_level=detail_level,
        compliance=compliance or {},
        verdict=build_verdict(summary, thresholds),
    )
    result.warnings.extend(
        collect_delta_detail_warnings(delta_detail, anomaly_summary=summary)
    )
    return result
