# ==============================================================================
# TraceNest Backend Multi-Stage Dockerfile (Production Hardened)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Dependencies
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest
COPY requirements.txt .

# Install dependencies into wheel cache
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Minimal Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Runtime labels
LABEL org.opencontainers.image.title="TraceNest Backend" \
      org.opencontainers.image.description="TraceNest Application Failure Investigation Platform API" \
      org.opencontainers.image.version="0.1.0"

# Install minimal runtime system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root unprivileged service user and group
RUN groupadd -g 10001 tracenest && \
    useradd -u 10001 -g tracenest -s /bin/false -M -d /app tracenest

WORKDIR /app

# Copy application source code
COPY --chown=tracenest:tracenest app /app/app
COPY --chown=tracenest:tracenest migrations /app/migrations
COPY --chown=tracenest:tracenest alembic.ini /app/alembic.ini
COPY --chown=tracenest:tracenest pyproject.toml /app/pyproject.toml

# Switch to non-root user
USER 10001:10001

# Production Environment Variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    ENVIRONMENT=production \
    DEBUG=false

EXPOSE 8000

# Health check without external tools (using Python's standard library)
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# Launch production server with multi-worker ASGI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
