FROM python:3.11-slim

WORKDIR /app

# System deps (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Copy shared + worker
COPY src/shared /app/src/shared
COPY src/jobs_worker /app/src/jobs_worker

# Install deps
RUN pip install --no-cache-dir -r /app/src/jobs_worker/requirements.txt \
 && pip install --no-cache-dir -e /app/src/shared

# Run
CMD ["python", "-m", "jobs_worker.worker"]
