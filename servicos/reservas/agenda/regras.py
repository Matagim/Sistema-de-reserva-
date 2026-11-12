"""Regras de negócio da reserva. Python puro: testável sem Django e sem banco."""

import os
from dataclasses import dataclass
from datetime import datetime


class RegraViolada(Exception):
    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo


@dataclass(frozen=True)
class Regras:
    duracao_max_horas: int = 4
    hora_abertura: int = 7
    hora_fechamento: int = 22
    dias_antecedencia_max: int = 14

    @classmethod
    def do_ambiente(cls, env=os.environ):
        return cls(
            duracao_max_horas=int(env.get("DURACAO_MAX_HORAS", 4)),
            hora_abertura=int(env.get("HORA_ABERTURA", 7)),
            hora_fechamento=int(env.get("HORA_FECHAMENTO", 22)),
            dias_antecedencia_max=int(env.get("DIAS_ANTECEDENCIA_MAX", 14)),
        )

    def como_dict(self):
        return {
            "duracao_max_horas": self.duracao_max_horas,
            "hora_abertura": self.hora_abertura,
            "hora_fechamento": self.hora_fechamento,
            "dias_antecedencia_max": self.dias_antecedencia_max,
        }


def _hora_cheia(dt: datetime) -> bool:
    return dt.minute == 0 and dt.second == 0 and dt.microsecond == 0


def validar_periodo(inicio: datetime, fim: datetime, agora: datetime, regras: Regras) -> None:
    """Levanta RegraViolada (resposta 400) na primeira regra quebrada. Horários sem fuso."""
    if fim <= inicio:
        raise RegraViolada("periodo_invalido", "o fim deve ser depois do início")
    if not (_hora_cheia(inicio) and _hora_cheia(fim)):
        raise RegraViolada("periodo_invalido", "início e fim devem ser horas cheias (ex.: 14:00)")
    if inicio.date() != fim.date():
        raise RegraViolada("fora_da_janela", "a reserva deve começar e terminar no mesmo dia")

    horas = int((fim - inicio).total_seconds() // 3600)
    if horas > regras.duracao_max_horas:
        raise RegraViolada(
            "duracao_invalida", f"a duração máxima é de {regras.duracao_max_horas} hora(s); pedido: {horas}"
        )
    if inicio.hour < regras.hora_abertura or fim.hour > regras.hora_fechamento:
        raise RegraViolada(
            "fora_da_janela",
            f"reservas só entre {regras.hora_abertura:02d}h e {regras.hora_fechamento:02d}h",
        )
    if inicio < agora:
        raise RegraViolada("no_passado", "não é possível reservar um horário que já começou")
    if (inicio.date() - agora.date()).days > regras.dias_antecedencia_max:
        raise RegraViolada(
            "antecedencia_excedida", f"só é possível reservar com até {regras.dias_antecedencia_max} dias de antecedência"
        )
