FROM python:3.11-slim

WORKDIR /var/azureml-app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY score.py .

ENV AZUREML_MODEL_DIR=/var/azureml-app
EXPOSE 5001

CMD ["python", "-m", "gunicorn", "-b", "0.0.0.0:5001", "score:app"]
