from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..database import get_db
from .. import schemas, services


router = APIRouter(
    prefix="/performance",
    tags=["Performance Acadêmica"]
)

# ==========================================================
# SESSÕES DE ESTUDO
# ==========================================================

@router.post(
    "/sessoes",
    response_model=schemas.SessaoEstudoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar Sessão de Estudo",
    description="""
    Registra uma sessão de estudo contendo:
    - Matéria
    - Assunto
    - Tipo (TEORIA, QUESTOES, REVISAO)
    - Minutos líquidos
    - Nível de foco (1-5)
    - Nível de energia (1-5)

    Esses dados influenciam análises futuras de carga e execução.
    """
)
def criar_sessao(
    payload: schemas.SessaoEstudoCreate,
    db: Session = Depends(get_db)
):
    return services.registrar_sessao_estudo(db, payload)


@router.get(
    "/sessoes",
    response_model=List[schemas.SessaoEstudoResponse],
    summary="Listar Sessões de Estudo",
    description="Retorna histórico paginado das sessões registradas, ordenadas da mais recente para a mais antiga."
)
def listar_sessoes(
    skip: int = Query(0, ge=0, description="Registros a ignorar"),
    limit: int = Query(100, ge=1, le=500, description="Limite máximo de registros"),
    db: Session = Depends(get_db)
):
    return services.listar_sessoes(db, skip, limit)


# ==========================================================
# BLOCOS DE QUESTÕES
# ==========================================================

@router.post(
    "/blocos",
    response_model=schemas.BlocoQuestoesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar Bloco de Questões",
    description="""
    Registra desempenho em um bloco de questões.

    O sistema calcula automaticamente:
    - Percentual de acerto
    - Tempo médio por questão
    - IPR ponderado (usado no dashboard)
    """
)
def criar_bloco(
    payload: schemas.BlocoQuestoesCreate,
    db: Session = Depends(get_db)
):
    return services.registrar_bloco_questoes(db, payload)


@router.get(
    "/blocos",
    response_model=List[schemas.BlocoQuestoesResponse],
    summary="Listar Blocos de Questões",
    description="Retorna blocos registrados ordenados por data."
)
def listar_blocos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    return services.listar_blocos(db, skip, limit)


# ==========================================================
# SIMULADOS SEMANAIS
# ==========================================================

@router.post(
    "/simulados",
    response_model=schemas.SimuladoSemanalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar Simulado Semanal",
    description="""
    Registra um simulado completo.

    Utilizado para comparação estratégica com desempenho diário.
    """
)
def criar_simulado(
    payload: schemas.SimuladoSemanalCreate,
    db: Session = Depends(get_db)
):
    return services.registrar_simulado(db, payload)


@router.get(
    "/simulados",
    response_model=List[schemas.SimuladoSemanalResponse],
    summary="Listar Simulados"
)
def listar_simulados(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    return services.listar_simulados(db, skip, limit)


# ==========================================================
# DASHBOARD PRINCIPAL
# ==========================================================

@router.get(
    "/dashboard",
    response_model=schemas.DashboardResumo,
    summary="Dashboard Estratégico de Performance",
    description="""
    Consolida indicadores estratégicos:

    - Horas líquidas
    - Total de questões
    - Percentual médio
    - IPR geral
    - Tendência (ASCENDENTE, ESTÁVEL, DECLÍNIO)
    - Status da missão
    - Assuntos críticos
    - Status das metas (horas e questões)
    - Recomendação automática

    Permite filtro por período e matéria.
    """
)
def obter_dashboard(
    periodo: str = Query(
        "semana",
        pattern="^(semana|mes|ano|total)$",
        description="Intervalo de análise"
    ),
    materia_id: Optional[UUID] = Query(
        None,
        description="Filtrar por matéria específica (UUID)"
    ),
    db: Session = Depends(get_db)
):
    return services.get_dashboard(
        db=db,
        periodo=periodo,
        materia_id=materia_id
    )


# ==========================================================
# ANALYTICS DETALHADO
# ==========================================================

@router.get(
    "/analytics",
    response_model=dict,
    summary="Analytics Avançado",
    description="""
    Retorna estatísticas detalhadas do período:

    - Horas totais
    - Total de questões
    - IPR médio
    - Assuntos críticos
    - Quantidade de registros

    Pode ser filtrado por matéria.
    """
)
def obter_analytics(
    periodo: str = Query(
        "semana",
        pattern="^(semana|mes|ano|total)$"
    ),
    materia_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db)
):
    return services.get_estatisticas_filtradas(
        db=db,
        periodo=periodo,
        materia_id=materia_id
    )


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

@router.post(
    "/materias",
    response_model=schemas.MateriaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Matéria",
    description="""
    Cria uma nova matéria no sistema.

    Regras:
    - O nome da matéria deve ser único (não pode repetir, ignorando maiúsculas/minúsculas).
    - O peso da prova deve ser maior que zero.
    """,
    tags=["Configurações"]
)
def criar_materia(
    payload: schemas.MateriaCreate,
    db: Session = Depends(get_db)
):
    """
    Cria uma nova matéria.

    Args:
        payload: Dados da matéria (nome e peso_prova).
        db: Sessão do banco de dados.

    Returns:
        MateriaResponse: matéria criada.
    """
    return services.criar_materia(db, payload)


