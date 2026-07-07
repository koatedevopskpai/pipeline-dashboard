"""
Django settings for pipeline-dashboard.

Architecture decision: Single settings module over split dev/prod files.

Why: For a portfolio project, a single settings module with environment-based
overrides is simpler and more transparent than splitting into base/dev/prod.
The settings are explicit and searchable. When this project needs production
deployment, we add env var overrides rather than duplicating the entire file.

Architecture decision: Environment variables for secrets, not settings.py.

Why: No API keys, database passwords, or secret keys should be hardcoded.
.env file for local dev, environment variables in production (Docker/Railway).
"""
from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
# Architecture decision: SECRET_KEY from env with a fallback for local dev only.
# Why: The fallback means you can clone and run without config, but production
# deployment requires setting DJANGO_SECRET_KEY. This avoids the "works on my
# machine" problem while still being secure by default in production.
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-do-not-use-in-production-abc123",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_htmx",   # HTMX integration: adds request.htmx boolean
    # Local
    "dashboard",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",   # Adds request.htmx for partial swaps
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Architecture decision: PostgreSQL by default with SQLite fallback.
# Why: PostgreSQL is the production standard for Django. The DATABASE_URL
# pattern (via dj_database_url) means Railway/Render/Heroku are one-line config
# changes. SQLite fallback means zero-config local development.
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.config(default=DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files (CSS, JavaScript)
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# BigQuery configuration (read-only client)
# ---------------------------------------------------------------------------
# Architecture decision: Application default credentials over service account JSON.
# Why: For a portfolio project, ADC is simpler — it picks up credentials from
# gcloud auth, environment variables, or the cloud provider automatically.
# For production deployment, set GOOGLE_APPLICATION_CREDENTIALS env var.
# ---------------------------------------------------------------------------

BIGQUERY_PROJECT_ID = os.environ.get("BIGQUERY_PROJECT_ID", "gcp-data-pipeline-5XXXXX")
BIGQUERY_DATASET_STAGING = os.environ.get("BIGQUERY_DATASET_STAGING", "pipeline_staging")
BIGQUERY_DATASET_ANALYTICS = os.environ.get("BIGQUERY_DATASET_ANALYTICS", "pipeline_analytics")

# ---------------------------------------------------------------------------
# Claude API configuration
# ---------------------------------------------------------------------------
# Architecture decision: Anthropic SDK over raw HTTP requests.
# Why: The SDK handles retries, rate limiting, streaming, and token counting
# automatically. Raw HTTP would require reimplementing all of this.
# The API key is required only on the chat page — the rest of the dashboard
# works without it.
# ---------------------------------------------------------------------------

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
