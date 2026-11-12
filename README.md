# Reservas da Faculdade

Sistema de reserva de salas, laboratórios e equipamentos, feito para demonstrar Docker, ECR, ECS/Fargate,
ALB e CloudFormation no AWS Learner Lab. O desenho completo (decisões, riscos, plano em fases) está no
documento de arquitetura; este repositório é a implementação.

## Como as peças se encaixam

```
navegador ──► ALB ──┬─ /api/usuarios/*  ──► usuarios  (3001)  login e JWT
                    ├─ /api/recursos/*  ──► recursos  (3002)  catálogo
                    ├─ /api/reservas/*  ──► reservas   (3003)  agenda + regra de conflito ──► SQS ──► notificacoes (worker)
                    └─ (qualquer outro) ──► web        (8080)  interface
                                   cada serviço ──► PostgreSQL (RDS), um esquema e um usuário de banco por serviço
```

- **Django 5.2 + Django REST Framework** nos quatro serviços HTTP; o worker é um script Python com boto3.
- **A dupla marcação é impedida pelo banco**: uma restrição de exclusão do PostgreSQL
  (`reservas_sem_sobreposicao`) rejeita qualquer reserva ativa que se sobreponha a outra do mesmo recurso,
  inclusive parcialmente. A API só traduz o erro `23P01` em `409`.
- O ALB **não reescreve o caminho**: cada serviço registra o prefixo `/api/<servico>` nas próprias URLs.
- O `/health` de todos os serviços **não consulta o banco** (uma queda do banco não derruba todas as tasks);
  as chamadas de dados respondem `503` quando o banco some.

## Estrutura

```
docker-compose.yml        PostgreSQL + serviços + nginx ("ALB" local em :8000)
.env.example
servicos/
  usuarios/               Django + DRF — cadastro, login, emissão do JWT
  recursos/               Django + DRF — catálogo (leitura pública, escrita só admin)
  reservas/               Django + DRF — agenda; agenda/regras.py (regras puras), eventos.py (SQS)
  web/                    Django com templates e JS puro, sem banco
  notificacoes/           worker.py (long polling do SQS), sem Django
infra/
  ecr.yaml                stack reserva-ecr: 6 repositórios
  dados.yaml              stack reserva-dados: RDS PostgreSQL, security group do banco, fila SQS + DLQ
  app.yaml                stack reserva-app: cluster, ALB, target groups, task definitions, services
  bootstrap/              bootstrap.sql + Dockerfile (imagem "migracao")
  local/                  nginx.conf e proxy.py (ALB local, com e sem Docker)
scripts/
  build-push.sh           build e push das 6 imagens para o ECR
  migrar.sh               bootstrap + migrations/seed no RDS, via ecs run-task
  teste_integracao.py     teste ponta a ponta (inclui a disputa pelo mesmo horário)
  demo/                   concorrencia.sh, loop-alb.sh
```

## Rodar localmente

### Com Docker

```bash
cp .env.example .env
docker compose up --build
```

Abra http://localhost:8000. O compose cria o banco, roda o `bootstrap`, aplica as migrations e o seed.

### Sem Docker (PostgreSQL local)

```bash
# 1. banco e bootstrap (como superusuário do PostgreSQL)
createdb faculdade
psql -d faculdade -v senha=dev12345 -f infra/bootstrap/bootstrap.sql

# 2. dependências de cada serviço (um venv serve para todos)
python -m venv .venv && . .venv/bin/activate
pip install -r servicos/reservas/requirements.txt -r servicos/web/requirements.txt

# 3. migrations e seed
export DB_HOST=localhost DB_SENHA=dev12345
(cd servicos/usuarios && DB_USER=app_usuarios python manage.py migrate && DB_USER=app_usuarios python manage.py seed)
(cd servicos/recursos && DB_USER=app_recursos python manage.py migrate && DB_USER=app_recursos python manage.py seed)
(cd servicos/reservas && DB_USER=app_reservas python manage.py migrate)

# 4. cada serviço em um terminal (ou em background)
(cd servicos/usuarios && DB_USER=app_usuarios gunicorn config.wsgi -b 127.0.0.1:3001)
(cd servicos/recursos && DB_USER=app_recursos gunicorn config.wsgi -b 127.0.0.1:3002)
(cd servicos/reservas && DB_USER=app_reservas RECURSOS_URL=http://localhost:3002 gunicorn config.wsgi -b 127.0.0.1:3003)
(cd servicos/web && gunicorn config.wsgi -b 127.0.0.1:8080)

# 5. o "ALB" local
python infra/local/proxy.py        # http://localhost:8000
```

