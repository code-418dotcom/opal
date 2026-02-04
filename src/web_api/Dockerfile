FROM python:3.11-slim

WORKDIR /app

# system deps (psycopg binary ok; keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY ../shared /app/shared
COPY ./pyproject.toml /app/pyproject.toml
COPY ./web_api /app/web_api

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir /app/shared \
 && pip install --no-cache-dir /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["uvicorn", "web_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
