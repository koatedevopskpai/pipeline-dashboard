# ADR 001: Django over FastAPI for Full-Stack Dashboard

## Status

Accepted (2026-07-07)

## Context

The pipeline dashboard needs to serve server-rendered HTML pages with data visualisations, an admin interface for data management, and an AI chat widget. The two main Python web frameworks are Django and FastAPI.

Django is a batteries-included framework with built-in ORM, admin, template engine, authentication, and form handling. FastAPI is an async-first framework designed for high-performance APIs.

The dashboard must:
- Render HTML templates with chart data injected at page load
- Provide an admin interface for non-technical users to manage pipeline configurations
- Connect to BigQuery for read-only analytics queries
- Support HTMX for interactive UI without a JavaScript framework
- Be deployable as a single Docker container

## Decision

Use Django with the following components:
- Django's built-in template engine for server-rendered HTML
- Django Admin for pipeline configuration management
- django-environ for environment variable management
- python-dotenv for `.env` file loading in development
- google-cloud-bigquery for analytics queries
- HTMX for interactive UI (form submissions, partial page updates)

## Consequences

### Positive
- Zero additional framework dependencies — Django's built-in admin and ORM eliminate the need for a separate admin tool
- Mature ecosystem with extensive documentation for deployment, security, and testing
- Single process serves both HTML and API endpoints — simplifies Docker deployment
- Django's template engine integrates naturally with HTMX for server-rendered partials

### Negative
- Django is heavier than necessary for pure API use cases — any future API-only endpoints will carry Django's overhead
- Async support in Django is still maturing — BigQuery queries block the event loop in the default WSGI mode
- Django's ORM is unused beyond the chat model — the primary data source is BigQuery, not a relational database

### Mitigations
- BigQuery queries are wrapped in `sync_to_async` or run in thread pool executors to avoid blocking the request-response cycle
- The chat model uses Django's ORM only for storing chat history — can be switched to a different backend without architectural change
- If API-only endpoints are needed later, a Django Ninja or Django REST Framework app can be added without changing the core architecture

## Alternatives Considered

### FastAPI + SQLAlchemy + Jinja2
- **Pros**: Async-native, better BigQuery performance, lighter deployment
- **Cons**: No admin interface, must build entire CMS from scratch, fewer "batteries included"
- **Rejected because**: The admin interface requirement alone justifies Django's weight. Building a comparable admin in FastAPI would take more time than the entire dashboard build.

### Next.js + API Route
- **Pros**: Modern full-stack JavaScript, excellent developer experience
- **Cons**: Requires Node.js runtime, doubles deployment complexity, team primarily Python-skilled
- **Rejected because**: Adding a second language and runtime contradicts the "Python-first portfolio" positioning
