from rest_framework import serializers


class CadastroSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    senha = serializers.CharField(min_length=8, max_length=128, write_only=True)

    def validate_nome(self, valor):
        return valor.strip()

    def validate_email(self, valor):
        return valor.strip().lower()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    senha = serializers.CharField(max_length=128)

    def validate_email(self, valor):
        return valor.strip().lower()
