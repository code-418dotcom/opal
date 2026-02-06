FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime deps
COPY src/jobs_worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy code (including shared package)
COPY src/shared /app/shared
COPY src/jobs_worker /app/jobs_worker

# Ensure /app is on PYTHONPATH so "shared" can be imported
ENV PYTHONPATH=/app

CMD ["python", "-m", "jobs_worker.worker"]
