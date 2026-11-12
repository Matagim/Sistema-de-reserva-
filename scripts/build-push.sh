#!/usr/bin/env bash
# Build e push das imagens para o ECR.
#
#   scripts/build-push.sh <servico|todos> <tag>
#   scripts/build-push.sh todos v1
#   scripts/build-push.sh reservas v2
#   QUEBRAR_HEALTH=1 scripts/build-push.sh reservas v3    # imagem "ruim" da demo do circuit breaker
#
# Serviços: web usuarios recursos reservas notificacoes migracao
# Variáveis: AWS_REGION (padrão us-east-1), REPO_PREFIX (padrão "reserva", gera reserva-web etc.)
set -euo pipefail

SERVICO="${1:?uso: $0 <servico|todos> <tag>}"
TAG="${2:?informe a tag (v1, v2...); não use latest}"
REGIAO="${AWS_REGION:-us-east-1}"
PREFIXO="${REPO_PREFIX:-reserva}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

CONTA="$(aws sts get-caller-identity --query Account --output text)"
REGISTRO="${CONTA}.dkr.ecr.${REGIAO}.amazonaws.com"

aws ecr get-login-password --region "$REGIAO" | docker login --username AWS --password-stdin "$REGISTRO"

contexto_de() {
  case "$1" in
    migracao) echo "$RAIZ/infra/bootstrap" ;;
    *)        echo "$RAIZ/servicos/$1" ;;
  esac
}

construir() {
  local nome="$1" ctx imagem
  ctx="$(contexto_de "$nome")"
  imagem="${REGISTRO}/${PREFIXO}-${nome}:${TAG}"
  echo "==> $nome -> $imagem"
  docker build --build-arg "VERSAO=${TAG}" --build-arg "QUEBRAR_HEALTH=${QUEBRAR_HEALTH:-0}" -t "$imagem" "$ctx"
  docker push "$imagem"
}

if [ "$SERVICO" = "todos" ]; then
  for s in web usuarios recursos reservas notificacoes migracao; do construir "$s"; done
else
  construir "$SERVICO"
fi