@router.post(
    "/assuntos",
    response_model=schemas.AssuntoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Assunto",
    description="""
    Cria um novo assunto vinculado a uma matéria existente.

    Regras:
    - A matéria referenciada por `materia_id` deve existir.
    - Não é permitido criar dois assuntos com o mesmo nome para a mesma matéria.
    - A semana do ciclo deve estar entre 1 e 4.
    """,
    tags=["Configurações"]
)
def criar_assunto(
    payload: schemas.AssuntoCreate,
    db: Session = Depends(get_db)
):
    """
    Cria um novo assunto.

    Args:
        payload: Dados do assunto (materia_id, nome, semana_do_ciclo).
        db: Sessão do banco de dados.

    Returns:
        AssuntoResponse: assunto criado.
    """
    return services.criar_assunto(db, payload)


@router.get(
    "/materias",
    response_model=List[schemas.MateriaResponse],
    summary="Listar Matérias Ativas",
    tags=["Configurações"]
)
def get_materias(db: Session = Depends(get_db)):
    return services.listar_materias(db)


@router.get(
    "/assuntos",
    response_model=List[schemas.AssuntoResponse],
    summary="Listar Assuntos",
    tags=["Configurações"]
)
def get_assuntos(
    materia_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, le=1000),
    db: Session = Depends(get_db)
):
    return services.listar_assuntos(
        db,
        materia_id=materia_id,
        skip=skip,
        limit=limit
    )


@router.get(
    "/materias/{materia_id}/assuntos",
    response_model=List[schemas.AssuntoResponse],
    summary="Listar Assuntos por Matéria",
    tags=["Configurações"]
)
def get_assuntos_por_materia(
    materia_id: UUID,
    db: Session = Depends(get_db)
):
    return services.listar_assuntos_por_materia(db, materia_id)



# ==========================================================
# CRIAR REDAÇÃO
# ==========================================================

@router.post(
    "/redacoes",
    response_model=schemas.RedacaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova redação",
    description="""
Cria um novo registro de redação.

O sistema automaticamente:

- Calcula a **nota total**
- Identifica a **competência mais fraca**
- Classifica o **status da redação**
- Gera **diagnóstico**
- Gera **recomendação de melhoria**
"""
)
def criar_redacao(
    payload: schemas.RedacaoRequest,
    db: Session = Depends(get_db)
):
    """
    Cria uma nova redação no banco de dados.

    Args:
        payload: Dados enviados pelo usuário contendo
        as notas das competências e informações da redação.

        db: Sessão do banco de dados.

    Returns:
        RedacaoResponse: redação criada com métricas calculadas.
    """

    return services.criar_redacao(db, payload)


# ==========================================================
# BUSCAR REDAÇÃO
# ==========================================================

@router.get(
    "/redacoes/{redacao_id}",
    response_model=schemas.RedacaoResponse,
    summary="Buscar redação",
    description="""
Retorna uma redação específica a partir do ID.

Se a redação não existir, retorna erro **404**.
"""
)
def buscar_redacao(
    redacao_id: str,
    db: Session = Depends(get_db)
):
    """
    Busca uma redação específica.

    Args:
        redacao_id: Identificador da redação.
        db: Sessão do banco de dados.

    Returns:
        RedacaoResponse

    Raises:
        HTTPException(404): caso a redação não exista.
    """

    redacao = services.buscar_redacao(db, redacao_id)

    if not redacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Redação não encontrada"
        )

    return redacao


# ==========================================================
# LISTAR REDAÇÕES
# ==========================================================

@router.get(
    "/redacoes",
    response_model=List[schemas.RedacaoResponse],
    summary="Listar redações",
    description="""
Lista todas as redações cadastradas no sistema.

As redações são retornadas **ordenadas da mais recente
para a mais antiga**, com base na data de escrita.
"""
)
def listar_redacoes(
    db: Session = Depends(get_db)
):
    """
    Retorna todas as redações registradas.

    Args:
        db: Sessão do banco de dados.

    Returns:
        List[RedacaoResponse]
    """

    return services.listar_redacoes(db)


# ==========================================================
# COLAR NO FINAL DE router.py (dentro do arquivo de Performance)
# ==========================================================

# ==========================================================
# RELATÓRIO MENSAL COMPLETO
# ==========================================================

