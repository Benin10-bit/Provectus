# Executar a ingestão e revisar localmente

Este programa é isolado do Provectus. Usa Python 3.11+, PyMuPDF, Pillow e SQLite. Não acessa internet durante a extração e não adivinha gabaritos. Não existe limite de tamanho de enunciado.

## 1. Instalar

Extraia o ZIP. No terminal, entre na pasta que contém `pyproject.toml`:

```bash
cd question_ingestor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Se `venv` não estiver disponível no seu Zorin, instale o pacote `python3-venv` pelo gerenciador do sistema. Em outro terminal, ative novamente o mesmo ambiente antes de executar os comandos.

## 2. Conferir a hierarquia

A raiz deve ser a pasta que contém as matérias, não uma matéria isolada. Nomes e acentos são preservados; underscores não são convertidos nem interpretados semanticamente.

```bash
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging" --dry-run
```

Confira `/home/beni/question_bank_staging/hierarchy_report.json`. O primeiro diretório é a matéria; os demais, mais o nome do PDF, formam `content_path`. Apenas duplicações adjacentes são removidas. `lista-questoes-123.pdf` é genérico e não acrescenta conteúdo. PDF diretamente na matéria é válido. PDF diretamente na raiz fica sem matéria, com aviso; não há inferência.

O dry-run não extrai questões nem abre PDFs. A descoberta ignora symlinks, arquivos ocultos e a própria saída. O relatório mostra quantos foram encontrados e selecionados. Configure `generic_filename_patterns` e `discovery_ignore_directories` em JSON se necessário.

## 3. Testar cinco e conferir

```bash
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging" --limit 5
```

Abra `reports/global.md` e a auditoria de cada PDF em `documents/<sha256>/audit.html`. O JSONL de cada documento fica em `documents/<sha256>/data/staging/questions.jsonl`. O banco operacional global é `staging.db`, na raiz da saída.

## 4. Executar o acervo completo

```bash
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging"
```

O programa é sequencial e libera o PDF atual antes de iniciar o próximo. Não consolida um JSONL gigante. O banco global permite consultar todas as questões. Não há deduplicação global de questões nesta versão.

Use Ctrl+C para interromper. Depois execute o mesmo comando: DONE íntegros são pulados; PROCESSING abandonado e INTERRUPTED são retomados. A retomada é por documento; um PDF interrompido pode precisar ser reprocessado usando raw compatível. Não remova arquivos enquanto um job estiver em execução.

## 5. Falhas e reprocessamento

```bash
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging" --retry-failed
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging" --materia "fisica" --limit 5
python -m question_ingestor batch "/home/beni/PDFs" --out "/home/beni/question_bank_staging" --path-prefix "fisica/hidroestatica" --force
```

`--limit` seleciona os primeiros N caminhos em ordem determinística, depois dos filtros; inclui os que forem SKIPPED. `--retry-failed` tenta novamente falhas anteriores, além de processar novos/alterados. `--force` reprocessa os selecionados e preserva correções manuais separadas. Evite `--force` sem filtro se não quiser reprocessar tudo.

Na versão 0.2.3, fontes com `CIDSystemInfo` auxiliar ilegível podem ser reparadas somente se todas as referências forem exclusivamente da fonte, houver uma referência canônica intacta e o texto nativo permanecer idêntico. Os metadados das outras fontes não são alterados. Esta correção alcança PDFs anteriormente FAILED; o fingerprint dos documentos DONE continua compatível, evitando reprocessamento de todo o acervo. Execute com `--retry-failed`, sem `--force` global. O SQLite global usa journal tradicional e verifica a integridade também depois de fechar e reabrir o banco.

Antes de retomar uma saída existente, faça uma cópia de segurança do `staging.db` e confira a integridade:

```bash
python - <<'PY'
import sqlite3
p='/home/beni/question_bank_staging/staging.db'
with sqlite3.connect(f'file:{p}?mode=ro', uri=True) as db:
    print(db.execute('PRAGMA integrity_check').fetchone()[0])
    print('documentos:', db.execute('SELECT count(*) FROM documents').fetchone()[0])
    print('questões:', db.execute('SELECT count(*) FROM questions').fetchone()[0])
