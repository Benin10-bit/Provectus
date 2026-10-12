# PROVECTUS — Atualização da Etapa 3

Base: instalação final da Etapa 2. Serviços Compose reais: **db**, **api**, **frontend**. Containers: postgres_db, fastapi_app, react_frontend. Os comandos usam serviços. O PostgreSQL 15 e os volumes/assets existentes são preservados.

Não houve implantação nem execução de migração em produção. O ensaio PostgreSQL abaixo ainda não foi executado neste ambiente; passe por ele antes de atualizar sua instalação. O código e os testes SQLite/frontend estão concluídos; resultados em `RESULTADOS_ETAPA3.md`.

## 1. Ensaio da migração em PostgreSQL 15 separado

Extraia o ZIP em uma pasta de teste, fora da instalação pessoal. Prepare um ambiente Python 3.11+ com `api/requirements-dev.txt`. Na raiz dessa cópia, execute o bloco abaixo. Ele inicia um container descartável **sem volumes montados**; a senha é exclusiva do teste. Não use o Compose ou a DSN da instalação real.

```bash
(
  set -euo pipefail
  test -f api/tests/test_stage3_postgresql.py
  provectus_test_container=$(sudo docker run --rm -d \
    --tmpfs /var/lib/postgresql/data:rw \
    -e POSTGRES_USER=provectus_test \
    -e POSTGRES_PASSWORD=etapa3_descartavel \
    -e POSTGRES_DB=provectus_etapa3_test \
    -p 127.0.0.1::5432 postgres:15-alpine)
  trap 'sudo docker stop "$provectus_test_container" >/dev/null' EXIT
  provectus_ready=false
  for provectus_attempt in {1..30}; do
    if sudo docker exec "$provectus_test_container" pg_isready -U provectus_test -d provectus_etapa3_test >/dev/null; then
      provectus_ready=true
      break
    fi
    sleep 1
  done
  test "$provectus_ready" = true
  sudo docker exec "$provectus_test_container" createdb -U provectus_test provectus_etapa2_test
  provectus_test_port=$(sudo docker port "$provectus_test_container" 5432/tcp)
  provectus_test_port=${provectus_test_port##*:}
  export PROVECTUS_STAGE2_TEST_DATABASE_URL="postgresql+psycopg://provectus_test:etapa3_descartavel@127.0.0.1:${provectus_test_port}/provectus_etapa2_test"
  export PROVECTUS_STAGE3_TEST_DATABASE_URL="postgresql+psycopg://provectus_test:etapa3_descartavel@127.0.0.1:${provectus_test_port}/provectus_etapa3_test"
  cd api
  DATABASE_URL=sqlite:// PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_stage2_postgresql.py tests/test_stage3_postgresql.py
)
```

Ambos os testes recusam bancos previamente povoados ou com schema BQ preexistente. O ensaio verifica a preservação do legado, as migrations ordenadas, repetição e escritas reais do novo contrato. São esperados **10 testes aprovados** nesse comando; essa expectativa não é resultado já observado. Se falhar, resolva antes de implantar.

## 2. Preparação do código

Tenha backup do PostgreSQL **e** dos assets, com restauração validada separadamente. Guarde a versão anterior do código. Finalize rascunhos/sessões e suspenda registros/importações durante a manutenção. A confirmação abaixo é condição explícita do pedido do proprietário para uma implantação futura.

Não use `atualizar.sh`, `down -v`, limpeza de volumes ou reimportação. Não copie `.env`, `.env.ingestion`, dumps ou diretórios persistentes. O trecho usa uma extração temporária e copia apenas arquivos modificados/acrescentados desta etapa:

