FROM python:3.11-slim

# rembg/onnxruntime needs libgomp
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
EXPOSE 8080

COPY src/shared/shared /app/shared
COPY src/bg_removal_worker/requirements.txt /app/requirements.txt
COPY src/bg_removal_worker/bg_removal_worker /app/bg_removal_worker

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "-m", "bg_removal_worker.worker"]
