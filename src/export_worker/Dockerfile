FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# shared package (shared.db etc.)
COPY src/shared/shared /app/shared

COPY src/export_worker/requirements.txt /app/requirements.txt
COPY src/export_worker/export_worker /app/export_worker

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# You have export_worker/worker.py, not export_worker/main.py
CMD ["python", "-m", "export_worker.worker"]
