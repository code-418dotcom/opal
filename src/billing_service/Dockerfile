FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Build context is repo root
COPY src/shared /app/shared
COPY src/billing_service /app/billing_service

# Baseline deps for FastAPI billing service + Mollie webhook handling
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir \
      "fastapi==0.115.0" \
      "uvicorn[standard]==0.30.6" \
      "pydantic==2.9.2" \
      "httpx==0.27.2"

EXPOSE 8080

# Common entrypoint; adjust if your module name differs (next error will tell us)
CMD ["uvicorn", "billing_service.main:app", "--host", "0.0.0.0", "--port", "8080"]
