"""
Dashboard views — one view per dashboard page.

Architecture decision: Function-based views over class-based views.

Why: CBVs are powerful when you need reuse (list, detail, create, update, delete).
This dashboard has mostly single-purpose views (show daily summary, show category
breakdown) where CBV inheritance adds abstraction without benefit. FBVs are
explicit, easier to debug, and directly readable by reviewers.

Architecture decision: HTMX partials over full page reloads for filters.

Why: Filtering by date range or category should update the charts without a full
page reload. HTMX lets us return HTML fragments from the same view based on the
HX-Request header. No JS framework, no API endpoints, no JSON serialisation.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .services import bigquery_client as bq

logger = logging.getLogger(__name__)


def _get_default_date_range(request: HttpRequest) -> int:
    """Get the default date range from user preferences, falling back to 30 days.

    Returns an int in every path. The previous implementation returned the raw
    query-string value (a str) before the coercion below could run, so callers
    could receive a string where the signature promises an int.
    """
    if request.user.is_authenticated:
        try:
            return request.user.dashboard_prefs.default_date_range_days
        except ObjectDoesNotExist:
            logger.debug(
                "No dashboard preferences for user %s; using the request default.",
                request.user,
            )
    try:
        return int(request.GET.get("days", 30))
    except (ValueError, TypeError):
        return 30


def index(request: HttpRequest) -> HttpResponse:
    """
    Main dashboard view — shows all pipeline visualisations.

    HTMX behaviour: If the request includes HX-Request header (triggered by
    filter change or refresh button), only the main content partial is returned.
    If it is a full page load, the complete page with header and navigation
    is rendered.
    """
    days = _get_default_date_range(request)
    snapshot = bq.fetch_dashboard_snapshot(days=days)

    context = {
        "snapshot": snapshot,
        "days": days,
        "page_title": "Pipeline Dashboard",
        "project_id": settings.BIGQUERY_PROJECT_ID,
    }

    template = (
        "dashboard/partials/dashboard_content.html"
        if request.htmx
        else "dashboard/index.html"
    )
    return render(request, template, context)


def daily_summary_view(request: HttpRequest) -> HttpResponse:
    """
    Daily transaction summary — table + chart view.

    This view is HTMX-loadable for the "expand" interaction on the main dashboard.
    """
    days = _get_default_date_range(request)
    summaries = bq.fetch_daily_summaries(days=days)

    return render(
        request,
        "dashboard/partials/daily_summary.html",
        {
            "summaries": summaries,
            "days": days,
        },
    )


def category_breakdown_view(request: HttpRequest) -> HttpResponse:
    """
    Category breakdown — shows spending by category for the selected period.
    """
    days = _get_default_date_range(request)
    summaries = bq.fetch_category_summaries(days=days)

    # Group by category for the template
    categories: dict[str, list] = {}
    for s in summaries:
        categories.setdefault(s.category, []).append(s)

    return render(
        request,
        "dashboard/partials/category_breakdown.html",
        {
            "categories": categories,
            "days": days,
        },
    )


def pipeline_runs_view(request: HttpRequest) -> HttpResponse:
    """
    Pipeline run history — observability panel showing recent executions.
    """
    runs = bq.fetch_recent_pipeline_runs(limit=50)

    return render(
        request,
        "dashboard/partials/pipeline_runs.html",
        {
            "runs": runs,
        },
    )


def data_quality_view(request: HttpRequest) -> HttpResponse:
    """
    Data quality dashboard — shows pipeline health and validation metrics.
    """
    metrics = bq.fetch_data_quality_metrics()

    return render(
        request,
        "dashboard/partials/data_quality.html",
        {
            "metrics": metrics,
        },
    )
