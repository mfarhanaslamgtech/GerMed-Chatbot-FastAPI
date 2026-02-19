# ── Stage 1: Builder ──────────────────────────────────────────────
# We use a build stage to compile dependencies without bloat.
FROM python:3.12-slim as builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies to a virtual env or user directory
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --target=/app/dependencies -r requirements.txt && \
    pip install --no-cache-dir --target=/app/dependencies gunicorn uvicorn

# ── Stage 2: Final Image ──────────────────────────────────────────
# This is the actual image that will run in production.
FROM python:3.12-slim

# Security: Create a non-root user
# 1000 is the standard UID/GID for non-root users.
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/dependencies:/app \
    PATH="/app/dependencies/bin:$PATH"

WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /app/dependencies /app/dependencies

# Install minimal runtime system deps (if needed, e.g., for specialized image libs)
# RUN apt-get update && apt-get install -y --no-install-recommends ...

# Copy application code
# Ensure the non-root user owns the files
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser .env .
COPY --chown=appuser:appuser gunicorn_conf.py .

# Switch to non-root user for security
USER appuser

# Expose port (documentary only, docker-compose maps it)
EXPOSE 8000

# Run with Gunicorn for production concurrency
# We use the config file for settings.
CMD ["gunicorn", "-c", "gunicorn_conf.py", "src.app.app:create_app"]