@router.get(
    "/relatorio/mensal",
    response_model=dict,
    summary="📊 Relatório Mensal Completo de Performance",
    description="""
## Relatório Mensal Completo de Performance Acadêmica

Gera um relatório **exaustivo e consolidado** de todos os dados do mês,
com cálculos, métricas derivadas, comparativos e recomendações estratégicas.

---

### 📦 O que está incluído

#### Período de análise
- Datas de início e fim, dias no mês, dias efetivamente estudados.

#### Resumo Geral
- Horas totais líquidas (sessões + blocos + simulados)
- Total de questões respondidas, acertos, erros
- Percentual médio de acerto
- IPR Geral ponderado (70% blocos + 30% simulados)
- Média de questões por dia
- Percentual de dias com estudo no mês

#### Sessões de Estudo
- Distribuição por tipo (TEORIA, QUESTOES, REVISAO): quantidade, minutos, foco médio, energia média
- Distribuição por matéria: tempo dedicado, percentual do total, níveis de foco e energia

#### Blocos de Questões
- Desempenho por matéria: total de blocos, questões, acertos, IPR médio, tempo médio/questão
- Desempenho por assunto: IPR, status (CRÍTICO / FRACO / REGULAR / BOM), semana do ciclo
- Distribuição por dificuldade (1 a 5)

#### Análise de Erros
- Total de erros registrados, quebrado por tipo
- Taxa de erro por distração/pressa vs. conceito/cálculo
- Tendência de erros vs. mês anterior (MELHORANDO / ESTÁVEL / PIORANDO)
- Erros por bloco (atual vs. mês anterior)

#### Simulados Semanais
- Detalhamento de cada simulado: percentual de acerto, IPR, tempo médio por questão
- Nível de ansiedade, fadiga e qualidade do sono registrados
- Desempenho por matéria dentro de cada simulado (quando disponível)

#### Provas Oficiais
- Todas as provas registradas no período, com nota total, tempo e estado mental
- Desempenho por matéria (quando disponível)

#### Redações
- Lista de todas as redações com notas por competência
- Estatísticas consolidadas: nota média, mín, máx
- Média por competência (1 a 5)
- Competência mais fraca mais recorrente no mês
- Distribuição de status (crítica, fraca, regular, boa, muito_boa, excelente)
- Evolução da nota ao longo do mês

#### Estado Mental
- Nível de foco médio (sessões), energia média (sessões)
- Nível de confiança médio (blocos)
- Ansiedade, fadiga e qualidade do sono médios (simulados)

#### Comparativo com Mês Anterior
- Variação absoluta e percentual de: horas, questões, percentual de acerto, IPR, redações
- Labels de tendência (↑ / → / ↓) para cada métrica

#### Projeção de Fechamento *(apenas para o mês atual)*
- Média diária atual de horas e questões
- Projeção do total ao fim do mês com base na média
- Indicador `on_track` para meta de horas (88h) e questões (1400)
- Horas e questões necessárias por dia para bater as metas

#### Score de Consistência
- Score 0–100 baseado em % de dias estudados com penalidade por variação
- Classificação: EXCELENTE / BOA / REGULAR / IRREGULAR
- Maior sequência de estudo contínuo (streak)
- Maior sequência sem estudo
- Desvio padrão de horas/dia e questões/dia

#### Melhor e Pior Dia do Mês
- Data, dia da semana, horas, questões, percentual de acerto e IPR do dia

#### Correlações
- Coeficiente de Pearson entre: foco × IPR, sono × acerto, ansiedade × taxa de erro
- Baseado nos dados do mês (requer mínimo de 3 pontos por par)

#### Balanceamento de Matérias
- Para cada matéria: peso na prova, % de tempo dedicado, % de questões respondidas, IPR
- Classificação por alinhamento peso×tempo: EQUILIBRADA / SUBINVESTIDA / SUPERINVESTIDA

#### Recomendações Estratégicas
- Lista priorizada (CRÍTICA / ALTA / MÉDIA / BAIXA) de ações concretas
- Baseada automaticamente em todos os indicadores do mês:
  IPR, consistência, assuntos críticos, balanceamento, erros, volume e redações

---

### 📌 Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `mes`     | int  | mês atual | Mês de referência (1–12) |
| `ano`     | int  | ano atual | Ano de referência (ex: 2025) |

---

### ⚠️ Observações
- A **projeção de fechamento** só é calculada para o mês atual.
  Para meses passados, os valores de projeção refletem o realizado.
- As **correlações** requerem ao menos 3 pares de dados por dimensão.
  Se insuficientes, o campo retorna `null`.
- O **IPR** é calculado com base na fórmula interna:
  `(precisão × peso) + (velocidade normalizada × peso) - penalidades`.
""",
    tags=["Relatórios"],
)
def obter_relatorio_mensal(
    mes: int = Query(
        default=None,
        ge=1,
        le=12,
        description="Mês de referência (1 = Janeiro ... 12 = Dezembro). Padrão: mês atual.",
    ),
    ano: int = Query(
        default=None,
        ge=2000,
        le=2100,
        description="Ano de referência (ex: 2025). Padrão: ano atual.",
    ),
    db: Session = Depends(get_db),
):
    """
    Gera o relatório mensal completo de performance acadêmica.

    Se `mes` ou `ano` não forem informados, usa o mês e ano atuais.

    Retorna um JSON com todas as seções descritas na documentação acima.
    """
    from datetime import datetime

    agora = datetime.utcnow()
    mes_ref = mes if mes is not None else agora.month
    ano_ref = ano if ano is not None else agora.year

    return services.gerar_relatorio_mensal(db=db, mes=mes_ref, ano=ano_ref)