#!/usr/bin/env bash
# Demonstração do ALB e do rolling deployment: chama a API em loop e mostra QUAL task
# respondeu (X-Task-Id), QUAL versão (X-Versao) e o código HTTP.
#
#   BASE_URL=http://<dns-do-alb> scripts/demo/loop-alb.sh [caminho] [intervalo_s]
#   BASE_URL=... scripts/demo/loop-alb.sh /api/reservas/regras 0.5
set -u

BASE_URL="${BASE_URL:?defina BASE_URL (ex.: http://localhost:8000)}"
CAMINHO="${1:-/api/recursos/}"
INTERVALO="${2:-0.5}"

cabecalho() {  # $1 = nome do cabeçalho, $2 = texto da resposta
  printf '%s' "$2" | tr -d '\r' | awk -F': ' -v n="$1" 'tolower($1) == n { print $2; exit }'
}

while true; do
  resposta="$(curl -s -o /dev/null -D - -w 'CODIGO:%{http_code}' "$BASE_URL$CAMINHO" || true)"
  codigo="${resposta##*CODIGO:}"
  printf '%s  task=%s  versao=%s\n' "$codigo" \
    "$(cabecalho x-task-id "$resposta")" "$(cabecalho x-versao "$resposta")"
  sleep "$INTERVALO"
done
