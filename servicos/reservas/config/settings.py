import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SERVICO = "reservas"


def env(nome, padrao=None):
    return os.environ.get(nome, padrao)


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-inseguro-trocar-fora-do-laboratorio")
DEBUG = env("DEBUG") == "1"
ALLOWED_HOSTS = ["*"]  

INSTALLED_APPS = [
    "rest_framework",
    "django.contrib.postgres",
    "agenda",
]

MIDDLEWARE = [
    "config.middleware.TaskIdMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"


DB_SCHEMA = env("DB_SCHEMA", "reservas")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "faculdade"),
        "USER": env("DB_USER", "app_reservas"),
        "PASSWORD": env("DB_SENHA", ""),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "options": f"-c search_path={DB_SCHEMA}",
            
            "sslmode": env("DB_SSLMODE", "prefer"),
            "connect_timeout": 5,
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "pt-br"
FACULDADE_TZ = env("FACULDADE_TZ", "America/Fortaleza")
TIME_ZONE = FACULDADE_TZ

USE_TZ = False


JWT_SEGREDO = env("JWT_SEGREDO", "dev-segredo-trocar")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["agenda.auth.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "config.erros.tratar",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}

# Regras de negócio: variáveis de ambiente da task definition. 
from agenda.regras import Regras  # nota: E402

REGRAS = Regras.do_ambiente(os.environ)

# `reservas` consulta `recursos` por HTTP (na AWS, pela URL do ALB).
RECURSOS_URL = env("RECURSOS_URL", "http://localhost:3002").rstrip("/")

# Fila de eventos. Vazia (desenvolvimento local): o evento é registrado em log e não enviado.
SQS_URL = env("SQS_URL", "")
AWS_REGION = env("AWS_REGION", env("AWS_DEFAULT_REGION", "us-east-1"))
