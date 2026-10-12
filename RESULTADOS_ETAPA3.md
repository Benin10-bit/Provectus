# PROVECTUS — Etapa 3: recomendador automático

Entrega de 12/10/2026. Base obrigatória: `PROVECTUS_Etapa2_Corrigido.zip`, SHA-256 `a76578ac334e67aedfc3744b771413bb2361cd5b9b2aaa5699efaf0e5c6142e5`.

A03, A04 e A24 implementados; A21 acompanha o fluxo com testes. Nenhum banco de produção foi acessado. A implantação e o ensaio PostgreSQL continuam separados desta entrega: veja `ATUALIZACAO_ETAPA3.md`.

## Decisão implementada

`api/app/recommender.py` gera candidatos de todas as matérias/assuntos ativos. Escolhe finalidade, atividade, assunto, prioridade, tarefa, explicação e duração quando conhecida. `GET /api/v1/estudos/agora`, orientações acionáveis do dashboard e fila usam esse serviço. As análises descritivas por período continuam com seu próprio escopo; seus resultados não são prova de domínio. Orientações de blocos explicam ajustes para quando aquele assunto for retomado e encaminham a decisão principal a Estudar agora.

- **Avanço:** assunto explicitamente não estudado, exploração de familiaridade desconhecida ou continuidade informada no mesmo assunto. Nenhuma ordem cadastral vira sequência pedagógica.
- **Consolidação:** aplicação ausente após teoria recente ou segunda aplicação com amostra inicial limitada. Recuperação de conteúdo antigo não recebe esse nome para escapar da proteção produtiva.
- **Revisão:** retorno a assunto registrado ou declarado estudado. A tarefa começa por recuperação/tentativa, com correção específica. Questões também podem ter finalidade revisional.
- **Ciclo:** cotas influenciam a comparação global; urgência e espera podem selecionar outra matéria. Cobertura desconhecida fora de um ciclo configurado entra como fallback; aplicação recente ou continuidade explícita fora dele pode competir por motivo pedagógico. Sem ciclo, o recomendador funciona sem cotas fictícias. Metas e ciclo não são reescritos.
- **Desempate:** necessidade da aplicação/continuidade, equilíbrio recente, proporção da cota quando comparável, diversificação/cobertura, contato conhecido e ID estável. Comparações incompletas de cota/data são omitidas; nomes, ordem de cadastro e aleatoriedade não definem currículo.

## Distribuição verificável

Cada sessão concluída conta uma vez, mesmo com bloco vinculado; bloco avulso válido conta uma oportunidade. Finalidades legadas ambíguas permanecem desconhecidas (U); REVISAO explícita pode contar em R. Respostas do BQ, visualizações, aceitação, pausa, rascunho e simulado global não alimentam os contadores.

Cada retorno tem origem estável (contato, declaração, revisão anterior ou ação programada). `b` conta atividades A/C/U concluídas desde sua elegibilidade; revisão de outro assunto não o zera. A espera atravessa semanas e a janela descritiva de 14 dias. O fim de um episódio de distribuição não apaga dificuldades observadas.

| Classe | Evidência | Limite inicial K |
|---|---|---:|
| Manutenção | Contato conhecido, sem recorrência sustentada | 4 |
| Recorrente | Falhas substanciais em dois dias locais distintos, recentes, sem níveis conhecidos conflitantes | 2 |
| Prioritária | Recorrência mais consequência e data de uso próximo explicitamente informadas na ação | 1 |

Quando `b >= K`, o retorno ganha oportunidade efetiva. Entre maduros, maior `b-K` primeiro, depois classe, consequência, ciclo, contato comparável, data de elegibilidade e ID. Backlog e data antiga sozinhos não tornam um assunto urgente.

Nos dias mistos, **duas atividades produtivas conhecidas entre revisões comuns** protegem o avanço. Uma recuperação prioritária pode entrar após uma produtiva quando a revisão anterior não era prioritária; a exceção não se repete indefinidamente. Sem candidato produtivo real, uma revisão pode prevalecer com explicação. Não há revisão diária obrigatória nem preenchimento de uma porcentagem. O teste de 36 conclusões com backlog verifica oportunidades para vários assuntos e ausência da sequência permanente R→A→R→A.

Sábado filtra primeiro: somente revisão de assuntos conhecidos, inclusive diagnóstico sem agendamento. Não exige bloco produtivo entre revisões; não repete automaticamente uma revisão já realizada naquele dia. Ação manual futura permanece futura. Sem assunto conhecido disponível, mostra estado vazio honesto. Domingo usa seleção mista e disponibilidade vigente, sem rotina presumida.

