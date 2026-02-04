FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Build context is repo root
COPY src/shared /app/shared
COPY src/orchestrator /app/orchestrator

# Install baseline deps (keeps CI deterministic even if requirements.txt doesn't exist yet)
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir \
      "pydantic==2.9.2" \
      "psycopg[binary]==3.2.2" \
      "azure-storage-blob==12.22.0" \
      "azure-servicebus==7.12.2" \
      "httpx==0.27.2"

# Try common entrypoints; if yours differs, the next error will tell us exactly what to run.
CMD ["python", "-m", "orchestrator.main"]