PY
```

Se o resultado não for `ok`, não retome nesse diretório e não apague o banco; preserve também eventuais arquivos `staging.db-wal`/`staging.db-shm` e solicite uma recuperação a partir dos bancos por documento. O PDF com falha `SANITIZATION_GRAPHIC_INTEGRITY_FAILURE` exige inspeção da fonte correspondente; esta versão não relaxa a checagem gráfica.

SHA-256 é a identidade. Mudança de bytes produz outro documento, mesmo no mesmo caminho. Versões antigas são mantidas para auditoria, e entram nos totais enquanto permanecerem DONE; não são apagadas automaticamente. PDFs idênticos em vários caminhos têm um documento e várias referências de origem: o primeiro caminho da execução é canônico. Se a hierarquia mudar, ela é atualizada sem reinterpretar o PDF. O global não representa uma sincronização destrutiva: arquivos removidos da entrada continuam no staging.

Ao atualizar da versão 0.2.0 para 0.2.1, execute novamente o comando batch normal para registrar negrito em questões antigas; a versão alterada do parser causa reprocessamento, sem exigir `--force`. O raw compatível é reutilizado. Confira overrides/decisões humanas que o editor sinalizar como incompatíveis após a mudança de conteúdo base. Na saída, consulte `statement.segments` e `alternativas[].segments`: trechos nativamente negritados têm `bold: true`. Campos de texto simples preservam as palavras, sem marcação HTML.

## 6. Revisar

Pare o batch antes de abrir o editor. Um lock do sistema impede dois escritores; após crash, o lock é liberado automaticamente.

```bash
python -m question_ingestor review "/home/beni/question_bank_staging"
```

Abra `http://127.0.0.1:8765`. Para abrir automaticamente, acrescente `--open-browser`. Se a porta estiver ocupada, use `--port 8766`. O padrão é exclusivamente local. `--host` permite endereço explícito, mas a ferramenta não tem autenticação e não deve ser publicada na internet.

1. Filtre REVIEW, ERROR, sem gabarito, glifo, overlap, missing formula, corrigidas/aprovadas, matéria, conteúdo ou documento.
2. Use a lista paginada, Anterior/Próxima ou o campo de número original.
3. Compare o conteúdo efetivo à esquerda com os recortes à direita.
4. Abra “Editar campos e trechos de texto”. Cada trecho nativo pode ser editado sem eliminar as imagens entre os trechos. Um glifo ilegível pode receber texto confirmado na fonte. A sugestão Unicode não é aplicada automaticamente.
5. Informe uma observação e clique “Salvar correções”. Letras de gabarito precisam pertencer às alternativas existentes. Campo de gabarito vazio significa null.
6. Para aprovação sem alteração, clique “Aprovar manualmente”. Isso registra a conferência humana, sem alterar OK/REVIEW/ERROR automático.
7. “Reverter ao automático” remove o override daquele campo e registra a reversão. O histórico guarda valores anterior/novo e data.

`automatic_status` e `human_status` são separados. Se uma nova extração alterar o conteúdo base, overrides incompatíveis não serão aplicados; o editor indica a necessidade de reconferência. Correções não alteram PDF, raw, JSONL automático nem recortes. O snapshot `audit.html` também permanece automático. O servidor calcula os valores efetivos a partir do SQLite. Não há editor avançado de fórmulas, crop, reordenação de imagens nem criação de questões.

## 7. Arquivos e consultas

- `staging.db`: documentos, questões, alternativas, segmentos, assets, avisos, jobs, overrides e histórico.
- `batch_manifest.json`: última execução e resumo.
- `hierarchy_report.json`: última seleção de caminhos.
- `reports/global.json` e `global.md`: totais de documentos DONE e problemas, incluindo falhas.
- `documents/<sha256>/report.json`, `report.md`, `metadata.json`, `audit.html`: saídas por PDF.
- `documents/<sha256>/data/raw/`: evidência sanitizada e versionada.
- `documents/<sha256>/data/staging/questions.jsonl`: exportação automática por documento.
- `storage/questions/`, `storage/originals/`: assets globais por hash. Em filesystems com hardlinks, as cópias de auditoria por documento compartilham os mesmos bytes. Sem hardlinks há cópias locais de compatibilidade.
- `logs/technical.log`: traceback, tipo de exceção e documento; sem enunciados. `logs/batch.log`: execução/caminho/duração. Cada PDF também tem seu log técnico quando necessário.

Com o cliente SQLite instalado:

```bash
sqlite3 "/home/beni/question_bank_staging/staging.db"
```

```sql
SELECT relative_path, processing_status, error_code FROM documents
WHERE processing_status <> 'DONE';
SELECT status, COUNT(*) FROM questions GROUP BY status;
SELECT d.materia, d.content_path, COUNT(*) FROM questions q
JOIN documents d ON d.sha256=q.document_sha256
GROUP BY d.materia,d.content_path;
SELECT * FROM review_actions ORDER BY id DESC LIMIT 20;
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

`documents.sha256` é também o document_id lógico; `questions.document_sha256` é a chave estrangeira. O conteúdo histórico da extração fica em `payload_json`; valores efetivos são calculados pelo módulo `review.overrides`.

## 8. Ingestão individual e backup

O comando original continua disponível:

```bash
python -m question_ingestor ingest "/caminho/Capacitores.pdf" --out "/caminho/piloto" --materia "Física" --assunto "Eletrodinâmica" --subassunto "Capacitores"
```

Use uma saída separada para ingestão individual. O editor global usa a saída do batch. Para backup, encerre batch e review e copie a pasta de saída inteira. O batch 0.2.3 usa journal SQLite tradicional e synchronous FULL; não copie apenas o arquivo principal enquanto houver processos escrevendo. PDFs originais devem continuar guardados por você; o programa não os reempacota nem modifica.
