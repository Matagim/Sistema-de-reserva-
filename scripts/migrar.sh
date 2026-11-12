#!/usr/bin/env bash
# Prepara o banco na AWS: bootstrap (extensao, esquemas, usuarios) e migrations/seed de cada servico.
# Roda tarefas pontuais (ecs run-task) com as task definitions da stack reserva-app, usando a rede do ALB/tasks.
#
#   scripts/migrar.sh                 # tudo, na ordem certa
#   scripts/migrar.sh reservas        # so as migrations de um servico (bootstrap, usuarios, recursos, reservas)
#
# Pre-requisitos: stacks reserva-dados e reserva-app criadas; imagens no ECR; AWS CLI configurada.
# Variaveis: AWS_REGION (padrao us-east-1), STACK_APP (padrao reserva-app), SEED=0 para pular o seed.
# E idempotente: pode rodar de novo a cada deploy que mude o esquema.
set -euo pipefail

REGIAO="${AWS_REGION:-us-east-1}"
STACK="${STACK_APP:-reserva-app}"
ALVO="${1:-todos}"
SEED="${SEED:-1}"

saida() {
  aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGIAO" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

CLUSTER="$(saida Cluster)"
SG="$(saida ServicosSecurityGroup)"
SUBNETS="$(saida SubnetsCsv)"
LOGS="$(saida LogGrupoNome)"
[ -n "$CLUSTER" ] && [ -n "$SG" ] && [ -n "$SUBNETS" ] || { echo "nao consegui ler as saidas de $STACK" >&2; exit 1; }

# executar <familia-da-task-definition> <container> <comando JSON ou vazio>
executar() {
  local familia="$1" container="$2" comando="${3:-}" overrides arn id codigo
  if [ -n "$comando" ]; then
    overrides="{\"containerOverrides\":[{\"name\":\"$container\",\"command\":$comando}]}"
  else
    overrides='{}'
  fi
  echo "==> $familia ${comando:-(comando padrao da imagem)}"
  arn="$(aws ecs run-task --region "$REGIAO" --cluster "$CLUSTER" --launch-type FARGATE \
    --task-definition "$familia" --overrides "$overrides" \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG],assignPublicIp=ENABLED}" \
    --query 'tasks[0].taskArn' --output text)"
  [ -n "$arn" ] && [ "$arn" != "None" ] || { echo "run-task nao iniciou a tarefa (veja failures com aws ecs run-task)" >&2; exit 1; }
  id="${arn##*/}"
  aws ecs wait tasks-stopped --region "$REGIAO" --cluster "$CLUSTER" --tasks "$arn"
  codigo="$(aws ecs describe-tasks --region "$REGIAO" --cluster "$CLUSTER" --tasks "$arn" \
    --query "tasks[0].containers[?name=='$container'].exitCode | [0]" --output text)"
  # os logs chegam ao CloudWatch com alguns segundos de atraso
  sleep 5
  aws logs get-log-events --region "$REGIAO" --log-group-name "$LOGS" \
    --log-stream-name "$container/$container/$id" --query 'events[].message' --output text 2>/dev/null | tr '\t' '\n' | sed 's/^/    /' || true
  if [ "$codigo" != "0" ]; then
    echo "FALHOU ($familia): exitCode=$codigo" >&2
    aws ecs describe-tasks --region "$REGIAO" --cluster "$CLUSTER" --tasks "$arn" \
      --query 'tasks[0].[stoppedReason,containers[0].reason]' --output text >&2 || true
    exit 1
  fi
}

migrar_servico() {
  local nome="$1" cmd
  if [ "$SEED" = "1" ] && [ "$nome" != "reservas" ]; then
    cmd='["sh","-c","python manage.py migrate --noinput && python manage.py seed"]'
  else
    cmd='["python","manage.py","migrate","--noinput"]'
  fi
  executar "reserva-$nome" "$nome" "$cmd"
}

case "$ALVO" in
  todos)
    executar reserva-migracao migracao
    migrar_servico usuarios
    migrar_servico recursos
    migrar_servico reservas
    ;;
  bootstrap) executar reserva-migracao migracao ;;
  usuarios|recursos|reservas) migrar_servico "$ALVO" ;;
  *) echo "uso: $0 [todos|bootstrap|usuarios|recursos|reservas]" >&2; exit 2 ;;
esac
echo "Banco pronto."
