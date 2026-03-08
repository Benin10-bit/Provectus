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