FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the actual shared Python package to /app/shared
COPY src/shared/shared /app/shared

COPY src/export_worker/requirements.txt /app/requirements.txt
COPY src/export_worker/export_worker /app/export_worker

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "-m", "export_worker.worker"]
