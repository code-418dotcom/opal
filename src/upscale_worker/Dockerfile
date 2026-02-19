FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
EXPOSE 8080

COPY src/shared/shared /app/shared
COPY src/upscale_worker/requirements.txt /app/requirements.txt
COPY src/upscale_worker/upscale_worker /app/upscale_worker

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Bake Real-ESRGAN model weights into image to eliminate cold-start download
RUN mkdir -p /app/models && \
    curl -L -o /app/models/RealESRGAN_x2plus.pth \
    https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth

CMD ["python", "-m", "upscale_worker.worker"]
