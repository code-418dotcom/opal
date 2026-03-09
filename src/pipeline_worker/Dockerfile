FROM python:3.11-slim

# System deps: libgomp (onnxruntime), libgl1+libglib (opencv/Real-ESRGAN), git (HF downloads)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    curl \
    git \
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

# Pre-bake BiRefNet_lite model weights (avoids cold-start download from HuggingFace)
RUN python -c "from transformers import AutoModelForImageSegmentation; \
    AutoModelForImageSegmentation.from_pretrained('ZhengPeng7/BiRefNet_lite', trust_remote_code=True)"

CMD ["python", "-m", "pipeline_worker.worker"]