### Contas do seed (senha `demo12345`, ou `SEED_SENHA`)

| E-mail | Papel |
|---|---|
| `admin@faculdade.local` | admin |
| `professor@faculdade.local` | professor |
| `aluno@faculdade.local`, `aluno2@faculdade.local` | aluno |

## API

| Método e caminho | Quem pode | Resposta |
|---|---|---|
| `POST /api/usuarios/cadastro` | qualquer um | `201` (sempre aluno), `400`, `409` e-mail repetido |
| `POST /api/usuarios/login` | qualquer um | `200` com `token` e `usuario`; `401` |
| `GET /api/recursos/?tipo=&ativo=` | qualquer um | lista |
| `GET /api/recursos/{id}` | qualquer um | `200` ou `404` |
| `POST /api/recursos/`, `PATCH /api/recursos/{id}` | admin | `201`/`200`; `401` sem token, `403` sem papel |
| `GET /api/reservas/regras` | qualquer um | regras em vigor (mudam com o deploy) |
| `GET /api/reservas/disponibilidade?recurso_id=&data=AAAA-MM-DD` | qualquer um | intervalos ocupados do dia |
| `GET /api/reservas/` | logado | minhas reservas |
| `POST /api/reservas/` | logado | `201`; `400` regra; `404` recurso; `409` ocupado ou recurso inativo; `503` |
| `DELETE /api/reservas/{id}` | dono ou admin | `200` (cancelada); `403`, `404` |

Horários são **locais da faculdade, sem fuso**: `2026-11-03T14:00`. Todo erro vem como
`{"erro": "<código>", "detalhe": ...}`. Toda resposta traz `X-Task-Id` (hostname da task) e `X-Versao`.

## Configuração (variáveis de ambiente)

| Variável | Onde | Padrão | Observação |
|---|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_SENHA` | usuarios, recursos, reservas | `localhost`, `5432`, `faculdade`, `app_<servico>` | na AWS vêm da stack de dados |
| `DB_SCHEMA` | idem | nome do serviço | define o `search_path` |
| `DB_SSLMODE` | idem | `prefer` | o RDS PostgreSQL 15+ exige SSL; `prefer` funciona local e na AWS |
| `JWT_SEGREDO` | usuarios, recursos, reservas | `dev-segredo-trocar` | **o mesmo valor nos três** |
| `DURACAO_MAX_HORAS`, `HORA_ABERTURA`, `HORA_FECHAMENTO`, `DIAS_ANTECEDENCIA_MAX` | reservas | `4`, `7`, `22`, `14` | mudar = novo deploy |
| `RECURSOS_URL` | reservas | `http://localhost:3002` | na AWS, a URL do ALB |
| `SQS_URL` | reservas, notificacoes | vazio | vazio em `reservas` = evento só no log |
| `FACULDADE_TZ` | reservas | `America/Fortaleza` | para "agora" e "no passado" |
| `PORT`, `WEB_CONCURRENCY` | imagens | porta do serviço, `2` | no máximo 2 conexões de banco por task |

Build args das imagens: `VERSAO` (aparece em `/health` e em `X-Versao`) e `QUEBRAR_HEALTH=1`
(faz o `/health` falhar, para a demonstração do circuit breaker).

## Testes

```bash
# regras de negócio e worker (sem banco)
(cd servicos/reservas && python -m unittest discover -s agenda/tests -t .)
(cd servicos/notificacoes && python -m unittest discover -s tests -t .)

# ponta a ponta, com o sistema no ar (cobre 201/409, cancelamento e 8 requisições simultâneas)
BASE_URL=http://localhost:8000 python scripts/teste_integracao.py
```

