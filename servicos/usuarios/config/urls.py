from django.urls import include, re_path


urlpatterns = [
    re_path(r"^api/usuarios(?:/|$)", include("contas.urls")),
]
