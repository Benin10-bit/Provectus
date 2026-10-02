# Ingestor Fênix no Docker Compose do Provectus

O serviço `question_ingestor` executa a extração sob demanda; `question_importer` é um comando separado para uma importação explicitamente solicitada. O `docker-compose.yml` original, `db`, `api`, `frontend` e o volume `pgdata` não são substituídos. Para a etapa de PostgreSQL, consulte `IMPORT_RUNBOOK.md`.

## 1. Instalar os arquivos

Coloque **o conteúdo deste complemento** na pasta do Provectus, ao lado do `docker-compose.yml` existente:

```text
Provectus/
  docker-compose.yml                 # o seu, sem alteração
  docker-compose.ingestion.yml       # novo
  .env.ingestion.example             # novo
  question_ingestor/                 # projeto Python, Dockerfile incluído
```

Não mova os PDFs nem o staging de 43 GB. Ambos continuarão em suas pastas do host e serão montados no container. Não coloque o staging dentro do diretório de build nem copie esses dados para a imagem.

## 2. Configurar caminhos

Na pasta do Provectus:

```bash
cp .env.ingestion.example .env.ingestion
id -u
id -g
```

Edite `.env.ingestion` e substitua `QUESTION_PDF_ROOT` pelo caminho absoluto da pasta que **contém as pastas das matérias**; substitua `QUESTION_STAGING_ROOT` pela pasta de staging que você já usa. Confira `HOST_UID` e `HOST_GID` com os dois comandos acima. Não use `/data/pdfs` ou `/data/staging` nesses valores: esses são os caminhos *dentro* do container. Os caminhos do host precisam existir; o Compose não os criará automaticamente.

Antes do primeiro batch Docker, pare qualquer batch ou review local e confira o staging existente. Guarde um backup do `staging.db` (e dos eventuais `staging.db-wal`/`staging.db-shm` do mesmo instante). Se `PRAGMA integrity_check` não responder `ok`, pare e preserve os arquivos para recuperação; não execute o batch nesse banco.

## 3. Conferir a configuração e construir

Os comandos abaixo são executados na pasta do Provectus. O primeiro `.env` já pertence ao Provectus; o segundo contém os caminhos de ingestão. O `-f` adicional não modifica o Compose original.

```bash
docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  config --services

docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  build question_ingestor
```

O serviço é comandado explicitamente; `docker compose up -d` usado anteriormente, sem o arquivo complementar, continua igual. Mesmo se alguém ativar o perfil e executar `up`, o comando padrão do ingestor só mostra `--help` e encerra; não inicia batch.

## 4. Primeiro teste sem extração

```bash
docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm question_ingestor batch /data/pdfs --out /data/staging --dry-run
```

Confira o `hierarchy_report.json` no staging existente. O PDF root é montado em leitura; o staging é montado para escrita. O processo usa seu UID/GID para manter a propriedade dos arquivos.

## 5. Retomar o staging existente

Teste um item selecionado antes do lote inteiro:

```bash
docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm question_ingestor batch /data/pdfs --out /data/staging --limit 1 --retry-failed
```

`--limit 1` inclui arquivos já concluídos na seleção determinística e, portanto, pode resultar em `SKIPPED`. Depois de conferir, retome os documentos falhos:

```bash
docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  run --rm question_ingestor batch /data/pdfs --out /data/staging --retry-failed
```

Os documentos `DONE` com o mesmo SHA-256, parser e configuração serão pulados. Reiniciar o Docker não executa o ingestor nem apaga o staging. Não use `--force` no acervo inteiro para retomar falhas.

## 6. Saídas e revisão

Relatórios: `QUESTION_STAGING_ROOT/reports/global.md` e `global.json`. Dados: `QUESTION_STAGING_ROOT/staging.db`, `documents/` e `storage/`. O editor de revisão atual pode continuar sendo iniciado pelo Python local, apontando para a mesma pasta de staging, **após encerrar o batch**. O serviço Docker nesta etapa não publica nenhuma porta.

O serviço `question_ingestor` continua sem conexão com `db`. Para a etapa opcional de importação, o complemento também contém `question_importer` e a migration isolada `api/migrations/004_question_bank.sql`. Siga `IMPORT_RUNBOOK.md` para preparar o schema, conferir uma amostra e importar somente `OK`. Não há endpoints nem frontend de questões nesta entrega.
