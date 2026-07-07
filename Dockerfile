# Architecture decision: Multi-stage Docker build.
# Why: Stage 1 installs dependencies and builds assets. Stage 2 copies only
# what is needed at runtime. The final image is ~150MB vs ~1GB for a full
# Python build image. Smaller images mean faster deploys and lower cold starts.
#
# Architecture decision: python:3.12-slim over alpine or full image.
# Why: slim is 50MB smaller than full but keeps glibc and common system deps
# that many Python wheels need (grpcio for BigQuery, cffi for cryptography).
# Alpine uses musl libc which can cause subtle issues with binary wheels.
# Full image adds build tools that are only needed during `pip install`.

# === Stage 1: Build ===
FROM python:3.12-slim AS builder

# Prevent Python from buffering logs and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system build dependencies (required by grpcio, cffi, etc.)
# Then clean up to keep the build stage lean
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first — Docker layer caching means this layer
# is reused unless requirements.txt changes, saving minutes per rebuild
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# === Stage 2: Runtime ===
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings

# Create a non-root user for security
RUN groupadd -r django && useradd -r -g django django

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/django/.local
ENV PATH=/home/django/.local/bin:$PATH

# Copy application code (after deps to optimise caching)
COPY . .

# Collect static files
RUN mkdir -p staticfiles && \
    python manage.py collectstatic --noinput --clear

# Create media directory and set permissions
RUN mkdir -p /app/media && \
    chown -R django:django /app

USER django

# Architecture decision: Gunicorn over Daphne or Uvicorn.
# Why: This is a WSGI application (Django with sync BigQuery views).
# Uvicorn is for ASGI. Daphne is the Django-channels server but adds
# complexity. Gunicorn is the standard Django production server with
# the best documentation and operational tooling.
#
# Architecture decision: Single worker over multiple workers.
# Why: BigQuery queries are I/O-bound, not CPU-bound. Multiple workers
# would each create their own BigQuery client and compete for the same
# I/O resources. A single worker with async query execution (via
# concurrent.futures) handles concurrent requests more efficiently.

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]

EXPOSE 8000
