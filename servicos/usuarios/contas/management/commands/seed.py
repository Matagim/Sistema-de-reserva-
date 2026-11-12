import os

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from contas.models import Papel, Usuario

DEMO = [
    ("Admin da Faculdade", "admin@faculdade.local", Papel.ADMIN),
    ("Profa. Helena Souza", "professor@faculdade.local", Papel.PROFESSOR),
    ("Aluno Demo", "aluno@faculdade.local", Papel.ALUNO),
    ("Aluna Demo 2", "aluno2@faculdade.local", Papel.ALUNO),
]


class Command(BaseCommand):
    help = "Cria os usuários de demonstração (idempotente). Senha: variável SEED_SENHA."

    def handle(self, *args, **opcoes):
        senha = os.environ.get("SEED_SENHA", "demo12345")
        for nome, email, papel in DEMO:
            usuario, criado = Usuario.objects.get_or_create(
                email=email,
                defaults={"nome": nome, "papel": papel, "senha_hash": make_password(senha)},
            )
            self.stdout.write(f"{'criado' if criado else 'existe'}: {email} ({usuario.papel})")
