FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/aml_sd_stub/requirements.txt /app/requirements.txt
COPY src/aml_sd_stub/score.py /app/score.py

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8080
CMD ["python", "/app/score.py"]
