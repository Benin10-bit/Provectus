> **Provectus 2.1:** para instalar ou atualizar com backup e preservação dos dados, siga [COMO_ATUALIZAR.md](COMO_ATUALIZAR.md). As instruções históricas abaixo não substituem esse procedimento. Veja também [MUDANCAS.md](MUDANCAS.md) e [TESTES.md](TESTES.md).

# Provectus 2.1

FastAPI, React/Vite, PostgreSQL 15 e Docker Compose. Design tático original preservado.

- **Já usa o Provectus?** Extraia esta versão em outra pasta e execute `bash atualizar.sh`. Não substitua seu `.env` nem remova volumes.
- **Instalação realmente nova:** `bash instalar.sh`.
- **Uso normal após instalar/atualizar:** `bash start-provectus.sh` na pasta da instalação.

Leia [COMO_ATUALIZAR.md](COMO_ATUALIZAR.md), [MUDANCAS.md](MUDANCAS.md) e [TESTES.md](TESTES.md).

Na interface: **Conteúdos** organiza seu cadastro; **Estudar agora** recebe as cotas do seu ciclo e oferece matéria, assunto e atividade. A sessão integrada salva tempo e questões uma única vez. A lista de revisão usa ações de retorno sem flashcards. Nenhum catálogo fictício é inserido no seu banco.

## Desenvolvimento

Use o lockfile npm (`npm ci`, `npm run dev`, porta 8080) e Python 3.11 (`pip install -r api/requirements-dev.txt`). Configure DATABASE_URL para um PostgreSQL de desenvolvimento. De `api/`, execute `python -m app.migrate`, depois `uvicorn app.main:app --host 127.0.0.1 --port 8000`. O proxy Vite remove apenas o primeiro `/api`, como o Nginx.

API: `/docs`; saúde real do banco: `/health`. A precisão observada mantém o campo legado `ipr_geral` por compatibilidade, com `versao_metrica=precisao_v2`; não há previsão de aprovação.

## Banco de Questões

A migration `api/migrations/004_question_bank.sql` contém as tabelas importadas pelo pipeline. A nova `005_question_bank_user_data.sql` acrescenta somente pastas, listas e respostas. Com o banco existente em execução, aplique as migrations ordenadas antes de abrir o módulo:

```bash
sudo docker compose run --rm api python -m app.migrate
sudo docker compose up -d --build
```

Caso a `004` tenha sido executada manualmente fora do histórico `provectus_migrations`, concilie o registro dessa migration com o DBA antes de executar o migrador; ele valida o checksum e não pula uma tabela já existente por conta própria.

Os arquivos de `question_bank.assets.storage_path` ficam fora do ZIP e do PostgreSQL. Configure `QUESTION_BANK_ASSETS_DIR` no `.env` do host para a **raiz que contém os arquivos relativos** a esses caminhos. O Compose monta essa raiz somente para leitura na API. Por exemplo, se `storage_path` é `assets/a.webp`, o arquivo deve existir em `${QUESTION_BANK_ASSETS_DIR}/assets/a.webp`. O padrão é `./question-bank-assets`. Uma imagem ausente aparece como indisponível, sem impedir o uso da questão. Não copie o `.env` de outro projeto por cima do seu.

A nova entrada **Banco de Questões** abre a busca paginada, seleção de conteúdos de profundidade variável, listas e pastas. A resolução grava alternativas eliminadas e a resposta por lista e questão. O PDF contém o gabarito ao final. O módulo não cria simulados nem modifica as tabelas importadas. Suas respostas e contadores ficam isolados nas tabelas de listas; não entram nos indicadores, metas ou métricas gerais do PROVECTUS. Apenas uma sessão de estudo registrada voluntariamente no fluxo já existente conta nas métricas. O cronômetro de uma sessão iniciada em Estudar agora aparece em outras páginas e leva de volta à sessão. A migração não altera questões já existentes.

## Banco de Questões: consulta e PDF

Veja [ATUALIZACAO_CADERNO.md](ATUALIZACAO_CADERNO.md) para as alterações, validação e instalação da visualização individual e dos dois modos de gabarito no PDF.