## Demonstrações

```bash
BASE_URL=http://<dns-do-alb> scripts/demo/concorrencia.sh [recurso_id] [dias_a_frente] [hora]   # 201 e 409
BASE_URL=http://<dns-do-alb> scripts/demo/loop-alb.sh /api/reservas/regras 0.5                   # task e versão
```

## ECR

```bash
scripts/build-push.sh todos v1
scripts/build-push.sh reservas v2
QUEBRAR_HEALTH=1 scripts/build-push.sh reservas v3     # imagem "ruim" do circuit breaker
```

Os repositórios são `reserva-web`, `reserva-usuarios`, `reserva-recursos`, `reserva-reservas`,
`reserva-notificacoes` e `reserva-migracao` (a stack `reserva-ecr` os cria). Nunca use a tag `latest`.

## Implantação na AWS (Learner Lab): passo a passo

Subir o sistema leva de 30 a 45 minutos (estimativa), em sua maior parte esperando o banco e a construção das
imagens. Tudo roda no **CloudShell** do Learner Lab. São três stacks, em camadas, com ciclos de vida
diferentes, e a ordem importa: `reserva-ecr` (repositórios), `reserva-dados` (banco e fila) e
`reserva-app` (aplicação, descartável).

### Antes de começar

- Learner Lab iniciado (indicador verde no AWS Academy) e o console da AWS aberto.
- O `reservas-faculdade.zip` deste projeto.
- Dois valores que você escolhe agora e usa de novo no passo 4. Anote os dois:
  - `DbSenha`: senha do banco, só letras e números, no mínimo 8 caracteres (exemplo: `SenhaDb2026`). Precisa
    ser a **mesma** nas stacks `reserva-dados` e `reserva-app`.
  - `JwtSecret`: segredo do login, no mínimo 8 caracteres (exemplo: `SegredoJwt2026`).

Os exemplos usam a região `us-east-1`. Se o console mostrar outra, troque nos comandos.

### 1. Preparar o CloudShell

1. No console, clique no ícone do CloudShell (`>_`) na barra superior e espere o terminal abrir.
2. Clique em **Actions → Upload file** e envie o zip.
3. Rode:

```bash
unzip reservas-faculdade.zip && cd reservas-faculdade
chmod +x scripts/*.sh scripts/demo/*.sh
export AWS_REGION=us-east-1
aws sts get-caller-identity                       # deve mostrar o número da conta
docker version --format '{{.Server.Version}}'     # deve mostrar a versão do Docker
```

O CloudShell fecha a sessão após 20 a 30 minutos sem uso. A pasta continua lá, mas **as variáveis do terminal
se perdem** (`AWS_REGION`, `VPC`, `SUBNETS`, `ARQ`). Se reabrir o terminal, refaça os comandos que as definem.

### 2. Repositórios e imagens

As imagens saem na arquitetura da máquina que as constrói, e a stack da aplicação precisa usar a mesma, senão
as tasks falham com `exec format error`. Descubra a sua e guarde o valor:

```bash
ARQ=$([ "$(uname -m)" = aarch64 ] && echo ARM64 || echo X86_64)
echo $ARQ                                         # X86_64 ou ARM64
```

Crie os repositórios e envie as 6 imagens, uma por vez (o laço limpa o disco entre elas, porque o CloudShell
tem pouco espaço):

```bash
aws cloudformation deploy --stack-name reserva-ecr --template-file infra/ecr.yaml

for s in usuarios recursos reservas web notificacoes migracao; do
  scripts/build-push.sh $s v1 || break
  docker image prune -af > /dev/null
done

aws ecr describe-images --repository-name reserva-reservas --query 'imageDetails[].imageTags'   # deve mostrar v1
```

Se aparecer `no space left on device`, rode `docker system prune -af` e repita só o serviço que falhou.

### 3. Rede, banco e fila

O comando escolhe sozinho a VPC padrão e duas subnets de zonas diferentes:

