FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG VERSAO=dev
ENV APP_VERSAO=${VERSAO}

RUN useradd --system --no-create-home app && chown -R app /app
USER app


CMD ["python", "-u", "worker.py"]
