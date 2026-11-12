
# Variáveis de conexão do master
set -eu
: "${DB_SENHA:?defina DB_SENHA (senha dos usuarios de servico)}"
exec psql -v ON_ERROR_STOP=1 -v senha="$DB_SENHA" -f /bootstrap.sql
