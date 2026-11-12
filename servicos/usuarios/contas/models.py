from django.db import models


class Papel(models.TextChoices):
    ALUNO = "aluno", "Aluno"
    PROFESSOR = "professor", "Professor"
    ADMIN = "admin", "Admin"


class Usuario(models.Model):
    """Tabela usuarios.usuarios (esquema `usuarios`, definido pelo search_path do serviço)."""

    nome = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    senha_hash = models.CharField(max_length=256)
    papel = models.CharField(max_length=10, choices=Papel.choices, default=Papel.ALUNO)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(papel__in=Papel.values),
                name="usuarios_papel_valido",
            )
        ]

    def __str__(self):
        return f"{self.nome} <{self.email}>"
