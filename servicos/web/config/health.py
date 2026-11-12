import os
import socket

from django.conf import settings
from django.http import JsonResponse


def health(request):
    
    if os.environ.get("QUEBRAR_HEALTH") == "1":
        return JsonResponse({"status": "quebrado", "servico": settings.SERVICO}, status=500)
    return JsonResponse(
        {
            "status": "ok",
            "servico": settings.SERVICO,
            "versao": os.environ.get("APP_VERSAO", "dev"),
            "task": socket.gethostname(),
        }
    )
