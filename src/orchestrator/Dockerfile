FROM python:3.11-slim

# Install system dependencies for OpenCV and Real-ESRGAN
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the actual shared Python package to /app/shared
COPY src/shared/shared /app/shared

COPY src/orchestrator/requirements.txt /app/requirements.txt
COPY src/orchestrator/orchestrator /app/orchestrator

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# FIXED: Run orchestrator.worker instead of orchestrator.main
CMD ["python", "-m", "orchestrator.worker"]
