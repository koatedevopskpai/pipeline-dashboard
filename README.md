# Pipeline Dashboard

> A Django full-stack dashboard that visualises ETL pipeline data from the [gcp-data-pipeline](https://github.com/koate-kpai/gcp-data-pipeline) project. Server-rendered HTML, HTMX interactivity, Chart.js visualisations, and an AI chat widget powered by Claude.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Dashboard                       │
│  ┌──────────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │  Overview        │   │  Daily       │   │  Category   │  │
│  │  · Pipeline      │   │  Summary     │   │  Breakdown  │  │
│  │  · Data Quality  │   │  · Volume    │   │  · Spending │  │
│  │  · Recent Runs   │   │  · Trends    │   │  · Regions  │  │
│  └────────┬─────────┘   └──────┬───────┘   └──────┬─────┘  │
│           │                    │                   │         │
│           └────────────────────┼───────────────────┘         │
│                              │                              │
│                    ┌─────────▼──────────┐                   │
│                    │    Django Views     │                   │
│                    │  (FBVs + HTMX)     │                   │
│                    └─────────┬──────────┘                   │
│                              │                              │
│           ┌──────────────────┼──────────────────┐           │
│           ▼                  ▼                  ▼           │
│   ┌──────────────┐  ┌───────────────┐  ┌──────────────┐    │
│   │  BigQuery    │  │     Claude    │  │   Django     │    │
│   │  Read Client │  │    API Chat   │  │   Admin      │    │
│   └──────┬───────┘  └───────┬───────┘  └──────────────┘    │
│          │                  │                               │
└──────────┼──────────────────┼───────────────────────────────┘
           ▼                  ▼
   ┌──────────────┐   ┌──────────────┐
   │  BigQuery    │   │  Claude API  │
   │  (Pipeline   │   │  (Anthropic) │
   │   Analytics)  │   │              │
   └──────────────┘   └──────────────┘
```

---

## Design Decisions

All architectural decisions are documented as Architecture Decision Records (ADRs) in `docs/adr/`:

| ADR | Title | Key Rationale |
|-----|-------|--------------|
| 001 | Django over FastAPI | Batteries-included (admin, ORM, templates) outweighs FastAPI's async performance |
| 002 | HTMX over React | Server-rendered UI with zero JavaScript build tooling |
| 003 | Chart.js CDN over npm | No bundler, automatic CDN caching, zero build step |
| 004 | BigQuery read-only over local DB | Always-current data, zero sync pipelines, simplified deployment |
| 005 | Claude API over local LLM | Zero GPU required, best-in-class instruction following |

---

## Prerequisites

- Python 3.12+
- A GCP project with BigQuery dataset from [gcp-data-pipeline](https://github.com/koate-kpai/gcp-data-pipeline)
- *(Optional)* Claude API key for AI chat

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/koate-kpai/pipeline-dashboard.git
cd pipeline-dashboard

# 2. Create virtual environment
python -m venv .venv

# PowerShell: .venv\Scripts\Activate.ps1
# Bash: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Authenticate with GCP
gcloud auth application-default login

# 5. Copy and edit environment variables
cp .env.example .env
# Edit .env with your GCP project ID and (optional) Claude API key

# 6. Run migrations (for admin + bookmarked queries)
python manage.py migrate

# 7. Create a superuser (for admin access)
python manage.py createsuperuser

# 8. Start the dev server
python manage.py runserver
```

Open http://localhost:8000

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Yes* | dev fallback | Django secret key — set a strong value in production |
| `DJANGO_DEBUG` | No | `True` | Enable debug mode (`True`/`False`) |
| `DJANGO_ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `BIGQUERY_PROJECT_ID` | Yes | `gcp-data-pipeline-5XXXXX` | GCP project ID with pipeline analytics |
| `BIGQUERY_DATASET_STAGING` | No | `pipeline_staging` | BigQuery staging dataset |
| `BIGQUERY_DATASET_ANALYTICS` | No | `pipeline_analytics` | BigQuery analytics dataset |
| `CLAUDE_API_KEY` | No | — | Anthropic API key for AI chat |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Claude model to use |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string for production |

*Required in production; fallback provided for local dev.

---

## Docker

```bash
# Build
docker build --tag pipeline-dashboard .

# Run
docker run --rm -it \
    -p 8000:8000 \
    -e DJANGO_SECRET_KEY=your-secret-key \
    -e BIGQUERY_PROJECT_ID=your-project-id \
    -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
    -v /path/to/credentials.json:/app/credentials.json \
    pipeline-dashboard
```

---

## CI/CD

The project uses GitHub Actions (see `.github/workflows/ci.yml`):

- **Test job**: Django checks, migration validation, Docker build
- **Lint job**: Ruff linting and formatting checks

Credentials for BigQuery are not available in CI — the `check --deploy` command validates settings without requiring external connections.

---

## Tests

```bash
# Django system checks (no BigQuery required)
python manage.py check --deploy --fail-level WARNING

# Migration checks
python manage.py makemigrations --check --dry-run
```

Unit tests that require BigQuery connections are intentionally omitted — mocking BigQuery tests the mock, not the real integration. See ADR-004 for the rationale.

---

## Project Structure

```
pipeline-dashboard/
├── .github/workflows/     # CI configuration
├── chat/                  # AI chat app (Claude)
│   ├── services/
│   │   └── claude_client.py
│   ├── templates/chat/
│   ├── apps.py
│   ├── urls.py
│   └── views.py
├── config/                # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── dashboard/             # Main dashboard app
│   ├── services/
│   │   └── bigquery_client.py
│   ├── static/
│   ├── templates/dashboard/
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── docs/adr/              # Architecture Decision Records
│   ├── 001-django-over-fastapi.md
│   ├── 002-htmx-over-react.md
│   ├── 003-chartjs-cdn-over-npm.md
│   ├── 004-bigquery-over-local-db.md
│   └── 005-claude-api-over-local-llm.md
├── .dockerignore
├── .env.example
├── Dockerfile
├── manage.py
└── requirements.txt
```

---

## Related Projects

- [gcp-data-pipeline](https://github.com/koate-kpai/gcp-data-pipeline) — The GCP-native serverless ETL pipeline that feeds data into this dashboard
- [data-pipeline-engine](https://github.com/koate-kpai/data-pipeline-engine) — Production ETL pipeline with FastAPI and Streamlit

---

## License

MIT — see [LICENSE](LICENSE) for details.
