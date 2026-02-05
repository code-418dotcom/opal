FROM python:3.11-slim

WORKDIR /app

# System deps (build-essential helps for some wheels; keep it lean but safe for now)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# IMPORTANT:
# Build context is repo root in GitHub Actions (we build with: -f src/web_api/Dockerfile .)
# So COPY paths must be relative to repo root.

# Shared code
COPY src/shared /app/shared

# Python project definition for this service
COPY src/web_api/pyproject.toml /app/pyproject.toml

# Service code
COPY src/web_api/web_api /app/web_api

# Install deps + package
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir .

EXPOSE 8080

CMD ["uvicorn", "web_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
