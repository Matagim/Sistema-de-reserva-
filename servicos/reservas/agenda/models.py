from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields.ranges import RangeBoundary, RangeOperators
from django.db import models
from django.db.models import Q

from .fields import TimestampLocal, TsRange
from .relogio import agora


class Status(models.TextChoices):
    ATIVA = "ativa", "Ativa"
    CANCELADA = "cancelada", "Cancelada"


class Reserva(models.Model):
    """Tabela reservas.reservas (esquema `reservas`, definido pelo search_path do serviço).

    recurso_id e usuario_id pertencem a outros serviços: não há chave estrangeira.
    `reservas` valida o recurso por HTTP e o usuário pelo token.
    """

    recurso_id = models.BigIntegerField()
    usuario_id = models.BigIntegerField()
    inicio = TimestampLocal()
    fim = TimestampLocal()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ATIVA)
    criada_em = TimestampLocal(default=agora)

    class Meta:
        db_table = "reservas"
        constraints = [
            models.CheckConstraint(condition=Q(fim__gt=models.F("inicio")), name="reservas_fim_depois_inicio"),
            models.CheckConstraint(condition=Q(status__in=Status.values), name="reservas_status_valido"),
            # A dupla marcação é impedida pelo banco: duas reservas ATIVAS do mesmo recurso
            # não podem ter intervalos que se sobrepõem. 
            ExclusionConstraint(
                name="reservas_sem_sobreposicao",
                expressions=[
                    ("recurso_id", RangeOperators.EQUAL),
                    (TsRange("inicio", "fim", RangeBoundary()), RangeOperators.OVERLAPS),
                ],
                condition=Q(status="ativa"),
            ),
        ]
        indexes = [models.Index(fields=["usuario_id", "inicio"], name="reservas_usuario_inicio_idx")]

    def __str__(self):
        return f"reserva {self.pk}: recurso {self.recurso_id} {self.inicio:%Y-%m-%d %H:%M}"
