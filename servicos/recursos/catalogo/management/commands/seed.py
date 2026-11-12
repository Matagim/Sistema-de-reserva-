from django.core.management.base import BaseCommand

from catalogo.models import Recurso, Tipo

DEMO = [
    ("Sala 101", Tipo.SALA, 40, "Bloco A, 1º andar"),
    ("Sala 102", Tipo.SALA, 40, "Bloco A, 1º andar"),
    ("Auditório Central", Tipo.SALA, 120, "Bloco B, térreo"),
    ("Laboratório de Informática 1", Tipo.LABORATORIO, 30, "Bloco C, 2º andar"),
    ("Laboratório de Redes", Tipo.LABORATORIO, 25, "Bloco C, 2º andar"),
    ("Projetor portátil", Tipo.EQUIPAMENTO, 1, "Almoxarifado"),
]


class Command(BaseCommand):
    help = "Cria recursos de demonstração (idempotente, por nome)."

    def handle(self, *args, **opcoes):
        for nome, tipo, capacidade, local in DEMO:
            _, criado = Recurso.objects.get_or_create(
                nome=nome, defaults={"tipo": tipo, "capacidade": capacidade, "local": local}
            )
            self.stdout.write(f"{'criado' if criado else 'existe'}: {nome}")