```bash
VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC Name=default-for-az,Values=true \
  --query 'Subnets[].[AvailabilityZone,SubnetId]' --output text | sort -u -k1,1 | head -2 | awk '{print $2}' | paste -sd,)
echo "VPC=$VPC"; echo "SUBNETS=$SUBNETS"
```

Confira: `VPC` começa com `vpc-` e `SUBNETS` tem duas subnets reais separadas por vírgula. Nunca use valores de
exemplo (`subnet-aaaa`) nem deixe as variáveis vazias: a stack falha na validação.

```bash
aws cloudformation deploy --stack-name reserva-dados --template-file infra/dados.yaml \
  --parameter-overrides VpcId=$VPC Subnets=$SUBNETS DbSenha='SenhaDb2026'
```

O RDS leva de 5 a 10 minutos. Espere o comando terminar. **Crie esta stack horas antes de uma apresentação.**

### 4. Aplicação

Cria o cluster, o ALB e os 5 serviços. Use a **mesma** `DbSenha` do passo 3. As imagens do passo 2 precisam
estar no ECR.

```bash
echo "VPC=$VPC"; echo "SUBNETS=$SUBNETS"; echo "ARQ=$ARQ"     # nenhum pode estar vazio

aws cloudformation deploy --stack-name reserva-app --template-file infra/app.yaml \
  --parameter-overrides VpcId=$VPC Subnets=$SUBNETS DbSenha='SenhaDb2026' JwtSecret='SegredoJwt2026' Arquitetura=$ARQ
```

### 5. Preparar o banco

O banco novo não tem esquemas nem usuários. O script cria a extensão, os esquemas e os usuários, e aplica as
migrations e os dados de exemplo (4 tarefas em sequência, com os logs de cada uma):

```bash
scripts/migrar.sh
```

Termina com `Banco pronto.` Pode ser repetido sem problema. Se a stack `reserva-app` não estiver pronta
(por exemplo, em `ROLLBACK_COMPLETE`), o script avisa logo no início. Enquanto o banco não é preparado, os
`/health` passam e as chamadas de dados respondem `503`: isso é esperado.

### 6. Testar e usar

```bash
ALB=$(aws cloudformation describe-stacks --stack-name reserva-app \
  --query "Stacks[0].Outputs[?OutputKey=='AlbUrl'].OutputValue" --output text)
echo $ALB
curl -s -o /dev/null -w "%{http_code}\n" $ALB/api/recursos/       # 200
BASE_URL=$ALB python3 scripts/teste_integracao.py
```

Se aparecer `502` ou `503` logo após o deploy, espere cerca de 1 minuto. Abra o endereço no navegador,
**com `http://`** (não há HTTPS), e entre com uma das contas do seed (tabela em "Rodar localmente").

### Ações da demonstração

Todas viram uma atualização da stack `reserva-app`. Repita `VpcId`, `Subnets`, `DbSenha`, `JwtSecret` e
`Arquitetura` junto com o parâmetro novo.

| Demonstração | Parâmetro |
|---|---|
| Escalar reservas | `QtdReservas=3` |
| Rolling deployment | `scripts/build-push.sh reservas v2` e depois `TagReservas=v2` |
| Circuit breaker | `QUEBRAR_HEALTH=1 scripts/build-push.sh reservas v3` e depois `TagReservas=v3`: o deploy falha e volta para a v2 |
| Mudar uma regra de negócio | `DuracaoMaxHoras=2` (novo deploy de reservas) |
| Economizar | `QtdPadrao=0 QtdReservas=0 QtdNotificacoes=0` (o RDS continua) |

### Pausar e retomar entre sessões

Fechar o laboratório não garante que os serviços parem. Deixar tudo ligado custa cerca de US$ 0,10 por hora
(estimativa pelos preços de lista de us-east-1; o saldo real está no painel do Learner Lab). Para pausar:

