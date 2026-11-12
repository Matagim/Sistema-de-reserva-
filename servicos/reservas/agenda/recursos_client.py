"""Chamada síncrona reservas -> recursos (na AWS, pela URL do ALB)."""

import json
import urllib.error
import urllib.request

from django.conf import settings


class RecursoInexistente(Exception):
    pass


class RecursosIndisponivel(Exception):
    pass


def buscar_recurso(recurso_id):
    url = f"{settings.RECURSOS_URL}/api/recursos/{recurso_id}"
    requisicao = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(requisicao, timeout=3) as resposta:
            return json.loads(resposta.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RecursoInexistente(recurso_id) from exc
        raise RecursosIndisponivel(f"recursos respondeu {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RecursosIndisponivel(str(exc)) from exc
