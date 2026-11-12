from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import EhAdmin
from .models import Recurso
from .serializers import RecursoSerializer


class AdminParaEscrever:
    """Leitura é pública (catálogo); escrita só para o papel admin."""

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return []
        return [EhAdmin()]


class RecursosView(AdminParaEscrever, APIView):
    def get(self, request):
        consulta = Recurso.objects.order_by("tipo", "nome")
        tipo = request.query_params.get("tipo")
        if tipo:
            consulta = consulta.filter(tipo=tipo)
        ativo = request.query_params.get("ativo")
        if ativo in ("true", "false"):
            consulta = consulta.filter(ativo=(ativo == "true"))
        return Response(RecursoSerializer(consulta, many=True).data)

    def post(self, request):
        serializer = RecursoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)


class RecursoView(AdminParaEscrever, APIView):
    def _obter(self, pk):
        return Recurso.objects.filter(pk=pk).first()

    def get(self, request, pk):
        recurso = self._obter(pk)
        if recurso is None:
            return Response({"erro": "recurso_inexistente", "detalhe": f"recurso {pk} não existe"}, status=404)
        return Response(RecursoSerializer(recurso).data)

    def patch(self, request, pk):
        recurso = self._obter(pk)
        if recurso is None:
            return Response({"erro": "recurso_inexistente", "detalhe": f"recurso {pk} não existe"}, status=404)
        serializer = RecursoSerializer(recurso, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
