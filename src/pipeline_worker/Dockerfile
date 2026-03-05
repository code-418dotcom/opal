FROM python:3.11-slim

# System deps: libgomp (rembg/onnxruntime), libgl1+libglib (opencv/Real-ESRGAN)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
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
COPY src/pipeline_worker/requirements.txt /app/requirements.txt
COPY src/pipeline_worker/pipeline_worker /app/pipeline_worker

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Bake Real-ESRGAN model weights into image to eliminate cold-start download
RUN mkdir -p /app/models && \
    curl -L -o /app/models/RealESRGAN_x2plus.pth \
    https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth

# Pre-bake u2net ONNX model for rembg (176MB, avoids cold-start download)
RUN mkdir -p /root/.u2net && \
    curl -L -o /root/.u2net/u2net.onnx \
    https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx

CMD ["python", "-m", "pipeline_worker.worker"]