```bash
(
  set -euo pipefail
  read -r -p 'Diretório da instalação PROVECTUS: ' provectus_install
  read -r -p 'Caminho de PROVECTUS_Etapa3_Recomendador_Inteligente.zip: ' provectus_zip
  test -d "$provectus_install/api/app"
  test -f "$provectus_install/.env"
  test -f "$provectus_install/.env.ingestion"
  test -f "$provectus_install/docker-compose.yml"
  test -f "$provectus_zip"
  read -r -p 'Após validar restauração de banco e assets, digite BACKUP VALIDADO: ' provectus_backup
  test "$provectus_backup" = 'BACKUP VALIDADO'
  provectus_unpack=$(mktemp -d -t provectus-etapa3.XXXXXXXX)
  unzip -q "$provectus_zip" -d "$provectus_unpack"
  python3 - "$provectus_unpack/provectus" "$provectus_install" <<'PY'
from pathlib import Path
import shutil, sys
source, destination = map(Path, sys.argv[1:])
files = '''
ATUALIZACAO_ETAPA3.md
README.md
RESULTADOS_ETAPA3.md
api/app/block_guidance.py
api/app/clock.py
api/app/goals.py
api/app/models.py
api/app/planner.py
api/app/planning_models.py
api/app/recommender.py
api/app/schemas.py
api/app/study_analysis.py
api/migrations/010_recomendador.sql
api/tests/test_flows.py
api/tests/test_goals.py
api/tests/test_stage2_measures.py
api/tests/test_stage2_postgresql.py
api/tests/test_stage3_postgresql.py
api/tests/test_stage3_recommender.py
api/tests/test_study_analysis.py
api/tests/test_study_strategy.py
frontend/src/lib/study.ts
frontend/src/pages/CoveragePage.tsx
frontend/src/pages/Index.tsx
frontend/src/pages/ReviewPage.tsx
frontend/src/pages/StudyPage.tsx
frontend/src/test/stage3Recommender.test.tsx
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

## 3. Construção e pré-verificação somente leitura

Na instalação, o bloco seguinte constrói apenas API/frontend. O banco deve estar em execução. Verifica checksums das migrations 001–009 antes de interromper a aplicação. Divergência exige conferir a base; não edite o registro de versões para contornar a verificação.

```bash
(
  set -euo pipefail
  test -f .env
  test -f .env.ingestion
  read -r -p 'Backup com restauração validada e ensaio PostgreSQL aprovado? Digite VALIDADO: ' provectus_verified
  test "$provectus_verified" = 'VALIDADO'
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
        if file.name.startswith('010_'):
            continue
        if applied.get(file.name) != sha256(file.read_text().encode()).hexdigest():
            raise SystemExit(f'Migração anterior ausente ou divergente: {file.name}. Nada alterado por esta verificação.')
    print('Etapa 2 confirmada por versões e checksums. Pré-verificação somente leitura.')
PY
)
```

## 4. Migração 010 e recriação de API/frontend

Somente depois da preparação, ensaio e pré-verificação bem-sucedidos, ainda na instalação:

```bash
(
  set -euo pipefail
  provectus_compose=(sudo docker compose --env-file .env --env-file .env.ingestion -f docker-compose.yml -f docker-compose.ingestion.yml)
  "${provectus_compose[@]}" stop api frontend
  "${provectus_compose[@]}" run --rm --no-deps api python -m app.migrate
  "${provectus_compose[@]}" up -d --no-deps --force-recreate api frontend
  "${provectus_compose[@]}" ps
  "${provectus_compose[@]}" logs --tail=80 api frontend
  "${provectus_compose[@]}" exec -T api curl -fsS http://localhost:8000/health
)
```

`010_recomendador.sql` acrescenta campos anuláveis e constraints; não preenche o passado. O migrador aplica tudo em transação e verifica checksums. Repetir após sucesso confirma as versões. O serviço **db não é parado, reconstruído ou recriado** por esses comandos. As duas fontes de ambiente e o overlay de ingestão continuam presentes para preservar os caminhos de imagens do BQ.

Abra Estudar agora, histórico e BQ/imagens. A recomendação deve ser automática sem cadastro obrigatório; confirme a agenda somente se quiser uma duração baseada nela. Faça ensaios de escrita na cópia descartável, não crie estudos fictícios no banco pessoal. Se o navegador mantiver assets antigos da PWA, recarregue após concluir qualquer rascunho ativo.

## Recuperação e limites

Falha no build ou na pré-verificação: containers existentes ainda funcionam. Falha na migration: transação revertida; preserve logs. Se não houve sucesso da migration nem recriação, os containers antigos parados podem ser retomados com o mesmo Compose e `start api frontend`.

Após sucesso de 010, não remova colunas/constraints nem tente backfill para voltar atrás. Preserve os dados e, se necessário, suspenda somente API/frontend enquanto prepara correção compatível. O schema aditivo conserva os campos usados pela Etapa 2, mas executar código antigo deixa de registrar a finalidade das novas sessões; rollback precisa ser avaliado e testado separadamente. Restauração de backup depende de considerar os registros posteriores e não faz parte destes comandos.

As receitas acima tiveram a sintaxe Bash verificada, mas **Docker, PostgreSQL 15 e a implantação real não foram executados nesta etapa**. Não há restrições novas de rede, login, JWT ou autenticação nesta entrega.
