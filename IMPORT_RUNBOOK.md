# Importar apenas questões OK para o PostgreSQL do Provectus

O importador usa o PostgreSQL **existente** (`db` no Compose enviado). Ele lê `staging.db` e os assets do host em modo somente leitura. Não extrai PDFs, não altera `public`, não inicia interface de questões e não importa `REVIEW`/`ERROR`.

## Instalação

1. Pare o batch e o editor de revisão. Substitua a pasta `question_ingestor/` e o arquivo `docker-compose.ingestion.yml` pelos deste complemento, preservando seu `docker-compose.yml` e seus `.env` existentes.
2. Copie **somente** `api/migrations/004_question_bank.sql` para `Provectus/api/migrations/` ao lado das migrations 001–003. Não substitua a pasta `api` inteira.
3. Confira que `.env.ingestion` continua apontando para o **staging já existente**.
4. Faça um backup do PostgreSQL antes de migrar. Na raiz do Provectus:

```bash
sudo docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$HOME/provectus-before-question-bank.dump"
```

Confira que o arquivo de backup foi criado e tem tamanho diferente de zero. A migration é aditiva; não altera tabelas `public`, mas o backup permite recuperação caso ocorra um erro externo.

## Criar o schema isolado

```bash
sudo docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  build api question_ingestor

sudo docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm api python -m app.migrate
```

O migrador existente da API registra a migration 004 e valida seu checksum. Rodá-lo de novo não recria as tabelas. A API em execução não precisa reiniciar para esta migration, pois nenhum endpoint foi alterado.

## Prévia sem gravar no PostgreSQL

```bash
sudo docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm question_importer import-ok /data/staging --limit 5
```

O resultado exibe `questions_ok_selected`, `documents_selected`, `excluded_statuses` e `database_modified: false`. Sem `--apply`, nem `import-ok` nem `rollback-import` gravam dados.

## Importar uma amostra de 5 OK

```bash
sudo docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm question_importer import-ok /data/staging --limit 5 --apply
```

Guarde o `job_id` mostrado. Confira a contagem:

```bash
sudo docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM question_bank.questions"'
```

Confira também algumas linhas e respectivos recortes no staging antes de importar o restante. Os assets continuam no `QUESTION_STAGING_ROOT/storage`; não são duplicados como `BYTEA`.

## Importar todos os OK

```bash
sudo docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm question_importer import-ok /data/staging --apply
```

A importação lê um documento por vez e faz transação por documento. Em nova execução, IDs com payload idêntico são `skipped`; conteúdo alterado sob o mesmo ID causa erro explícito. Um job com falha pode ter PDFs anteriores já confirmados; seu `job_id` e estado ficam registrados em `question_bank.import_jobs`. Os metadados e os caminhos de assets são verificados contra os arquivos do staging. Não existe limite de tamanho de texto.

Para ver os totais por status e job:

```bash
sudo docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT automatic_status,count(*) FROM question_bank.questions GROUP BY 1"'
sudo docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT id,status,imported_count,skipped_count FROM question_bank.import_jobs ORDER BY started_at DESC LIMIT 10"'
```

## Desfazer um job específico

Use o `job_id` impresso na importação. Primeiro visualize a quantidade, depois execute explicitamente:

```bash
sudo docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm question_importer rollback-import JOB_ID

sudo docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm question_importer rollback-import JOB_ID --apply
```

O rollback remove apenas as questões **inseridas por aquele job**; não apaga arquivos do staging nem questões pré-existentes que foram `skipped`. Faça rollback de jobs parciais antes de executar uma nova importação se quiser limpar completamente uma tentativa com falha.

## Limites desta etapa

O importador não resolve duplicatas de conteúdo entre PDFs diferentes, não cria endpoints nem tela e não integra respostas de usuários. Os textos integrais e rich-content estão no `payload` JSONB; as colunas separadas facilitam filtros. O backend precisará montar `QUESTION_STAGING_ROOT/storage` em leitura quando a API de questões for implementada. Não remova esse diretório após importar.
