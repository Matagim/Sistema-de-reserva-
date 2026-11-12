from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from . import tokens
from .models import Papel, Usuario
from .serializers import CadastroSerializer, LoginSerializer


def representar(usuario):
    return {"id": usuario.id, "nome": usuario.nome, "email": usuario.email, "papel": usuario.papel}


class CadastroView(APIView):
    """POST /api/usuarios/cadastro: todo cadastro novo é aluno; admin e professor vêm do seed."""

    def post(self, request):
        serializer = CadastroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        try:
            with transaction.atomic():
                usuario = Usuario.objects.create(
                    nome=dados["nome"],
                    email=dados["email"],
                    senha_hash=make_password(dados["senha"]),
                    papel=Papel.ALUNO,
                )
        except IntegrityError:
            return Response(
                {"erro": "email_ja_cadastrado", "detalhe": "já existe um usuário com esse e-mail"},
                status=409,
            )
        return Response(representar(usuario), status=201)


class LoginView(APIView):
    """POST /api/usuarios/login: devolve o token JWT e os dados do usuário."""

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        usuario = Usuario.objects.filter(email=dados["email"]).first()
        if usuario is None or not check_password(dados["senha"], usuario.senha_hash):
            return Response(
                {"erro": "credenciais_invalidas", "detalhe": "e-mail ou senha incorretos"},
                status=401,
            )
        return Response({"token": tokens.emitir(usuario), "usuario": representar(usuario)})
