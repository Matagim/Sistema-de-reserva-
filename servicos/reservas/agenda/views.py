import logging
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from . import eventos
from .auth import EstaAutenticado
from .models import Reserva, Status
from .recursos_client import RecursoInexistente, RecursosIndisponivel, buscar_recurso
from .regras import RegraViolada, validar_periodo
from .relogio import agora
from .serializers import NovaReservaSerializer

log = logging.getLogger("reservas")

EXCLUSION_VIOLATION = "23P01"  # SQLSTATE da restrição de exclusão


def erro(status, codigo, detalhe, **extra):
    return Response({"erro": codigo, "detalhe": detalhe, **extra}, status=status)


def representar(reserva):
    return {
        "id": reserva.id,
        "recurso_id": reserva.recurso_id,
        "usuario_id": reserva.usuario_id,
        "inicio": reserva.inicio.isoformat(timespec="seconds"),
        "fim": reserva.fim.isoformat(timespec="seconds"),
        "status": reserva.status,
    }


def violou_sobreposicao(exc):
    return getattr(exc.__cause__, "sqlstate", None) == EXCLUSION_VIOLATION


class ReservasView(APIView):
    permission_classes = [EstaAutenticado]

    def get(self, request):
        """Minhas reservas (as mais recentes primeiro)."""
        reservas = Reserva.objects.filter(usuario_id=request.user.id).order_by("-inicio")[:200]
        return Response([representar(r) for r in reservas])

    def post(self, request):
        serializer = NovaReservaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        inicio, fim, recurso_id = dados["inicio"], dados["fim"], dados["recurso_id"]

        try:
            validar_periodo(inicio, fim, agora(), settings.REGRAS)
        except RegraViolada as exc:
            return erro(400, exc.codigo, str(exc))

        try:
            recurso = buscar_recurso(recurso_id)
        except RecursoInexistente:
            return erro(404, "recurso_inexistente", f"recurso {recurso_id} não existe")
        except RecursosIndisponivel as exc:
            log.warning("serviço recursos indisponível: %s", exc)
            return erro(503, "recursos_indisponivel", "não foi possível consultar o serviço de recursos")
        if not recurso.get("ativo", False):
            return erro(409, "recurso_inativo", f"o recurso {recurso_id} não pode ser reservado")

        try:
            with transaction.atomic():
                reserva = Reserva.objects.create(
                    recurso_id=recurso_id, usuario_id=request.user.id, inicio=inicio, fim=fim
                )
        except IntegrityError as exc:
            if violou_sobreposicao(exc):
                restricao = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
                return erro(
                    409,
                    "horario_ocupado",
                    "já existe uma reserva ativa que se sobrepõe a esse horário",
                    restricao=restricao,
                )
            raise

        dados_reserva = representar(reserva)
        eventos.publicar("reserva.criada", dados_reserva, request.user)
        return Response(dados_reserva, status=201)


class ReservaView(APIView):
    permission_classes = [EstaAutenticado]

    def delete(self, request, pk):
        """Cancelar: só o dono ou um admin, e só antes do início do horário."""
        reserva = Reserva.objects.filter(pk=pk).first()
        if reserva is None:
            return erro(404, "reserva_inexistente", f"reserva {pk} não existe")
        if reserva.usuario_id != request.user.id and request.user.papel != "admin":
            return erro(403, "sem_permissao", "só o dono da reserva ou um admin pode cancelá-la")
        if reserva.status == Status.CANCELADA:
            return Response(representar(reserva))  
        if reserva.inicio <= agora():
            return erro(403, "reserva_iniciada", "não é possível cancelar uma reserva que já começou")
        reserva.status = Status.CANCELADA
        reserva.save(update_fields=["status"])
        dados_reserva = representar(reserva)
        eventos.publicar("reserva.cancelada", dados_reserva, request.user)
        return Response(dados_reserva)


class DisponibilidadeView(APIView):
    """GET /api/reservas/disponibilidade?recurso_id=1&data=2026-11-03: intervalos ocupados do dia."""

    def get(self, request):
        try:
            recurso_id = int(request.query_params["recurso_id"])
            dia = date.fromisoformat(request.query_params["data"])
        except (KeyError, ValueError):
            return erro(400, "requisicao_invalida", "informe recurso_id (número) e data (AAAA-MM-DD)")
        comeco = datetime.combine(dia, time.min)
        ocupadas = Reserva.objects.filter(
            recurso_id=recurso_id, status=Status.ATIVA, inicio__lt=comeco + timedelta(days=1), fim__gt=comeco
        ).order_by("inicio")
        return Response(
            {
                "recurso_id": recurso_id,
                "data": dia.isoformat(),
                "hora_abertura": settings.REGRAS.hora_abertura,
                "hora_fechamento": settings.REGRAS.hora_fechamento,
                "ocupados": [
                    {
                        "reserva_id": r.id,
                        "inicio": r.inicio.isoformat(timespec="seconds"),
                        "fim": r.fim.isoformat(timespec="seconds"),
                    }
                    for r in ocupadas
                ],
            }
        )


class RegrasView(APIView):
    """GET /api/reservas/regras: as regras em vigor (para o front-end validar antes de enviar)."""

    def get(self, request):
        return Response(settings.REGRAS.como_dict())
