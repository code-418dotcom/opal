FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
EXPOSE 8080

COPY src/shared/shared /app/shared
COPY src/scene_worker/requirements.txt /app/requirements.txt
COPY src/scene_worker/scene_worker /app/scene_worker

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "-m", "scene_worker.worker"]
