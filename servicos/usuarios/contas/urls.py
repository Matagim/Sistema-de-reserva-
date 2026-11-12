from django.urls import re_path

from config.health import health

from . import views


urlpatterns = [
    re_path(r"^health/?$", health),
    re_path(r"^cadastro/?$", views.CadastroView.as_view()),
    re_path(r"^login/?$", views.LoginView.as_view()),
]
