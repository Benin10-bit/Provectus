# PROVECTUS — Resultados da Etapa 2

Base: ZIP final da Etapa 1, SHA256 `7a836b34d7d7730e7c80c5d0db30611b582137d236a033b11788b7560cb5a728`. O projeto completo e todas as correções anteriores foram preservados. Nenhum banco, container ou volume de produção foi acessado.

## A02 — Dificuldade opcional e origem explícita

A dificuldade ausente fica `NULL`; selecionar 3 continua gravando 3. O registro integrado e o formulário independente oferecem seleção opcional, iniciando em “Não informada”. Criação, edição, histórico e serialização aceitam valores desconhecidos.

A nova coluna opcional `dificuldade_informada` distingue valores novos explicitamente escolhidos (`true`), ausência (`false`) e origem histórica desconhecida (`NULL`). A migração não reclassifica valores antigos. Comparações de mudança entre pares de blocos exigem dificuldade conhecida, igual e explicitamente informada em todos os blocos. Precisão agregada e distribuição descritiva por dificuldade continuam disponíveis; não constituem comparação controlada de dificuldade. O editor permite confirmar voluntariamente um valor histórico, inclusive 3, sem mudar seu número.

Arquivos: `api/app/models.py`, `schemas.py`, `planner.py`, `services.py`, `study_analysis.py`; tipos, captura, formulário independente, editor, histórico e relatório no frontend.

## A09 — Tempo líquido separado do tempo das questões

`segundos_exatos`/`minutos_liquidos` continuam representando a sessão inteira. `tempo_total_segundos` do bloco passa a representar o tempo específico de resolução, opcional. Um único campo em minutos aparece junto às questões da sessão; não há segundo cronômetro. Tempos negativos, zero e resolução superior à sessão são recusados. Blocos independentes mantêm seu tempo próprio e sua contribuição única às horas; quando a duração está ausente, horas somam apenas medidas conhecidas e a interface informa a incompletude.

A coluna opcional `tempo_questoes_informado` qualifica a origem. Blocos integrados históricos conservam o tempo numérico original, mas, sem confirmação explícita, ficam fora de velocidade, média de tempo, orientações por ritmo e calibração semanal. Isso se aplica também a sessões históricas rotuladas QUESTOES: o rótulo não demonstra tempo exclusivamente de resolução. Tempos positivos de blocos históricos independentes mantêm a semântica do fluxo próprio. Essa inferência pela ausência de vínculo não comprova o método de medição; não há metadado para reconstituí-lo retrospectivamente.

A média de tempo do relatório usa somente questões dos blocos com tempo adequado; retorna `NULL` se nenhum bloco for elegível e expõe `questoes_com_tempo` e `blocos_com_tempo`. Tempo desconhecido não vira zero por questão. Uma sessão de 60 minutos com 10 minutos de questões soma 60 minutos de estudo, preserva 600 segundos no bloco e calcula 60 segundos por questão para 10 questões.

Editar uma sessão não sobrescreve o tempo do bloco; editar o bloco não sobrescreve a duração da sessão. Reduzir a sessão abaixo de um tempo específico confirmado é recusado antes de qualquer alteração. Edições de outros campos não qualificam automaticamente números antigos. Reenvios idênticos, inclusive hashes anteriores à Etapa 2, preservam idempotência e não duplicam registros.

Arquivos: `api/app/models.py`, `schemas.py`, `planner.py`, `metrics.py`, `services.py`, `goals.py`, `block_guidance.py`, `study_analysis.py`; captura, editor, tipos, histórico, metas e relatório no frontend.

## A06 — Referência persistida e política compartilhada

`goals.period_projection` atende dashboard, relatório mensal e projeções exibidas nas metas. Mês = 4 × referência semanal; ano = 48 × referência semanal. Taxas de acerto não são multiplicadas. Os números 25h e 200 questões são exemplos de testes, não novas configurações do usuário.

A referência vem da configuração existente: soma integral dos minutos diários e meta manual de questões; sem meta manual, usa percentual de prática e minutos por questão configurados, com o arredondamento existente em grupos de 5. A calibração empírica continua orientando a meta efetiva semanal, mas não recalibra a referência de projeção a cada semana. Semanas parciais, reduções, pausas e meta de questões válida só para a semana atual não mudam a referência.

A primeira leitura registra a referência com a data real de observação. Alterar a configuração para próximas semanas, ou salvar questões com “Usar também nas próximas semanas”, agenda a nova referência para a segunda-feira seguinte. Até lá, a projeção conserva a referência vigente. Não existe edição automática por desempenho. O histórico dessas referências reside no JSON já existente de `tb_config_metas`, em `_referencias_projecao`; não foi criada uma nova tabela de metas. Fotografias existentes em `tb_semana_metas` permanecem preservadas.

Para um mês passado, o relatório usa a última referência cuja observação e vigência ocorreram até o fechamento daquele mês, identificada como projeção de planejamento, com sua data. Não afirma que essa projeção era a soma de metas semanais efetivas. Meses anteriores ao início desse registro ficam com informação indisponível (`NULL`); os snapshots antigos não são reinterpretados para fabricar uma referência. Uma referência observada no meio do mês é identificada pela data, sem presumir vigência desde o primeiro dia.

