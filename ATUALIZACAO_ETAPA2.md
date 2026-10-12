# PROVECTUS — Atualização segura da Etapa 2

Esta entrega modifica código e inclui a migração 009. Os comandos abaixo foram revisados e sua sintaxe foi verificada; não foram executados na instalação Docker do usuário. `db`, `api` e `frontend` são os nomes dos serviços observados no Compose deste projeto, distintos de `postgres_db`, `fastapi_app` e `react_frontend`.

## Antes de aplicar

Tenha backup do banco e dos arquivos persistentes do Banco de Questões, com restauração validada em ambiente separado. Salve a versão anterior do código. Este backup continua pendente de confirmação do proprietário. Não aplique a atualização enquanto essa condição não estiver atendida. Finalize sessões/rascunhos ativos e suspenda registros durante a manutenção; confirme que não há importação em andamento.

Não execute `atualizar.sh` nem o guia da Etapa 1 para esta entrega. Não substitua `.env`, `.env.ingestion` ou diretórios persistentes. Não remova volumes. A Etapa 2 preserva Dockerfiles, Compose e dependências da Etapa 1.

## Copiar somente os arquivos da entrega

O comando usa o ZIP completo, mas copia apenas os arquivos modificados ou acrescentados. Não extrai sobre os diretórios persistentes. O diretório temporário fica disponível para inspeção.

```bash
(
  set -euo pipefail
  read -r -p 'Diretório da instalação PROVECTUS: ' provectus_install
  read -r -p 'Caminho de PROVECTUS_Etapa2_Corrigido.zip: ' provectus_zip
  test -d "$provectus_install/api/app"
  test -f "$provectus_install/.env"
  test -f "$provectus_install/.env.ingestion"
  test -f "$provectus_install/docker-compose.yml"
  test -f "$provectus_zip"
  read -r -p 'Após validar a restauração do banco E dos assets, digite BACKUP VALIDADO: ' provectus_backup
  test "$provectus_backup" = 'BACKUP VALIDADO'
  provectus_unpack=$(mktemp -d -t provectus-etapa2.XXXXXXXX)
  unzip -q "$provectus_zip" -d "$provectus_unpack"
  python3 - "$provectus_unpack/provectus" "$provectus_install" <<'PY'
from pathlib import Path
import shutil, sys
source, destination = map(Path, sys.argv[1:])
# Generated from the byte comparison against the final Etapa 1 ZIP.
files = '''
ATUALIZACAO_ETAPA2.md
README.md
RESULTADOS_ETAPA2.md
api/app/block_guidance.py
api/app/goals.py
api/app/metrics.py
api/app/models.py
api/app/planner.py
api/app/schemas.py
api/app/services.py
api/app/study_analysis.py
api/migrations/009_bloco_medidas_opcionais.sql
api/tests/test_flows.py
api/tests/test_goals.py
api/tests/test_stage2_goals.py
api/tests/test_stage2_measures.py
api/tests/test_stage2_postgresql.py
api/tests/test_study_analysis.py
frontend/src/components/RecordEditor.tsx
frontend/src/components/dashboard/DashboardKpis.tsx
frontend/src/components/dashboard/PeriodGoals.tsx
frontend/src/components/dashboard/WeeklyGoals.tsx
frontend/src/lib/api.ts
frontend/src/lib/goals.ts
frontend/src/lib/study.ts
frontend/src/lib/types.ts
frontend/src/pages/BlockForm.tsx
frontend/src/pages/GoalsPage.tsx
frontend/src/pages/HistoryPage.tsx
frontend/src/pages/RelatorioMensalPage.tsx
frontend/src/pages/StudyPage.tsx
frontend/src/test/dashboardTargets.test.tsx
frontend/src/test/periodGoals.test.tsx
frontend/src/test/redesign.test.tsx
frontend/src/test/stage2Capture.test.ts
'''.split()
for name in files:
    target = destination / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / name, target)
print(f'{len(files)} arquivos de código/testes/documentação copiados; configurações e assets preservados.')
PY
  printf 'Extração para inspeção: %s\n' "$provectus_unpack"
)
```

## Construir, verificar o estado anterior e migrar

Execute o bloco a seguir no diretório da instalação, depois da cópia. Ele exige que o banco existente esteja em execução e que as migrações anteriores já estejam registradas com os checksums esperados. Se a verificação falhar, pare e confira o estado: não force, não edite a tabela de versões e não execute migrações antigas manualmente.

