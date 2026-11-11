# syntax=docker/dockerfile:1
# EXPERTOS WORLD OS — Production Container Image
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8099 \
    EXPERTOS_DB=/data/expertos.db

WORKDIR /app

# Install system curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Create non-root unprivileged service user
RUN groupadd -g 10001 expertos && \
    useradd -u 10001 -g expertos -s /bin/bash -m expertos && \
    mkdir -p /data && chown -R expertos:expertos /data /app

# Copy application source code
COPY app/ /app/app/
COPY web/ /app/web/
COPY docs/ /app/docs/
COPY pytest.ini /app/
RUN chown -R expertos:expertos /app

USER expertos

EXPOSE 8099

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8099/api/status || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099", "--workers", "1"]