Dashboard e relatório do mês atual usam a mesma referência e fórmula. Metas semanais por matéria existentes são preservadas; para mês/ano não são inventadas metas individuais a partir das cotas da semana. O período Total não recebe meta acumulada. Projeções não geram dívida, mudança de missão ou cobrança diária automática. Redações conservam a convenção de projeção anteriormente exibida, agora pela referência estável.

Arquivos: `api/app/goals.py`, `metrics.py`, `services.py`, `schemas.py`; `frontend/src/lib/goals.ts`, `DashboardKpis.tsx`, `PeriodGoals.tsx`, `WeeklyGoals.tsx`, `GoalsPage.tsx`, `RelatorioMensalPage.tsx`.

## Migração

Arquivo novo: `api/migrations/009_bloco_medidas_opcionais.sql`.

- Remove somente `NOT NULL` de dificuldade e tempo do bloco.
- Acrescenta duas colunas booleanas opcionais de proveniência.
- Acrescenta validação das medidas com `NOT VALID`, preservando linhas antigas. Linhas novas/editadas respeitam o contrato.
- Não executa `UPDATE`, backfill, exclusão, alteração de IDs ou reimportação.
- As migrações 001–008 e seus checksums foram preservados byte a byte.
- A persistência de referências usa o JSON existente e não exige migração adicional.

O teste PostgreSQL aplica 001–008 em banco vazio, insere um registro representativo da Etapa 1, aplica 009, verifica todas as colunas antigas e repete o migrador. Também testa escrita nula, idempotência HTTP, restrição de tempo negativo, edição separada dos tempos e persistência de metas entre conexões. Não houve migração em produção.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| API completa com SQLite isolado | 165 aprovados; 6 testes PostgreSQL pulados nesta execução sem DSN |
| Integração PostgreSQL isolado | 6 aprovados, incluindo migração e repetição |
| Importador completo | 86 aprovados; 1 teste PostgreSQL da Etapa 1 pulado sem sua DSN |
| Frontend completo | 75 aprovados em 20 arquivos |
| Typecheck e build do frontend | Aprovados |

Comandos, a partir dos diretórios indicados, em ambiente de testes com as dependências existentes:

```bash
# api/: dependências de requirements-dev.txt; DATABASE_URL não deve apontar a produção.
DATABASE_URL=sqlite:// PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests

# api/: apenas um PostgreSQL descartável VAZIO chamado provectus_etapa2_test.
# A DSN é definida pelo operador no ambiente; o teste verifica nome e ausência de tabelas antes de escrever.
DATABASE_URL=sqlite:// PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_stage2_postgresql.py

# raiz do projeto
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=question_ingestor/src python -m unittest discover -s question_ingestor/tests -q

# frontend/
npm ci --offline --no-audit --no-fund
npm run typecheck
npm run test
npm run build
```

Nesta execução, `python` para API foi o ambiente isolado da Etapa 1 em `/workspace/scratch/923425e78244/etapa1/test-env/bin/python`. A integração recebeu `PROVECTUS_STAGE2_TEST_DATABASE_URL` de um PostgreSQL novo iniciado por `pgserver`, fora do projeto, sem acesso a dados pessoais. O helper não faz parte do aplicativo ou de suas dependências. O teste está incluído para futura reprodução em PostgreSQL 15.

Ambiente efetivamente verificado: Python 3.12.14, PostgreSQL 16.2, Node 24.19.0, npm 11.9.0 e dependências do projeto mantidas. O importador utilizou PyMuPDF 1.26.6/Pillow 12.3.0. A instalação inicial de dependências e os testes HTTP ficaram bloqueados pelas restrições de subprocessos/rede; foram executados com autorização automática de ambiente, usando somente recursos isolados.

Falhas iniciais corrigidas: campos novos da projeção eram descartados pelo schema de resposta do dashboard; inclusão no contrato resolveu o problema. Testes da interface foram ajustados ao novo rótulo do tempo opcional. Dois testes novos supunham uma rota de exclusão de blocos inexistente e foram corrigidos ao contrato existente. O fixture PostgreSQL passou a fornecer `criado_em`, como os registros válidos reais. Não restam falhas nos testes executados. Avisos de depreciação das dependências e de tamanho do bundle permanecem sem alteração de escopo.

Não executados: Docker Compose real, imagens Python 3.11/Node do Dockerfile, PostgreSQL 15 e restauração de backup do usuário. A sintaxe da migração é compatível com PostgreSQL 15, mas essa versão precisa da validação local descrita em `ATUALIZACAO_ETAPA2.md`. O teste opcional PostgreSQL do importador não foi repetido nesta etapa; o seu código e teste permaneceram idênticos.

## Preservações e limites

A01/A05/A13/A17 e seus testes permanecem. Banco de Questões, seus arquivos e suas métricas continuam separados do dashboard. Docker Compose, Dockerfiles, dependências, ciclo e identidade visual foram preservados. Não foram implementados A03, A04/A24, autenticação ou restrições de rede. Valores antigos não confirmados podem reduzir a amostra de comparação; isso é deliberado para evitar conclusões baseadas em medidas de origem desconhecida. Não existe endpoint de exclusão de blocos nesta versão; a etapa não acrescenta um novo.

A implantação depende de backup validado do banco e dos assets e das instruções de migração abaixo. Não presuma que esse backup foi realizado. Para esta etapa, use `ATUALIZACAO_ETAPA2.md`; o guia da Etapa 1 fica apenas como registro da entrega anterior.
