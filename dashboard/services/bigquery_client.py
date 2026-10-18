"""
BigQuery read-only client — connects to gcp-data-pipeline analytics tables.

Architecture decision: Read-only client over full CRUD.

Why: This dashboard is a visualisation layer over the existing pipeline, not
a data entry point. A read-only client prevents accidental writes, keeps the
surface area small, and makes the integration testable with just SELECT
permissions. Data flows one way: pipeline → BigQuery → dashboard.

Architecture decision: Raw SQL queries over Django ORM.

Why: BigQuery is not a relational OLTP database — it is a columnar warehouse.
Django's ORM is designed for PostgreSQL-style row operations. Raw SQL lets us
use BigQuery-specific features (time partitioning, clustering, UNNEST) that
the ORM cannot express. The queries are simple enough that SQL injection is
not a concern (no user input interpolation in table names).

Architecture decision: Application default credentials for authentication.

Why: ADC works seamlessly across local dev (gcloud auth), CI (workload identity),
and production (GCP service account attached to the runtime). No credential
files to manage, no rotation to schedule.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from django.conf import settings
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data transfer objects — explicit shape for every query result
# ---------------------------------------------------------------------------
# Architecture decision: Dataclasses over dicts or TypedDicts.
# Why: Dataclasses give us type-checked, immutable value objects with clear
# field names. Dicts are opaque — you have to read the query to know what
# keys exist. TypedDicts add type hints but no runtime validation. Dataclasses
# are the right balance for query result transfer objects.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DailySummary:
    """One row from v_daily_summary — transaction counts and amounts per day."""

    date: date
    transaction_count: int
    unique_transactions: int
    total_amount: float
    avg_amount: float
    currency_count: int
    region_count: int
    category_count: int


@dataclass(frozen=True)
class CategorySummary:
    """One row from v_category_summary — spending breakdown by category."""

    category: str
    date: date
    transaction_count: int
    total_amount: float
    avg_amount: float


@dataclass(frozen=True)
class RegionSummary:
    """One row from v_region_summary — spending breakdown by region and quarter."""

    region: str
    quarter: str
    transaction_count: int
    total_amount: float
    avg_amount: float


@dataclass(frozen=True)
class PipelineRun:
    """One row from v_pipeline_runs — observability for pipeline executions."""

    run_id: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    rows_read: int | None
    rows_written: int | None
    error_count: int | None
    status: str
    error_message: str | None


@dataclass(frozen=True)
class DataQualityMetric:
    """One row from v_data_quality — aggregate pipeline health indicators."""

    metric: str
    value: int


@dataclass(frozen=True)
class DashboardSnapshot:
    """Complete snapshot of all dashboard data for one request."""

    daily_summaries: list[DailySummary] = field(default_factory=list)
    category_summaries: list[CategorySummary] = field(default_factory=list)
    region_summaries: list[RegionSummary] = field(default_factory=list)
    recent_runs: list[PipelineRun] = field(default_factory=list)
    quality_metrics: list[DataQualityMetric] = field(default_factory=list)
    total_transactions: int = 0
    total_amount: float = 0.0
    avg_transaction: float = 0.0
    pipeline_health: str = "unknown"


# ---------------------------------------------------------------------------
# BigQuery client singleton
# ---------------------------------------------------------------------------

_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    """
    Lazy-initialised BigQuery client singleton.

    Architecture decision: Module-level singleton over per-request instantiation.
    Why: Creating a BigQuery client requires network calls (to discover service
    endpoints, fetch credentials). Doing this on every request adds 200-500ms
    latency. A module-level singleton, initialised once, eliminates this overhead.
    In production, the process lives long enough that the client is reused across
    many requests, making the amortised cost negligible.
    """
    global _client
    if _client is None:
        _client = bigquery.Client(project=settings.BIGQUERY_PROJECT_ID)
        logger.info(
            "BigQuery client initialised for project %s", settings.BIGQUERY_PROJECT_ID
        )
    return _client


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def _rows_to_dataclass(
    rows, cls: type, field_map: dict[str, str] | None = None
) -> list:
    """
    Convert BigQuery RowIterator rows to a list of dataclass instances.

    Architecture decision: Explicit field mapping over **row pattern.
    Why: BigQuery Row objects support both attribute access (row.date) and
    dict access (row["date"]). The dict approach is more explicit about
    which fields we expect, and the field_map parameter handles naming
    mismatches between SQL column names and Python field names.
    """
    results = []
    for row in rows:
        kwargs = {}
        for field_name in cls.__dataclass_fields__:
            bq_field = (
                field_map.get(field_name, field_name) if field_map else field_name
            )
            kwargs[field_name] = row.get(bq_field)
        results.append(cls(**kwargs))
    return results


def _execute_query(sql: str) -> list[dict[str, Any]]:
    """Execute a SQL query and return results as a list of dicts."""
    client = _get_client()
    query_job = client.query(sql)
    return [dict(row) for row in query_job.result()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_daily_summaries(days: int = 30) -> list[DailySummary]:
    """
    Fetch daily transaction summaries for the last N days.
    """
    sql = f"""
        SELECT
            date,
            transaction_count,
            unique_transactions,
            total_amount,
            avg_amount,
            currency_count,
            region_count,
            category_count
        FROM `{settings.BIGQUERY_PROJECT_ID}.{settings.BIGQUERY_DATASET_ANALYTICS}.v_daily_summary`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY date DESC
    """
    rows = _execute_query(sql)
    return _rows_to_dataclass(rows, DailySummary)


def fetch_category_summaries(days: int = 30) -> list[CategorySummary]:
    """
    Fetch category breakdown for the last N days.
    """
    sql = f"""
        SELECT
            category,
            date,
            transaction_count,
            total_amount,
            avg_amount
        FROM `{settings.BIGQUERY_PROJECT_ID}.{settings.BIGQUERY_DATASET_ANALYTICS}.v_category_summary`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY category, date DESC
    """
    rows = _execute_query(sql)
    return _rows_to_dataclass(rows, CategorySummary)


def fetch_region_summaries() -> list[RegionSummary]:
    """
    Fetch regional breakdown for all available quarters.
    """
    sql = f"""
        SELECT
            region,
            _quarter AS quarter,
            transaction_count,
            total_amount,
            avg_amount
        FROM `{settings.BIGQUERY_PROJECT_ID}.{settings.BIGQUERY_DATASET_ANALYTICS}.v_region_summary`
        ORDER BY region, quarter DESC
    """
    rows = _execute_query(sql)
    return _rows_to_dataclass(rows, RegionSummary)


def fetch_recent_pipeline_runs(limit: int = 20) -> list[PipelineRun]:
    """
    Fetch the most recent pipeline runs for the observability panel.
    """
    sql = f"""
        SELECT
            run_id,
            started_at,
            completed_at,
            duration_seconds,
            rows_read,
            rows_written,
            error_count,
            status,
            error_message
        FROM `{settings.BIGQUERY_PROJECT_ID}.{settings.BIGQUERY_DATASET_ANALYTICS}.v_pipeline_runs`
        ORDER BY started_at DESC
        LIMIT {limit}
    """
    rows = _execute_query(sql)
    return _rows_to_dataclass(rows, PipelineRun)


def fetch_data_quality_metrics() -> list[DataQualityMetric]:
    """
    Fetch aggregate pipeline health metrics for the data quality panel.
    """
    sql = f"""
        SELECT metric, value
        FROM `{settings.BIGQUERY_PROJECT_ID}.{settings.BIGQUERY_DATASET_ANALYTICS}.v_data_quality`
    """
    rows = _execute_query(sql)
    return _rows_to_dataclass(rows, DataQualityMetric)


def fetch_dashboard_snapshot(days: int = 30) -> DashboardSnapshot:
    """
    Fetch all dashboard data in a single coordinated call.

    Architecture decision: Separate queries over a single big query.

    Why: BigQuery charges per byte scanned, not per query. One big query
    that joins all views would scan more data than necessary — joining
    daily summaries (few rows) with daily run logs (few rows) forces
    BigQuery to scan both tables even though the join adds no value.
    Separate queries let BigQuery prune partitions independently.
    """
    daily = fetch_daily_summaries(days)
    categories = fetch_category_summaries(days)
    regions = fetch_region_summaries()
    runs = fetch_recent_pipeline_runs()
    quality = fetch_data_quality_metrics()

    total_txns = sum(s.transaction_count for s in daily) if daily else 0
    total_amt = sum(s.total_amount for s in daily) if daily else 0.0
    avg_txn = round(total_amt / total_txns, 2) if total_txns > 0 else 0.0

    # Derive pipeline health from the most recent run
    pipeline_health = "unknown"
    if runs:
        latest = runs[0]
        if latest.status == "success":
            pipeline_health = "healthy"
        elif latest.status == "running":
            pipeline_health = "running"
        elif latest.status == "failed":
            pipeline_health = "degraded"

    return DashboardSnapshot(
        daily_summaries=daily,
        category_summaries=categories,
        region_summaries=regions,
        recent_runs=runs,
        quality_metrics=quality,
        total_transactions=total_txns,
        total_amount=round(total_amt, 2),
        avg_transaction=avg_txn,
        pipeline_health=pipeline_health,
    )