Parâmetros opcionais no ambiente **da API**: `RECOMMENDER_MAINTENANCE=4`, `RECOMMENDER_RECURRING=2`, `RECOMMENDER_PRIORITY=1`, `RECOMMENDER_RECENT_DAYS=14`, `RECOMMENDER_PRODUCTIVE_GAP=2`. Exigem `1 <= priority <= recurring <= maintenance`, janela >=1 e intervalo produtivo >=2. Não é necessário configurá-los para começar; uma variável apenas no `.env` não chega à API sem ser encaminhada pelo Compose. São heurísticas de produto, não constantes científicas.

## Dados incompletos e aprendizagem

Conteúdos oferece indicação opcional “Já estudei”, “Ainda não estudei” ou “Não informado”. Estudo registrado prevalece sobre declaração conflitante. A declaração não cria sessões, datas de estudo, horas, questões ou domínio; removê-la retorna a desconhecido quando não há registro real.

Assunto desconhecido pode receber **avanço exploratório**, começando por uma tentativa breve e seguindo para introdução se necessário. Não exige classificação em massa. No sábado, permanece excluído. Um registro real posterior fornece contato documentado normalmente.

O estado de evidência é separado da realização. Revisão de 40 minutos sem questões atualiza contato, mas não remove baixa precisão. Tentativas substanciais em dias diferentes podem modificar a avaliação; um bloco minúsculo ou apenas um resultado favorável não encerra a dificuldade. Se a dificuldade anterior tinha nível explicitamente conhecido, resultados de nível menor/desconhecido não a eliminam automaticamente. Dificuldade desconhecida não vira 3; velocidade usa somente medidas qualificadas da Etapa 2. Mesmo resultados favoráveis não são chamados de domínio.

Heurísticas locais: tentativa substancial >=10 questões, dois dias distintos, referência descritiva de 70%, recorrência recente em 60 dias; retorno inicial de prática após 1 dia ou de teoria após 7, e nova oportunidade após pelo menos 2 dias da revisão. A elegibilidade não desliza a cada prática adicional; mudar a classe não reinicia a espera. Os números não estimam uma curva científica individual de retenção.

## Disponibilidade e interface

Ajuste opcional de minutos para agora prevalece sobre a agenda. Sem ele, usa janela confirmada/configurada atual e reserva as pausas. Não converte saldo de meta em tempo livre. A configuração antiga idêntica ao seed não é assumida vigente; salvar a agenda a confirma, sem necessidade de fazer isso para começar. Dados incompletos retornam duração desconhecida. Janela explicitamente fechada oferece ajuste excepcional. Referência máxima de 50 minutos, mínimo operacional de 5 para tentativa/correção útil; ambos são heurísticas, sem aumento obrigatório de carga.

`STUDY_TIMEZONE` continua configurável; default da instalação passa a `America/Maceio`. Timestamps históricos permanecem UTC, sem atualização retroativa. A interface consulta novamente a cada minuto/foco, sem consumir oportunidades.

A apresentação é somente leitura. Aceitação e início são identificados no rascunho local; o mesmo clique pode registrar ambos, sem criar sessão no servidor. A conclusão salva finalidade/objetivo/classe com a sessão, pela transação e chave idempotente existentes. Rascunhos antigos continuam válidos, sem finalidade inventada. Uma edição que altera assunto ou tipo invalida a proveniência anterior, conservando o registro. Sessão ativa é retomada; a escolha manual permanece disponível.

## Ajustes explícitos frente à especificação anterior

O prompt da Etapa 3 prevaleceu em três pontos: intervalo produtivo comum de **duas** atividades, em lugar de apenas uma; desconhecidos podem entrar como avanço exploratório; disponibilidade desconhecida mantém recomendação sem duração inventada, inclusive domingo. A garantia revisional respeita esse intervalo reforçado. Não há novo requisito arquitetural, autenticação, filtro de rede, IA integrada ou integração das métricas com BQ.

## Testes executados e limites

Ambiente: Python 3.12.14, Node 24.19.0, npm 11.9.0; dependências das etapas anteriores, sem alteração dos lockfiles.

