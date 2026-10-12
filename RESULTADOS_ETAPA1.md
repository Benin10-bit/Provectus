# Etapa 1 — Correções e validação

Escopo concluído: A01, A05, A13, A17 e regressões A21. Nenhuma migration, alteração de Docker/rede, autenticação ou novo recomendador. Nenhum acesso ao banco real.

## Correções

| Item | Arquivos principais | Comportamento após correção |
|---|---|---|
| A01 | `question_ingestor/src/question_ingestor/importing/postgres.py` | Captura a exceção original; marca FAILED quando possível; falhas de status/fechamento entram como notas sem substituir a causa; documentos e contagens confirmados permanecem |
| A05 | `api/app/services.py`, `frontend/src/pages/RelatorioMensalPage.tsx` | Tendência compara respostas erradas / questões nos trechos equivalentes; classificação aparece separadamente; ausência de classificação não vira melhora |
| A13 | `api/app/question_bank.py` | Nomes de pastas/listas são aparados antes da validação; vazio retorna 422 em português; espaços internos e movimentos sem renomeação preservados |
| A17 | `frontend/package.json`, `frontend/package-lock.json`, `README.md` | Node >=22.12.0 declarado; somente engine raiz do lock mudou, sem atualizar dependências ou imagens |

A05 preserva os campos existentes: `total_erros_registrados` e `erros_por_bloco_*` continuam descrevendo classificações. Novos campos informam erros/questões observados, taxas, cobertura de classificação e contexto. Sem questões, a taxa é `null`; com questões e nenhum erro, é zero. Comparação exige 20 questões/2 blocos em cada trecho e usa tolerância de 5 pontos percentuais; são heurísticas descritivas, não testes estatísticos ou prova de aprendizagem. Classificação histórica acima dos erros observados é sinalizada, nunca corrigida automaticamente.

## Comandos realmente executados e resultados

Ambiente: Python 3.12.14; API em ambiente virtual externo ao projeto, com `api/requirements-dev.txt`; ingestor com PyMuPDF 1.26.6/Pillow 12.3.0; Node 24.19.0/npm 11.9.0. A execução Python 3.11 dos containers não foi realizada.

Na pasta `api/`, o interpretador utilizado foi `/workspace/scratch/923425e78244/etapa1/test-env/bin/python`:

```bash
DATABASE_URL=sqlite:// PYTHONDONTWRITEBYTECODE=1 /workspace/scratch/923425e78244/etapa1/test-env/bin/python -m pytest -q -p no:cacheprovider tests/test_report_error_trend.py tests/test_question_bank_names.py
DATABASE_URL=sqlite:// PYTHONDONTWRITEBYTECODE=1 /workspace/scratch/923425e78244/etapa1/test-env/bin/python -m pytest -q -p no:cacheprovider tests
```

- Regressões focadas: **37 aprovadas**.
- Suíte completa de API: **131 aprovadas**; SQLite descartável/fixtures, incluindo os contratos HTTP. Avisos de depreciação não impediram aprovação.

Na raiz do projeto:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=question_ingestor/src /workspace/scratch/923425e78244/etapa1/test-env/bin/python -m unittest discover -s question_ingestor/tests -p test_import_failures.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=question_ingestor/src python -m unittest discover -s question_ingestor/tests -q
```

- A01 focado: **9 aprovados**, com modelo transacional em memória e exceções/status/contagens verificados.
- Suíte final do ingestor: **87 casos, 86 aprovados e 1 não executado**. O caso opt-in PostgreSQL é pulado sem `PROVECTUS_TEST_DATABASE_URL`; não foi apresentado como aprovado. A suíte também foi exercitada antes da inclusão desse caso, com 86 aprovações e dependências exatas do ingestor.

Na pasta `frontend/`:

```bash
npm ci --no-audit --no-fund
npm run test -- src/test/reportErrors.test.tsx src/test/requestNoContent.test.ts
npm test
npm run build
```

- Instalação pelo lock: **aprovada**, repetida após alinhar a engine.
- Frontend focado: **8 aprovados**.
- Frontend completo: **70 aprovados em 19 arquivos**.
- Build: **aprovado**, incluindo `npm run typecheck` e geração PWA. O aviso de tamanho de bundle não foi tratado como erro ou motivo para refatoração fora de escopo.
- Sintaxe dos arquivos Python verificada por AST. Contratos/versões do lock e arquivos alterados comparados com o ZIP de entrada.

## Reprodução local e PostgreSQL

Use um ambiente virtual de teste, com as dependências de desenvolvimento indicadas no README, substituindo o caminho do interpretador acima pelo do seu ambiente. Nunca aponte testes para o banco real. Os testes normais da API usam SQLite e os do importador usam fixtures; eles não comprovam comportamento PostgreSQL completo.

Para exercitar commits reais de A01, há `question_ingestor/tests/test_import_postgresql.py`. Ele só aceita o banco **provectus_etapa1_test** sem schema `question_bank` pré-existente; cria e remove apenas suas tabelas de teste. A seleção/extração é simulada, enquanto jobs, transações, rollback do documento falho e contagens usam PostgreSQL real. Não é teste de todo o pipeline de importação.

Na raiz de uma cópia do projeto, com o Python de teste e `question-ingestor[postgresql]` instalados, execute este bloco Bash. Ele cria um servidor independente, com dados temporários em memória e credenciais fictícias de teste. Não usa Compose, banco ou volumes da instalação:

```bash
(
  set -euo pipefail
  etapa1_pg_id=$(sudo docker run --rm -d \
    -e POSTGRES_DB=provectus_etapa1_test \
    -e POSTGRES_USER=provectus_test \
    -e POSTGRES_PASSWORD=etapa1_teste_descartavel \
    --mount type=tmpfs,destination=/var/lib/postgresql/data \
    -p 127.0.0.1::5432 postgres:15-alpine)
  trap 'sudo docker stop "$etapa1_pg_id" >/dev/null' EXIT
  for tentativa in {1..30}; do
    if sudo docker exec "$etapa1_pg_id" pg_isready -U provectus_test -d provectus_etapa1_test >/dev/null 2>&1; then break; fi
    sleep 1
  done
  sudo docker exec "$etapa1_pg_id" pg_isready -U provectus_test -d provectus_etapa1_test
  etapa1_pg_endereco=$(sudo docker port "$etapa1_pg_id" 5432/tcp)
  etapa1_pg_porta=${etapa1_pg_endereco##*:}
  PROVECTUS_TEST_DATABASE_URL="postgresql://provectus_test:etapa1_teste_descartavel@127.0.0.1:$etapa1_pg_porta/provectus_etapa1_test" \
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=question_ingestor/src \
    python -m unittest discover -s question_ingestor/tests -p test_import_postgresql.py -v
)
```

Esse bloco PostgreSQL **não foi executado aqui**: Docker e servidor PostgreSQL não estão disponíveis. Não o adapte para produção. Ele destrói somente o container descartável que acabou de criar ao terminar.

## Limitações diretamente relacionadas

- Containers de produção, imagens Docker/Python 3.11 e transações PostgreSQL reais permanecem não verificados neste ambiente; o teste opt-in e comandos acima permitem conferência local.
- Backup real de banco e assets permanece **pendente de confirmação pelo proprietário** antes de aplicar a atualização.
- Jobs históricos PROCESSING não são reconciliados automaticamente. Se FAILED não puder ser gravado, a exceção original informa o job em uma nota; verificar manualmente conforme `ATUALIZACAO_ETAPA1.md`.

Não há bloqueador conhecido nos testes executados. As limitações acima não foram tratadas como aprovações fictícias.
