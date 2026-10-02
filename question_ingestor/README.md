# Question Ingestor 0.3.0 — Fênix

Projeto Python isolado: PDFs → raw sanitizado → parser Fênix → rich-content/assets → validação → JSONL e SQLite → revisão humana. Não altera o Provectus.

**Leia [RUNBOOK.md](RUNBOOK.md)** para executar sozinho, incluindo instalação, testes, dry-run, limit, resume, force, revisão e consultas SQL.

Para executar a mesma CLI em um container sob demanda no Compose do Provectus, use o `Dockerfile` e o complemento `docker-compose.ingestion.yml` fornecido separadamente. As instruções de montagem e retomada ficam em `DOCKER_RUNBOOK.md` na raiz do complemento; o container não importa dados para PostgreSQL.

A versão 0.3.0 acrescenta um comando separado `import-ok` com prévia sem escrita e `--apply` explícito. Ele importa somente questões `OK` de documentos `DONE` para o schema `question_bank` do PostgreSQL existente. A migration da API e os passos de backup, teste limitado e rollback estão em `IMPORT_RUNBOOK.md`. O comando `batch` e seu fingerprint de extração permanecem compatíveis com o staging anterior.

```bash
cd question_ingestor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging" --dry-run
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging" --limit 5
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging"
python -m question_ingestor review "/home/beni/question_bank_staging" --open-browser
```

A raiz contém as matérias. A hierarquia usa o primeiro diretório e `content_path[]`, sem classificação semântica. Nomes genéricos e aliases são configuráveis. Extensão PDF é case-insensitive, sem seguir symlinks.

O batch reutiliza `pipeline.ingest`, mantendo o comando individual. Processa um documento por vez; SHA-256, versão do parser e configuração determinam skip/reprocessamento. SQLite global usa transações, journal tradicional e synchronous FULL. Ctrl+C permite retomada por documento. Falhas isoladas são registradas, sem descartar os demais PDFs. Assets regionais íntegros da mesma configuração/documento podem ser reutilizados, com verificação de hashes.

Saída operacional: `OUT/staging.db`, `reports/global.json`, `reports/global.md`, `hierarchy_report.json`, `documents/<sha256>/data/staging/questions.jsonl`, `documents/<sha256>/data/raw/`, auditoria por documento e `storage/` global. A organização interna existente por documento foi preservada.

O editor é local, paginado e sem React. Mantém automático e overrides separados, com histórico, aprovação e reversão. O valor efetivo usa os trechos canônicos de rich-content. Não há editor gráfico avançado nem criação de segmentos para alternativas totalmente vazias. A edição não altera PDF, raw, JSONL automático ou recortes.

**Negrito nativo:** cada trecho de texto guarda `bold: true/false` a partir dos flags do span no PDF; a auditoria e o editor o exibem em negrito. `enunciado` e `texto` das alternativas continuam texto simples integral, enquanto `statement.segments` e `alternativas[].segments` preservam a ênfase. O parser revisado tem outra versão: um batch com a mesma saída reprocessa documentos concluídos com a versão antiga, reutilizando o raw compatível. Overrides/decisões humanas relacionados a uma extração anterior podem exigir reconferência quando o conteúdo base mudar.

Não há limite de caracteres/páginas por questão. Páginas comprovadamente vazias ficam como INFO. Diagnósticos gráficos são associados às páginas afetadas. Gabaritos e glifos não são inventados. REVIEW continua explícito quando a fonte ou extração permanece incerta.

Consulte `BATCH_INTEGRATION_REPORT.md` e `evidence/`. O ZIP de teste contém **quatro**, não cinco PDFs. O pacote de resultados inclui o staging e assets desses quatro arquivos. Os relatórios históricos de Capacitores documentam a versão anterior; suas métricas não são as do lote atual.

Fora do escopo nesta versão: processamento do acervo pelo assistente, deduplicação global, endpoints, frontend, respostas de usuários e integração com desempenho/revisão do Provectus.

## Correção 0.2.3

O reparo conservador do `CIDSystemInfo` aceita PDFs Fênix cujas outras fontes possuam variantes legíveis desse metadado. O batch usa journal SQLite tradicional e confirma a integridade do staging após reabertura. Consulte `RUNBOOK.md` antes de retomar um staging existente.
