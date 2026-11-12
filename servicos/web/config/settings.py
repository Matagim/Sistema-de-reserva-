import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SERVICO = "web"


def env(nome, padrao=None):
    return os.environ.get(nome, padrao)


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-inseguro-trocar-fora-do-laboratorio")
DEBUG = env("DEBUG") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "painel",
]

MIDDLEWARE = [
    "config.middleware.TaskIdMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]


DATABASES = {}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
