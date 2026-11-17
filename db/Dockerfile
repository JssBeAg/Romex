FROM postgres:16-alpine

# Scripts in this folder run once, when the data volume is created
COPY init.sql /docker-entrypoint-initdb.d/init.sql
