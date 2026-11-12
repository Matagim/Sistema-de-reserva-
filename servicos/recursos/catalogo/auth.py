"""Validação local do token JWT emitido por `usuarios`.

"""

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions, permissions


class Principal:

    is_authenticated = True

    def __init__(self, claims):
        self.id = int(claims["sub"])
        self.nome = claims.get("nome", "")
        self.email = claims.get("email", "")
        self.papel = claims.get("papel", "aluno")


class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        cabecalho = request.headers.get("Authorization", "")
        if not cabecalho:
            return None  # anônimo; as views que exigem login usam EstaAutenticado
        partes = cabecalho.split()
        if len(partes) != 2 or partes[0].lower() != "bearer":
            raise exceptions.AuthenticationFailed("Use o cabeçalho 'Authorization: Bearer <token>'.")
        try:
            claims = jwt.decode(partes[1], settings.JWT_SEGREDO, algorithms=["HS256"])
            return Principal(claims), partes[1]
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token expirado.")
        except (jwt.InvalidTokenError, KeyError, ValueError):
            raise exceptions.AuthenticationFailed("Token inválido.")

    def authenticate_header(self, request):
        return 'Bearer realm="faculdade"'  # faz o DRF responder 401 sem login


class EstaAutenticado(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user is not None and request.user.is_authenticated


class EhAdmin(permissions.BasePermission):
    message = "Apenas administradores podem fazer isso."

    def has_permission(self, request, view):
        return request.user is not None and request.user.is_authenticated and request.user.papel == "admin"
