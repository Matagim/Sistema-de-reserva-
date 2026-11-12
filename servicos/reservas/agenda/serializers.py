from datetime import datetime

from rest_framework import serializers


def _horario_local(valor):
    try:
        dt = datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        raise serializers.ValidationError("use o formato 2026-11-03T14:00")
    if dt.tzinfo is not None:
        raise serializers.ValidationError("informe o horário local da faculdade, sem fuso (ex.: 2026-11-03T14:00)")
    return dt


class NovaReservaSerializer(serializers.Serializer):
    recurso_id = serializers.IntegerField(min_value=1)
    inicio = serializers.CharField()
    fim = serializers.CharField()

    def validate_inicio(self, valor):
        return _horario_local(valor)

    def validate_fim(self, valor):
        return _horario_local(valor)
