FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Build context is repo root, so copy using src/... paths
COPY src/shared /app/shared
COPY src/web_api/pyproject.toml /app/pyproject.toml
COPY src/web_api/web_api /app/web_api

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir "fastapi==0.115.0" "uvicorn[standard]==0.30.6" "pydantic==2.9.2" "psycopg[binary]==3.2.2" "azure-storage-blob==12.22.0" "azure-servicebus==7.12.2" "httpx==0.27.2" "python-multipart==0.0.12"

EXPOSE 8080

CMD ["uvicorn", "web_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