| Verificação final | Aprovados | Reprovados | Não executados/ignorados |
|---|---:|---:|---:|
| API, serviço e regressões | 210 | 0 | 10 testes PostgreSQL opt-in |
| Frontend, incluindo fluxo de início/retomada/conclusão | 81 | 0 | 0 |
| Importador | 86 | 0 | 1 integração PostgreSQL opcional |
| TypeScript + build Vite/PWA | Concluído | 0 | — |

Comandos realmente executados, a partir da pasta indicada (o Python usado era o ambiente virtual preparado para as etapas anteriores):

```bash
# Raiz do projeto
DATABASE_URL=sqlite:// PYTHONPATH=api python -m pytest -q api/tests --disable-warnings
# frontend/
npm run build
npm test
# question_ingestor/
PYTHONPATH=src python -m unittest discover -s tests
```

Os testes antigos que esperavam escolha prévia da matéria, revisão obrigatória sem maturidade, orientação revisional para assunto desconhecido ou duração dominical herdada foram ajustados à nova especificação. As verificações de métricas, idempotência, nulabilidade, metas e tempo separado foram mantidas. O ensaio de replay histórico constrói o formato da Etapa 2 sem os novos campos, preservando o teste real de compatibilidade.

`api/tests/test_stage3_recommender.py` contém testes com prefixos **R01 a R34**, individualmente executados; não são apenas referências no relatório. R18 também é verificado pelo fluxo real da página em `frontend/src/test/stage3Recommender.test.tsx`.

| Casos | Cobertura executável |
|---|---|
| R01–R05 | Escolha automática, backlog, vários blocos, proteção após R/U, liberação de avanço |
| R06–R11 | Sábado, estado vazio, domingo, pouco tempo, agenda vigente |
| R12–R17 | Evidência insuficiente, A03, episódios, BQ, refresh e ciclo versus recorrência |
| R18–R23 | Retomada de rascunho, mesma decisão no dashboard, ação futura, bloco único, excesso de espera |
| R24–R29 | Espera entre semanas, revisões seguidas, declarações, desconhecidos, sábado com vários retornos |
| R30–R34 | Retenção sem agenda, ID estável, poucos dados, contagem única e declarações conflitantes |
| T01/T02 | R22 e simulação de 36 conclusões com backlog e progresso protegido |
| T03/T04/T05 | R28, R06 e R08; estado vazio também na interface |
| T06/T07 | R13 e teste de melhora consistente, incluindo amostra pequena e nível inferior |
| T08/T09/T10 | R17, R01 e nulabilidade sem velocidade/prioridade fictícia |
| T11/T12 | R16, contabilidade/idempotência e testes de aceitação/retomada no navegador simulado |
| T13/T14/T15 | R15, calendário/fusos, histórico e rascunhos antigos |

Há ainda verificações de parâmetros, exceção urgente documentada, ciclo incompleto e agenda incompleta. Os seis novos testes de frontend preservam IDs, finalidade revisional de questões, rascunho e ausência de gravação antes da conclusão.

**Limitações:** não houve execução de Docker nem de PostgreSQL nesta etapa. A tentativa de iniciar PostgreSQL 16.2 descartável falhou na criação do usuário de sistema; a alternativa com usuário existente também foi bloqueada por permissões do ambiente. Os quatro novos testes `test_stage3_postgresql.py` e seis da Etapa 2 ficaram ignorados na suíte local; não são declarados aprovados. O guia inclui ensaio com PostgreSQL 15 separado, que deve passar antes da implantação. Não houve ensaio visual em navegador real ou banco pessoal; a interface foi verificada por testes de componentes e build. O build mantém aviso de bundle acima de 500 kB; nenhuma otimização ampla foi incluída.

## Integridade e migração

Nova migration: `api/migrations/010_recomendador.sql`. Acrescenta campos anuláveis de familiaridade/data de declaração, finalidade/objetivo/classe da sessão e consequência/data de uso da ação. Não contém UPDATE, DELETE, backfill ou recriação de tabelas. A aplicação continua transacional pelo migrador existente. Os testes PostgreSQL fornecidos verificam 009→010, repetição, preservação dos campos históricos, valores desconhecidos, restrições e conclusão idempotente; sua execução permanece pendente.

A comparação com o ZIP-base confirmou todos os arquivos originais presentes, migrations 001–009 intactas e preservação dos arquivos Docker, dependências, importador e implementação do BQ. Não foram entregues volumes, segredos, dumps, caches, ambientes virtuais ou node_modules. Documentação das etapas anteriores permanece como histórico; o guia desta etapa é a referência de implantação.