```bash
for s in web usuarios recursos reservas notificacoes; do
  aws ecs update-service --cluster reserva --service $s --desired-count 0 > /dev/null
done
DB=$(aws rds describe-db-instances --query 'DBInstances[?contains(DBInstanceIdentifier,`reserva`)].DBInstanceIdentifier' --output text)
aws rds stop-db-instance --db-instance-identifier $DB
```

Para retomar:

```bash
DB=$(aws rds describe-db-instances --query 'DBInstances[?contains(DBInstanceIdentifier,`reserva`)].DBInstanceIdentifier' --output text)
aws rds start-db-instance --db-instance-identifier $DB
aws rds wait db-instance-available --db-instance-identifier $DB
for s in web usuarios recursos reservas notificacoes; do
  aws ecs update-service --cluster reserva --service $s --desired-count 1 > /dev/null
done
```

O endereço do ALB não muda e os dados continuam no banco. O ALB continua cobrando mesmo pausado, e um RDS
parado por 7 dias é religado automaticamente pela AWS. Não use a opção *Reset* do laboratório, que costuma
apagar os recursos da conta.

### Problemas comuns

| Sintoma | O que fazer |
|---|---|
| Stack em `ROLLBACK_COMPLETE` | Não pode ser atualizada. Veja a causa nos eventos (abaixo), apague a stack e crie de novo. |
| `parameter value  for parameter name Subnets does not exist` (valor vazio ou de exemplo) | As variáveis `VPC` e `SUBNETS` estavam vazias. Refaça o passo 3 e confira o `echo` antes do `deploy`. |
| `exec format error` na task | A arquitetura das tasks difere da das imagens. Atualize a stack com `Arquitetura` igual ao `uname -m` (`aarch64` = `ARM64`, `x86_64` = `X86_64`). |
| `TaskDefinition not found` no `migrar.sh` | A stack `reserva-app` não está pronta ou a região é outra. Confira `AWS_REGION` e o status da stack. |
| O site não abre | Use `http://`, espere 1 a 2 minutos e confira se `running` é igual a `desired` nos services. |
| `503` com `banco_indisponivel` | Rode `scripts/migrar.sh` e confira se a `DbSenha` é a mesma nas duas stacks. |
| `no space left on device` no build | `docker system prune -af` e repita só o serviço que falhou. |

```bash
# eventos da stack (a causa costuma estar no CREATE_FAILED mais antigo)
aws cloudformation describe-stack-events --stack-name reserva-app --output text \
  --query 'StackEvents[].[Timestamp,LogicalResourceId,ResourceStatus,ResourceStatusReason]'

# services e logs
aws ecs describe-services --cluster reserva --services web usuarios recursos reservas notificacoes \
  --query 'services[].[serviceName,desiredCount,runningCount]' --output text
aws logs tail /ecs/reserva --since 10m

# apagar uma stack falhada
aws cloudformation delete-stack --stack-name reserva-app
aws cloudformation wait stack-delete-complete --stack-name reserva-app
```

### Apagar tudo no fim

Nesta ordem, esperando cada uma terminar (a aplicação depende do banco):

```bash
aws cloudformation delete-stack --stack-name reserva-app
aws cloudformation wait stack-delete-complete --stack-name reserva-app
aws cloudformation delete-stack --stack-name reserva-dados
aws cloudformation wait stack-delete-complete --stack-name reserva-dados
aws cloudformation delete-stack --stack-name reserva-ecr
```

Isso apaga o banco (sem cópia de segurança), a fila e as imagens.

## Limitações conhecidas (laboratório)

- O segredo do JWT e a senha do banco aparecem na task definition.
- Os três usuários de banco compartilham a senha `DB_SENHA`.
- O login usa o hash padrão do Django (PBKDF2, muitas iterações): numa task pequena leva alguns décimos
  de segundo de CPU.
- O `docker-compose.yml` ainda não foi executado; o código foi validado com PostgreSQL 16 e gunicorn locais,
  e os Dockerfiles e as stacks foram usados no Learner Lab.

## Próximos passos

1. Ensaiar o roteiro de 1 hora com as stacks reais e anotar os tempos de cada demonstração.
2. Atualizar o documento de arquitetura com as decisões que o laboratório confirmou ou derrubou.