```bash
(
  set -euo pipefail
  test -f .env
  test -f .env.ingestion
  read -r -p 'Backup do banco e assets com restauração validada? Digite BACKUP VALIDADO: ' provectus_backup
  test "$provectus_backup" = 'BACKUP VALIDADO'
  provectus_compose=(sudo docker compose --env-file .env --env-file .env.ingestion -f docker-compose.yml -f docker-compose.ingestion.yml)
  "${provectus_compose[@]}" config --services
  provectus_db=$("${provectus_compose[@]}" ps -q db)
  test -n "$provectus_db"
  test "$(sudo docker inspect --format '{{.State.Running}}' "$provectus_db")" = true
  "${provectus_compose[@]}" build api frontend
  "${provectus_compose[@]}" run --rm --no-deps -T api python - <<'PY'
from pathlib import Path
from hashlib import sha256
from sqlalchemy import text, inspect
from app.database import engine
with engine.connect() as connection:
    if 'provectus_migrations' not in inspect(connection).get_table_names():
        raise SystemExit('Registro de migrações ausente. Confira o banco antes de continuar.')
    applied = dict(connection.execute(text('SELECT version, sha256 FROM provectus_migrations')).all())
    for file in sorted(Path('/app/migrations').glob('*.sql')):
        if file.name.startswith('009_'):
            continue
        expected = sha256(file.read_text().encode()).hexdigest()
        if applied.get(file.name) != expected:
            raise SystemExit(f'Migração anterior ausente ou divergente: {file.name}. Nada alterado por esta verificação.')
    print('Migrações anteriores confirmadas. Pré-verificação somente leitura.')
PY
  "${provectus_compose[@]}" stop api frontend
  "${provectus_compose[@]}" run --rm --no-deps api python -m app.migrate
  "${provectus_compose[@]}" up -d --no-deps --force-recreate api frontend
  "${provectus_compose[@]}" ps
  "${provectus_compose[@]}" logs --tail=80 api frontend
  "${provectus_compose[@]}" exec -T api curl -fsS http://localhost:8000/health
)
```

A API e o frontend ficam interrompidos durante a migração. O banco existente não é reiniciado nem recriado; seus volumes não são modificados pelo procedimento. Não há reimportação de questões. O migrador faz a alteração em transação e verifica versões/checksums; repetir após sucesso apenas confirma as versões.

Depois, abra a aplicação e verifique registros/histórico, Banco de Questões e imagens, relatório mensal, projeções e a conclusão de uma sessão. Faça qualquer ensaio de escrita primeiro em cópia descartável; não crie registros fictícios em produção só para testar.

## Reproduzir a integração em PostgreSQL 15

O teste `api/tests/test_stage2_postgresql.py` aceita apenas banco **vazio** chamado `provectus_etapa2_test`, sem esquema Banco de Questões preexistente. Ele aplica as migrações e escreve fixtures nesse banco. Use uma instância totalmente separada, sem Compose/volumes da instalação pessoal, e não aponte a DSN ao banco real. O ambiente de testes precisa das dependências de `api/requirements-dev.txt`.

O exemplo inicia um container separado com armazenamento temporário em memória; não monta volumes. A senha abaixo é fictícia e exclusiva desse ensaio. O container de teste é parado ao sair do bloco. A limpeza se limita ao container novo deste ensaio, nunca ao da instalação.

```bash
(
  set -euo pipefail
  provectus_test_container=$(sudo docker run --rm -d \
    --tmpfs /var/lib/postgresql/data:rw \
    -e POSTGRES_USER=provectus_test \
    -e POSTGRES_PASSWORD=etapa2_descartavel \
    -e POSTGRES_DB=provectus_etapa2_test \
    -p 127.0.0.1::5432 postgres:15-alpine)
  trap 'sudo docker stop "$provectus_test_container" >/dev/null' EXIT
  provectus_ready=false
  for provectus_attempt in {1..30}; do
    if sudo docker exec "$provectus_test_container" pg_isready -U provectus_test -d provectus_etapa2_test >/dev/null; then
      provectus_ready=true
      break
    fi
    sleep 1
  done
  test "$provectus_ready" = true
  provectus_test_port=$(sudo docker port "$provectus_test_container" 5432/tcp)
  provectus_test_port=${provectus_test_port##*:}
  export PROVECTUS_STAGE2_TEST_DATABASE_URL="postgresql+psycopg://provectus_test:etapa2_descartavel@127.0.0.1:${provectus_test_port}/provectus_etapa2_test"
  cd api
  DATABASE_URL=sqlite:// PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_stage2_postgresql.py
)
```

Esse comando PostgreSQL 15/Docker não foi executado aqui; a integração equivalente passou em PostgreSQL 16.2 isolado. Uma falha deve ser resolvida antes da implantação.

## Recuperação

Se build ou pré-verificação falharem, os containers existentes ainda não foram interrompidos e nenhum esquema foi alterado. Guarde os logs e corrija o problema antes de continuar.

Se a migração falhar, o migrador reverte a transação. Os containers antigos ainda existem, parados; se não houve sucesso da migração nem recriação, pode retomar a versão anterior com o mesmo comando Compose e `start api frontend`. Não tente contornar o erro preenchendo medidas desconhecidas.

Se 009 tiver sucesso, sua alteração é aditiva e conserva todas as linhas anteriores. **Não reverta colunas para NOT NULL nem apague os metadados.** Depois que houver registros novos com valores nulos, a Etapa 1 não é compatível com todos esses registros. Voltar apenas o código antigo pode causar erros de consulta; não há downgrade automático seguro nessa condição.

Se a versão nova apresentar problema, preserve banco/assets e suspenda somente API/frontend enquanto corrige uma versão compatível. Restauração do backup só deve ser decidida pelo proprietário após avaliar registros posteriores e validar o procedimento em cópia. Não é parte dos comandos desta entrega. Não existe backfill ou substituição de dados por valores artificiais para facilitar rollback.
