# Imagem "migracao": roda o bootstrap.sql com o usuário master (extensão, esquemas e usuários).
FROM postgres:16-alpine
COPY bootstrap.sql /bootstrap.sql
COPY bootstrap.sh /bootstrap.sh
RUN chmod +x /bootstrap.sh
ENTRYPOINT ["/bootstrap.sh"]
