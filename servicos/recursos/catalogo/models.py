from django.db import models


class Tipo(models.TextChoices):
    SALA = "sala", "Sala"
    LABORATORIO = "laboratorio", "Laboratório"
    EQUIPAMENTO = "equipamento", "Equipamento"


class Recurso(models.Model):
    """Tabela recursos.recursos (esquema `recursos`, definido pelo search_path do serviço)."""

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    capacidade = models.PositiveIntegerField()
    local = models.CharField(max_length=120, blank=True, default="")
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "recursos"
        constraints = [
            models.CheckConstraint(condition=models.Q(capacidade__gt=0), name="recursos_capacidade_positiva"),
            models.CheckConstraint(condition=models.Q(tipo__in=Tipo.values), name="recursos_tipo_valido"),
        ]

    def __str__(self):
        return self.nome
