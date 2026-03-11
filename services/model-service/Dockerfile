ARG MODEL_SERVICE_BASE_IMAGE=python:3.12-slim
FROM ${MODEL_SERVICE_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/*

COPY services/model-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/model-service/app ./app
COPY configs/model-service ./configs

EXPOSE 8011

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011", "--no-access-log"]
