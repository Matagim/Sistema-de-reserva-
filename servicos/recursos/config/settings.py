import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SERVICO = "recursos"


def env(nome, padrao=None):
    return os.environ.get(nome, padrao)


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-inseguro-trocar-fora-do-laboratorio")
DEBUG = env("DEBUG") == "1"
ALLOWED_HOSTS = ["*"]  

INSTALLED_APPS = [
    "rest_framework",
    "catalogo",
]

MIDDLEWARE = [
    "config.middleware.TaskIdMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DB_SCHEMA = env("DB_SCHEMA", "recursos")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "faculdade"),
        "USER": env("DB_USER", "app_recursos"),
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
TIME_ZONE = "UTC"
USE_TZ = True

# Autenticação: o token é emitido por `usuarios`; aqui ele só é VALIDADO (mesmo segredo).
JWT_SEGREDO = env("JWT_SEGREDO", "dev-segredo-trocar")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["catalogo.auth.JWTAuthentication"],
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
