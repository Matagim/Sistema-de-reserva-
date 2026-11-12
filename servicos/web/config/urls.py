from django.urls import path, re_path

from config.health import health
from painel.views import index

urlpatterns = [
    re_path(r"^health/?$", health),
    path("", index),
]
