# ADR 004: BigQuery Read-Only Access over Local Database

## Status

Accepted (2026-07-07)

## Context

The dashboard visualises data from the gcp-data-pipeline ETL project, which loads data into BigQuery. The dashboard needs to query this data for charts and analytics. Two approaches are possible:

1. Query BigQuery directly from the Django application
2. Periodically export BigQuery data to a local PostgreSQL or SQLite database and query locally

The gcp-data-pipeline transforms raw data into analytics-ready tables in BigQuery. The dashboard reads from these tables to display:
- Daily transaction volumes
- Category and regional spending breakdowns
- Pipeline run health and data quality metrics

## Decision

Query BigQuery directly using the `google-cloud-bigquery` Python client, with read-only credentials scoped to the specific dataset.

## Consequences

### Positive
- Always current — data is queried live from BigQuery, no data freshness delay
- Zero local data storage — no database to maintain, back up, or migrate
- Leverages BigQuery's compute — aggregation queries run on BigQuery's infrastructure, not on the Django server
- Simplifies deployment — the Docker container needs no database volume or connection string

### Negative
- Query latency — BigQuery queries take 1-3 seconds even for simple aggregations (cold start)
- Always-on internet — the dashboard cannot function without BigQuery access
- Cost — BigQuery charges per query (though analytics tables are small enough to stay within free tier)
- More complex local development — developers need either a real BigQuery dataset or mock data

### Mitigations
- Queries are designed to be simple aggregations that BigQuery can process in seconds — no joins across terabytes
- A `MockBigQueryClient` class is provided for local development and testing, returning canned data without network calls
- Query caching is implemented at the view level — the same data is cached for 5 minutes to avoid repeated queries on page reload
- BigQuery's free tier covers 1 TB of query data per month — the dashboard's query volume is well under this limit

## Alternatives Considered

### PostgreSQL local replica
- **Pros**: Sub-millisecond queries, works offline, no query costs
- **Cons**: Requires scheduled data sync (complexity), stale data between syncs, additional database to maintain
- **Rejected because**: The data sync pipeline adds architectural complexity that outweighs the latency benefit. The dashboard is designed to demonstrate the pipeline — reading from the pipeline's output is architecturally honest.

### SQLite cache
- **Pros**: Zero-configuration, file-based, no server process
- **Cons**: No concurrent write support, limited SQL features, not suitable for production
- **Rejected because**: SQLite cannot handle concurrent dashboard users. The cache would need to be regenerated per request or per session, defeating the purpose of caching.

### DuckDB
- **Pros**: Fast analytical queries on local data, supports Parquet/CSV, no server required
- **Cons**: Still requires data sync from BigQuery, less mature Python client, fewer community resources
- **Rejected because**: Like PostgreSQL, the data sync pipeline adds complexity. DuckDB is excellent for local analytics but adds another moving part to the deployment.
