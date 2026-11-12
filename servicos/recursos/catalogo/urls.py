from django.urls import re_path

from config.health import health

from . import views


urlpatterns = [
    re_path(r"^health/?$", health),
    re_path(r"^$", views.RecursosView.as_view()),
    re_path(r"^(?P<pk>\d+)/?$", views.RecursoView.as_view()),
]
