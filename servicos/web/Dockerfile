FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    WEB_CONCURRENCY=2

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput


ARG VERSAO=dev
ARG QUEBRAR_HEALTH=0
ENV APP_VERSAO=${VERSAO} \
    QUEBRAR_HEALTH=${QUEBRAR_HEALTH}

RUN useradd --system --no-create-home app && chown -R app /app
USER app

EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --access-logfile -"]
