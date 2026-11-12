from django.urls import include, re_path


urlpatterns = [
    re_path(r"^api/reservas(?:/|$)", include("agenda.urls")),
]
