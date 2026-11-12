#!/usr/bin/env bash
# Demonstração: duas requisições simultâneas para o MESMO horário -> um 201 e um 409.
#
#   BASE_URL=http://<dns-do-alb> scripts/demo/concorrencia.sh [recurso_id] [dias_a_frente] [hora]
#
# Usa os usuários do seed (SEED_SENHA, padrão demo12345).
set -euo pipefail

BASE_URL="${BASE_URL:?defina BASE_URL (ex.: http://localhost:8000)}"
SENHA="${SEED_SENHA:-demo12345}"
RECURSO="${1:-1}"
DIAS="${2:-3}"
HORA="${3:-14}"

DIA="$(date -d "+${DIAS} days" +%F 2>/dev/null || date -v+${DIAS}d +%F)"
INICIO="${DIA}T$(printf '%02d' "$HORA"):00"
FIM="${DIA}T$(printf '%02d' $((HORA + 2))):00"

token() {
  curl -sf -X POST "$BASE_URL/api/usuarios/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$1\",\"senha\":\"$SENHA\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])'
}
T1="$(token aluno@faculdade.local)"
T2="$(token aluno2@faculdade.local)"

CORPO="{\"recurso_id\":$RECURSO,\"inicio\":\"$INICIO\",\"fim\":\"$FIM\"}"
echo "Reservando o recurso $RECURSO de $INICIO a $FIM com dois usuários ao mesmo tempo..."

tentar() {
  curl -s -o "/tmp/conc_$1.json" -w "$1 -> HTTP %{http_code}\n" -X POST "$BASE_URL/api/reservas/" \
    -H "Authorization: Bearer $2" -H 'Content-Type: application/json' -d "$CORPO"
}
tentar aluno "$T1" &
tentar aluno2 "$T2" &
wait

echo; echo "Corpos das respostas:"
cat /tmp/conc_aluno.json; echo
cat /tmp/conc_aluno2.json; echo
