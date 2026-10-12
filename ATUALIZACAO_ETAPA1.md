# Atualização local — Etapa 1

Esta entrega não muda esquema. Não execute migrations, `atualizar.sh`, reimportação ou rollback de dados para instalar estas quatro correções. O script antigo é preservado, mas executa o migrador e não é o caminho desta etapa.

## Antes da aplicação

Confirme que existe backup **validado e restaurável** do PostgreSQL e dos arquivos externos do BQ. A execução que produziu este ZIP não fez nem validou seu backup. Guarde também a versão anterior do código para eventual reversão.

A instalação deve ser a existente, com banco `db` em execução e suas configurações/imagens já funcionais. Não use esta receita para criar instalação nova ou corrigir migrations históricas pendentes.

## 1. Copiar somente código alterado

Abra um terminal Bash. O bloco pede os caminhos reais e confirma a pendência de backup. Copia somente arquivos desta etapa; não substitui `.env`, `.env.ingestion`, Compose, Dockerfiles, volumes, imagens ou arquivos legítimos não relacionados.

```bash
(
  set -euo pipefail
  read -r -p 'Pasta da instalação existente do PROVECTUS: ' etapa1_instalacao
  read -r -p 'Caminho do PROVECTUS_Etapa1_Corrigido.zip: ' etapa1_zip
  etapa1_instalacao=$(realpath "$etapa1_instalacao")
  etapa1_zip=$(realpath "$etapa1_zip")
  test -f "$etapa1_zip"
  test -f "$etapa1_instalacao/docker-compose.yml"
  test -f "$etapa1_instalacao/.env"
  test -f "$etapa1_instalacao/.env.ingestion"
  test -f "$etapa1_instalacao/api/app/main.py"
  read -r -p 'Banco e assets têm backup validado? Digite BACKUP VALIDADO: ' etapa1_backup
  if [ "$etapa1_backup" != 'BACKUP VALIDADO' ]; then
    printf 'Atualização interrompida: backup validado ainda não confirmado.\n'
    exit 1
  fi

  cd "$etapa1_instalacao"
  etapa1_compose=(sudo docker compose --project-directory "$etapa1_instalacao" \
    --env-file "$etapa1_instalacao/.env" --env-file "$etapa1_instalacao/.env.ingestion")
  etapa1_db_id=$("${etapa1_compose[@]}" ps -q db)
  test -n "$etapa1_db_id"
  test "$(sudo docker inspect --format '{{.State.Running}}' "$etapa1_db_id")" = true

  etapa1_extraido=$(mktemp -d)
  unzip -q "$etapa1_zip" -d "$etapa1_extraido"
  etapa1_origem="$etapa1_extraido/provectus"
  etapa1_arquivos=(
    README.md
    RESULTADOS_ETAPA1.md
    ATUALIZACAO_ETAPA1.md
    api/app/services.py
    api/app/question_bank.py
    api/tests/test_report_error_trend.py
    api/tests/test_question_bank_names.py
    frontend/package.json
    frontend/package-lock.json
    frontend/src/pages/RelatorioMensalPage.tsx
    frontend/src/test/reportErrors.test.tsx
    frontend/src/test/requestNoContent.test.ts
    question_ingestor/src/question_ingestor/importing/postgres.py
    question_ingestor/tests/test_import_failures.py
    question_ingestor/tests/test_import_postgresql.py
  )
  for etapa1_relativo in "${etapa1_arquivos[@]}"; do
    test -f "$etapa1_origem/$etapa1_relativo"
  done
  for etapa1_relativo in "${etapa1_arquivos[@]}"; do
    mkdir -p "$(dirname "$etapa1_instalacao/$etapa1_relativo")"
    cp "$etapa1_origem/$etapa1_relativo" "$etapa1_instalacao/$etapa1_relativo"
  done
  printf 'Código copiado. Nenhum comando de escrita no banco foi executado.\n'
)
```

`docker compose ps` e `docker inspect` apenas confirmam o banco existente; não o iniciam/recriam. Se houver erro, confira caminho, permissões e configuração existente antes de continuar. A confirmação digitada representa sua verificação, não uma validação automática de backup.

## 2. Reconstruir e trocar os containers da aplicação

