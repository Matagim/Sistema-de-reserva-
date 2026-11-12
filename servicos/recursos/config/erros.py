from django.db.utils import InterfaceError, OperationalError
from rest_framework.response import Response
from rest_framework.views import exception_handler

CODIGOS = {
    400: "requisicao_invalida",
    401: "nao_autenticado",
    403: "sem_permissao",
    404: "nao_encontrado",
    405: "metodo_nao_permitido",
    415: "tipo_nao_suportado",
}


def tratar(exc, contexto):
    """Formato único de erro: {"erro": <código>, "detalhe": ...}."""
    if isinstance(exc, (OperationalError, InterfaceError)):
        return Response(
            {"erro": "banco_indisponivel", "detalhe": "não foi possível falar com o banco de dados"},
            status=503,
        )
    resposta = exception_handler(exc, contexto)
    if resposta is None:
        return None
    resposta.data = {
        "erro": CODIGOS.get(resposta.status_code, "erro"),
        "detalhe": resposta.data.get("detail", resposta.data) if isinstance(resposta.data, dict) else resposta.data,
    }
    return resposta
