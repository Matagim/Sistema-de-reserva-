
-- Variável do psql: :senha (senha dos usuários de serviço).
-- Cria a extensão usada pela restrição de exclusão de reservas, um usuário de banco
-- por serviço e um esquema por serviço, com permissão só no próprio esquema.
-- As tabelas NÃO são criadas aqui: vêm do `python manage.py migrate` de cada serviço.

CREATE EXTENSION IF NOT EXISTS btree_gist;

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', r, :'senha')
FROM unnest(ARRAY['app_usuarios', 'app_recursos', 'app_reservas']) AS r
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r)
\gexec

SELECT format('ALTER ROLE %I PASSWORD %L', r, :'senha')
FROM unnest(ARRAY['app_usuarios', 'app_recursos', 'app_reservas']) AS r
\gexec

CREATE SCHEMA IF NOT EXISTS usuarios;
CREATE SCHEMA IF NOT EXISTS recursos;
CREATE SCHEMA IF NOT EXISTS reservas;

REVOKE ALL ON SCHEMA usuarios FROM PUBLIC;
REVOKE ALL ON SCHEMA recursos FROM PUBLIC;
REVOKE ALL ON SCHEMA reservas FROM PUBLIC;

GRANT USAGE, CREATE ON SCHEMA usuarios TO app_usuarios;
GRANT USAGE, CREATE ON SCHEMA recursos TO app_recursos;
GRANT USAGE, CREATE ON SCHEMA reservas TO app_reservas;

ALTER ROLE app_usuarios SET search_path = usuarios;
ALTER ROLE app_recursos SET search_path = recursos;
ALTER ROLE app_reservas SET search_path = reservas;
