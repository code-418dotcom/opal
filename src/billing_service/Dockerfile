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

COPY src/billing_service/requirements.txt /app/requirements.txt
COPY src/billing_service/billing_service /app/billing_service

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8080
CMD ["uvicorn", "billing_service.main:app", "--host", "0.0.0.0", "--port", "8080"]
