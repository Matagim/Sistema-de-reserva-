import os
import socket


class TaskIdMiddleware:
    

    def __init__(self, get_response):
        self.get_response = get_response
        self.task_id = socket.gethostname()
        self.versao = os.environ.get("APP_VERSAO", "dev")

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Task-Id"] = self.task_id
        response["X-Versao"] = self.versao
        return response
