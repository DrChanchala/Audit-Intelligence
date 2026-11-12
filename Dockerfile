# =================================================================
# SiteIQ — Production Multi-Stage Container Image
# Optimized for Railway, FastAPI, Static Serving, and Supabase Postgres
# =================================================================

FROM python:3.12-slim as runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install minimal OS dependencies for network operations & PostgreSQL client libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app_audit.py /app/
COPY database_audit.py /app/
COPY allocation_service.py /app/
COPY inspection_report_service.py /app/
COPY ai_agent.py /app/
COPY progress_engine.py /app/
COPY database.py /app/
COPY master_checklist_parsed.json /app/
COPY migrate_sqlite_to_postgres.py /app/
COPY migrations /app/migrations
COPY static /app/static

# Create uploads evidence directory
RUN mkdir -p /app/static/uploads/evidence

# Expose default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Start FastAPI server on dynamic Railway PORT
CMD ["sh", "-c", "uvicorn app_audit:app --host 0.0.0.0 --port ${PORT:-8000}"]
