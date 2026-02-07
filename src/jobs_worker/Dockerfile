FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime deps
COPY src/jobs_worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy shared package (the inner shared/ directory that has the actual Python package)
COPY src/shared/shared /app/shared

# Copy jobs_worker package (the inner jobs_worker/ directory that has the actual Python package)
COPY src/jobs_worker/jobs_worker /app/jobs_worker

# Ensure /app is on PYTHONPATH so "shared" can be imported
ENV PYTHONPATH=/app

# Run the worker
CMD ["python", "-m", "jobs_worker.worker"]