from django.urls import re_path

from config.health import health

from . import views

# O prefixo /api/reservas/ já foi consumido em config/urls.py.
urlpatterns = [
    re_path(r"^health/?$", health),
    re_path(r"^regras/?$", views.RegrasView.as_view()),
    re_path(r"^disponibilidade/?$", views.DisponibilidadeView.as_view()),
    re_path(r"^$", views.ReservasView.as_view()),
    re_path(r"^(?P<pk>\d+)/?$", views.ReservaView.as_view()),
]
