FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Your actual shared package is src/shared/shared/*
# Copy it into /app/shared so `import shared.db` works.
COPY src/shared/shared /app/shared

COPY src/web_api/requirements.txt /app/requirements.txt
COPY src/web_api/web_api /app/web_api

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8080
CMD ["uvicorn", "web_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
