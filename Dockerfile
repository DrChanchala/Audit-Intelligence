# =================================================================
# SiteIQ — Production Multi-Stage Container Image
# Optimized for Railway, FastAPI, and Postgres
# =================================================================

FROM python:3.12-slim as runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    UPLOAD_DIR=/data/uploads

WORKDIR /app

# Install minimal OS dependencies for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application directories only
COPY app /app/app
COPY templates /app/templates
COPY static /app/static
COPY scripts /app/scripts
COPY migrations /app/migrations
COPY archive /app/archive

# Non-root user and persistent volume mount point
RUN useradd -m -u 1000 appuser && \
    mkdir -p /data/uploads && \
    chown -R appuser:appuser /app /data/uploads

USER appuser

# Expose default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Start FastAPI server on dynamic Railway PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