Este bloco interage com os containers `api`/`frontend`. Ele mantém `db` e volumes existentes, carrega ambos os arquivos de ambiente e não executa migrador. Parar/recriar a aplicação interrompe brevemente seu uso; não apaga o banco.

```bash
(
  set -euo pipefail
  read -r -p 'Pasta da instalação onde o código já foi atualizado: ' etapa1_instalacao
  cd "$etapa1_instalacao"
  test -f RESULTADOS_ETAPA1.md
  test -f .env
  test -f .env.ingestion
  etapa1_compose=(sudo docker compose --project-directory "$PWD" --env-file "$PWD/.env" --env-file "$PWD/.env.ingestion")
  etapa1_db_id=$("${etapa1_compose[@]}" ps -q db)
  test -n "$etapa1_db_id"
  test "$(sudo docker inspect --format '{{.State.Running}}' "$etapa1_db_id")" = true
  "${etapa1_compose[@]}" build api frontend
  "${etapa1_compose[@]}" up -d --no-deps --force-recreate api frontend
  "${etapa1_compose[@]}" ps api frontend
  "${etapa1_compose[@]}" exec -T api curl -fsS http://localhost:8000/health
  "${etapa1_compose[@]}" logs --tail=50 api frontend
)
```

Se sua instalação utiliza outros arquivos Compose por configuração local, mantenha a mesma seleção já usada nela. Nenhum arquivo Compose é substituído pelo bloco de cópia. Se o healthcheck falhar, consulte os logs; não aplique migrations nem crie um banco vazio como tentativa de resolver esta etapa.

## 3. Atualizar a imagem do ingestor, se utilizada

A correção A01 está no ingestor, não na imagem da API. Se as importações usam os serviços `question_ingestor`/`question_importer`, reconstrua a imagem compartilhada; isso **não inicia importação**:

```bash
# Na pasta da instalação, após copiar o código e confirmar backup:
sudo docker compose --env-file .env --env-file .env.ingestion \
  -f docker-compose.yml -f docker-compose.ingestion.yml \
  --profile ingestion build question_ingestor
```

O `question_importer` usa essa mesma imagem na próxima execução explicitamente autorizada. Não execute `import-ok --apply` ou `rollback-import --apply` como parte da atualização. Se utiliza instalação Python do ingestor fora do Docker, atualize o pacote a partir desta cópia no ambiente já utilizado, preservando staging e PDFs.

## 4. Conferência funcional

Abra o relatório mensal: “Erros observados” deve mostrar respostas erradas reais; “Classificados” e cobertura permanecem separados. Estado insuficiente fica neutro. Nomes apenas com espaços devem retornar 422; mover uma pasta/lista sem renomear deve continuar funcionando. Esses testes podem ser feitos em cópia/ambiente de teste; não é necessário criar dados de produção para validar a atualização.

## 5. Jobs antigos ou status FAILED indisponível

Não existe reconciliação automática nesta entrega. Antes de qualquer intervenção manual em dados reais, confirme backup validado e que nenhum importador ainda trabalha no job. Anote o `import_job_id` da saída/nota de exceção.

Uma inspeção somente leitura pode ser feita com o `psql` do serviço `db`:

```bash
sudo docker compose --env-file .env --env-file .env.ingestion exec db \
  sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

No psql, execute apenas a inspeção, usando o UUID realmente retornado:

```sql
\prompt 'UUID do job a conferir: ' job_id
SELECT id,status,imported_count,skipped_count,error_code,finished_at
FROM question_bank.import_jobs WHERE id=:'job_id'::uuid;
SELECT document_sha256,count(*) AS questoes_confirmadas
FROM question_bank.questions WHERE import_job_id=:'job_id'::uuid
GROUP BY document_sha256 ORDER BY document_sha256;
```

Compare documentos e contagens com os logs. `skipped_count` não é reconstruído contando questões novas; não invente esse número. Se um PROCESSING estiver comprovadamente abandonado, a eventual marcação manual de falha exige decisão explícita e revisão do job, preservando questões/documentos já confirmados. Não há comando de escrita automática nesta receita. Divergência de contagens ou dúvida sobre processo ativo deve interromper a reconciliação, não provocar exclusão/reimportação.

Para testes locais descartáveis e resultados executados, veja `RESULTADOS_ETAPA1.md`.
