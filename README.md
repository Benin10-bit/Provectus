# PROVECTUS

FastAPI, React/Vite, PostgreSQL 15 e Docker Compose. Sistema de estudos com Banco de Questões separado das métricas.

**Atualização desta entrega:** substitua os arquivos na instalação existente, preservando `.env`, `.env.ingestion` e as imagens. Execute `sudo bash atualizar.sh` na pasta do Compose. O script reconstrói a aplicação e aplica as migrations; não copia arquivos de outra pasta e não remove volumes. Veja a seção Construtor de listas ao final deste README.

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


## Atualização dos filtros do banco de questões

- Bancas e dificuldades permitem várias escolhas simultâneas. Nenhuma seleção significa todas. Dentro de cada grupo basta corresponder a uma opção; os grupos são combinados entre si.
- **Excluir já respondidas** remove da busca e das novas listas as questões respondidas, certas ou erradas, em qualquer lista ou avulsamente. Abrir uma questão, cortar alternativas ou adicioná-la a uma lista não marca uma resposta.
- A migration **006_question_bank_solved.sql** recupera as respostas completas das listas existentes. Após a atualização, excluir uma lista não apaga a marca de questão respondida.
- Tentativas avulsas anteriores e respostas de listas já excluídas não podem ser recuperadas, porque a versão anterior não mantinha esse histórico.
- A opção é desmarcada por padrão, pode ser removida a qualquer momento e permanece ao voltar aos resultados. Os dados continuam exclusivos do banco de questões; não alimentam as métricas do PROVECTUS.

Substitua os arquivos do projeto, preservando seu `.env` local e a pasta de imagens. Na pasta que contém o Compose, execute:

```bash
sudo docker compose build api frontend
sudo docker compose up -d db
sudo docker compose run --rm api python -m app.migrate
sudo docker compose up -d api frontend
```

A migration 006 é necessária antes de responder questões ou usar a exclusão de respondidas. Ela cria apenas o histórico do banco de questões; não reimporta questões nem modifica os registros de estudo.

## Filtro por acertos e erros

Em **Explorar → Resultado**, escolha **Apenas as que acertei** ou **Apenas as que errei**. A busca e a criação de listas usam a correção mais recente registrada de cada questão, inclusive avulsa. Uma nova tentativa pode mudar a questão de grupo. Reabrir uma resposta antiga da mesma lista não sobrescreve uma correção posterior.

O filtro de resultado e **Excluir já respondidas** são alternativas: selecionar um resultado desmarca a exclusão; ativar a exclusão volta o resultado para Todos. Bancas, dificuldades, conteúdos e busca continuam combináveis.

Aplique a migration **007_question_bank_results.sql** usando os mesmos comandos de atualização acima. A migration 006 permanece intacta. A 007 recupera a última correção disponível das listas existentes; tentativas avulsas anteriores a esta atualização tinham somente a marca de respondida, sem resultado salvo, e precisam de uma nova resposta para entrar no filtro de acertos/erros. Questões sem correção conhecida não aparecem em nenhum dos dois grupos.

## Construtor de listas — composição por hierarquia

A área de criação agora fica acima dos resultados de **Explorar**. Nome, total, matérias e filtros bastam para uma lista automática. **Personalizar composição** abre as cotas por matéria e, ao expandir um ramo, por cada nível real do conteúdo.

- **Automática:** as quantidades variam aleatoriamente, respeitando a disponibilidade e as cotas internas já definidas. Cada grupo elegível participa com pelo menos uma questão quando o orçamento daquele nível permite; o restante é sorteado com chances iguais entre os grupos que ainda têm capacidade.
- **Personalizada:** informe cotas fixas. Um ramo com quantidade **AUTO** recebe parte do restante. O modo de distribuição de cada ramo é independente do modo entre matérias.
- **Completar restante em AUTO** preserva cotas positivas e libera os ramos selecionados com cota zero para receber o saldo. É preciso manter pelo menos um ramo AUTO se as cotas fixas não fecham o total.
- **Sortear distribuição** apresenta cotas concretas sem escolher as questões. **Ajustar quantidades sorteadas** transforma esse resultado em cotas editáveis; ele permite sortear matérias primeiro e personalizar conteúdos depois.
- A composição confirmada permanece estável até mudar total, filtros, seleção ou cotas, ou pedir novo sorteio. Criar usa exatamente essas quantidades, valida novamente a disponibilidade e sorteia questões distintas em cada grupo. Questões de um ramo pai não se repetem nos seus descendentes: os grupos finais são partições disjuntas.
- **Embaralhada** é a ordem padrão; **Agrupar por matéria/conteúdo** mantém os grupos juntos. Depois de criar, questões e ordem permanecem gravadas.
- Bancas, dificuldades, conteúdo, texto do enunciado, exclusão de respondidas e acertos/erros valem tanto para a disponibilidade quanto para o sorteio.
- Os metadados de criação são armazenados apenas nas listas novas. Listas antigas continuam sem essa informação e mantêm seus resultados, questões, ordem, resolução, exportação e exclusão.

O backend agrega a disponibilidade em uma consulta. A seleção usa uma consulta com ranking aleatório por grupo, seguida de inserção conjunta. A criação é transacional; falhas não deixam listas incompletas. Uma trava breve durante a criação impede que importação ou novas respostas mudem os filtros entre a validação e o sorteio.

### Atualizar esta versão

Esta entrega usa a migration aditiva **008_question_bank_composition.sql**, sem modificar as migrations anteriores. Substitua os arquivos do projeto preservando `.env`, `.env.ingestion` e as imagens. O `atualizar.sh` desta versão incorpora a correção que carrega os dois arquivos de ambiente em todos os comandos, valida o diretório das imagens, reconstrói a aplicação e aplica as migrations:

```bash
sudo bash atualizar.sh
```

O script deve estar na instalação atual, junto ao Compose; ele atualiza os containers a partir dos arquivos que você já substituiu. Não copia arquivos de outra pasta. As referências históricas no início deste README ao instalador por manifesto não se aplicam a esse script.

### Validação e limites

A distribuição foi exercitada com múltiplos seeds e testes de soma exata, capacidades, cotas, níveis mistos, hierarquia profunda e grupos sem disponibilidade. Os testes também cobrem seleção de questões, filtros, rollback, estabilidade da composição confirmada e estados da interface. O módulo não escreve em tabelas de sessões, blocos ou métricas do PROVECTUS.

Neste ambiente, a execução com seu PostgreSQL populado e a inspeção visual em navegador real não estão disponíveis. A seleção SQL foi testada com dados isolados e a sintaxe PostgreSQL da migration foi verificada. O limite de criação permanece em 1.000 questões por lista; a hierarquia é recursiva, com até 12 segmentos por caminho, incluindo a matéria.
