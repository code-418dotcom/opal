FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY ../shared /app/shared
COPY ./pyproject.toml /app/pyproject.toml
COPY ./orchestrator /app/orchestrator

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir /app/shared \
 && pip install --no-cache-dir /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "orchestrator.worker"]
