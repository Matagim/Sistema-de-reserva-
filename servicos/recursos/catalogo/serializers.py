from rest_framework import serializers

from .models import Recurso


class RecursoSerializer(serializers.ModelSerializer):
    capacidade = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recurso
        fields = ["id", "nome", "tipo", "capacidade", "local", "ativo"]
        read_only_fields = ["id"]
