from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Literal


# ==========================================================
# MATERIA
# ==========================================================

class MateriaBase(BaseModel):
    nome: str = Field(..., min_length=1)
    peso_prova: float = Field(..., gt=0)


class MateriaCreate(MateriaBase):
    pass


class MateriaResponse(MateriaBase):
    id: UUID
    ativa: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# ASSUNTO
# ==========================================================

class AssuntoBase(BaseModel):
    materia_id: UUID
    nome: str = Field(..., min_length=1)
    semana_do_ciclo: int = Field(..., ge=1, le=4)


class AssuntoCreate(AssuntoBase):
    pass


class AssuntoResponse(AssuntoBase):
    id: UUID
    ativo: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# SESSÃO DE ESTUDO
# ==========================================================

class SessaoEstudoBase(BaseModel):
    materia_id: UUID
    assunto_id: UUID

    tipo_sessao: Literal["TEORIA", "QUESTOES", "REVISAO"]
    minutos_liquidos: int = Field(..., gt=0)

    nivel_foco: Optional[int] = Field(None, ge=1, le=5)
    nivel_energia: Optional[int] = Field(None, ge=1, le=5)

    data: datetime = Field(default_factory=datetime.utcnow)


class SessaoEstudoCreate(SessaoEstudoBase):
    pass


class SessaoEstudoResponse(SessaoEstudoBase):
    id: UUID
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# BLOCO DE QUESTÕES
# ==========================================================

class BlocoQuestoesBase(BaseModel):
    materia_id: UUID
    assunto_id: UUID

    dificuldade: int = Field(..., ge=1, le=5)

    total_questoes: int = Field(..., ge=1)
    total_acertos: int = Field(..., ge=0)

    tempo_total_segundos: int = Field(..., gt=0)
    nivel_confianca_medio: Optional[int] = Field(None, ge=1, le=5)

    data: datetime = Field(default_factory=datetime.utcnow)


class BlocoQuestoesCreate(BlocoQuestoesBase):
    pass


class BlocoQuestoesResponse(BlocoQuestoesBase):
    id: UUID
    percentual_acerto: float
    tempo_medio_por_questao: float
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# ERRO DE QUESTÃO
# ==========================================================

class ErroQuestaoBase(BaseModel):
    bloco_id: UUID
    tipo_erro: Literal[
        "CONCEITO",
        "INTERPRETACAO",
        "CALCULO",
        "DISTRACAO",
        "PRESSA",
        "CONTEUDO_ESQUECIDO"
    ]
    quantidade: int = Field(..., ge=1)


class ErroQuestaoCreate(ErroQuestaoBase):
    pass


class ErroQuestaoResponse(ErroQuestaoBase):
    id: UUID
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# SIMULADO SEMANAL
# ==========================================================

class SimuladoSemanalBase(BaseModel):
    numero_ciclo: int = Field(..., ge=1)
    numero_semana: int = Field(..., ge=1, le=4)

    total_questoes: int = Field(..., ge=1)
    total_acertos: int = Field(..., ge=0)
    tempo_total_segundos: int = Field(..., gt=0)

    nivel_ansiedade: Optional[int] = Field(None, ge=1, le=5)
    nivel_fadiga: Optional[int] = Field(None, ge=1, le=5)
    qualidade_sono: Optional[int] = Field(None, ge=1, le=5)


class SimuladoSemanalCreate(SimuladoSemanalBase):
    pass


class SimuladoSemanalResponse(SimuladoSemanalBase):
    id: UUID
    percentual_acerto: float
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# DESEMPENHO POR MATÉRIA NO SIMULADO
# ==========================================================

class DesempenhoSimuladoMateriaBase(BaseModel):
    simulado_id: UUID
    materia_id: UUID
    total_questoes: int = Field(..., ge=1)
    total_acertos: int = Field(..., ge=0)
    tempo_total_segundos: int = Field(..., gt=0)


class DesempenhoSimuladoMateriaCreate(DesempenhoSimuladoMateriaBase):
    pass


class DesempenhoSimuladoMateriaResponse(DesempenhoSimuladoMateriaBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# PROVA OFICIAL
# ==========================================================

class ProvaOficialBase(BaseModel):
    ano: int = Field(..., ge=2000)
    nota_total: float = Field(..., ge=0)
    tempo_total_segundos: int = Field(..., gt=0)

    nivel_ansiedade: Optional[int] = Field(None, ge=1, le=5)
    nivel_fadiga: Optional[int] = Field(None, ge=1, le=5)
    qualidade_sono: Optional[int] = Field(None, ge=1, le=5)


class ProvaOficialCreate(ProvaOficialBase):
    pass


class ProvaOficialResponse(ProvaOficialBase):
    id: UUID
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# DESEMPENHO POR MATÉRIA NA PROVA OFICIAL
# ==========================================================

class DesempenhoProvaMateriaBase(BaseModel):
    prova_id: UUID
    materia_id: UUID
    percentual_acerto: float = Field(..., ge=0)
    tempo_total_segundos: int = Field(..., gt=0)


class DesempenhoProvaMateriaCreate(DesempenhoProvaMateriaBase):
    pass


class DesempenhoProvaMateriaResponse(DesempenhoProvaMateriaBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# DASHBOARD
# ==========================================================

class DashboardParametros(BaseModel):
    periodo: Literal["semana", "mes", "ano", "total"] = "semana"
    materia_id: Optional[UUID] = None


class DashboardResumo(BaseModel):
    horas_liquidas: float
    total_questoes: int
    percentual_medio: float
    ipr_geral: float
    tendencia: str
    status_missao: str
    assuntos_criticos: List[str]
    status_horas: str
    status_questoes: str
    recomendacao: List[str]


from pydantic import BaseModel
from uuid import UUID


class MateriaResponse(BaseModel):
    id: UUID
    nome: str

    class Config:
        from_attributes = True


class AssuntoResponse(BaseModel):
    id: UUID
    nome: str
    materia_id: UUID

    class Config:
        from_attributes = True


# ==========================================================
# REDAÇÃO
# ==========================================================

class RedacaoRequest(BaseModel):

    tema: str = Field(..., max_length=300)

    eixo_tematico: Optional[str] = None

    tempo_escrita_min: Optional[int] = None

    observacoes: Optional[str] = None

    repertorios: Optional[str] = None

    competencia1: int = Field(..., ge=0, le=200)
    competencia2: int = Field(..., ge=0, le=200)
    competencia3: int = Field(..., ge=0, le=200)
    competencia4: int = Field(..., ge=0, le=200)
    competencia5: int = Field(..., ge=0, le=200)


class RedacaoResponse(BaseModel):

    id: UUID

    tema: str

    eixo_tematico: Optional[str]

    data_escrita: datetime

    tempo_escrita_min: Optional[int]

    observacoes: Optional[str]

    repertorios: Optional[str]

    competencia1: int
    competencia2: int
    competencia3: int
    competencia4: int
    competencia5: int

    nota_total: int

    status: str

    competencia_mais_fraca: int

    diagnostico: str

    recomendacao: str

    criado_em: datetime

    class Config:
        from_attributes = True


# ==========================================================
# RELATÓRIO MENSAL COMPLETO
# ==========================================================

class PeriodoAnalise(BaseModel):
    """Define o período de análise do relatório."""
    mes_referencia: int = Field(..., ge=1, le=12)
    ano_referencia: int = Field(..., ge=2000, le=2100)
    data_inicio: datetime
    data_fim: datetime
    dias_no_mes: int
    dias_estudados: int


class ResumoGeralRelatorio(BaseModel):
    """Métricas consolidadas de alto nível do mês."""
    horas_totais: float
    total_sessoes: int
    total_blocos: int
    total_questoes_respondidas: int
    total_acertos: int
    total_erros: int
    percentual_acerto_geral: float
    ipr_geral: float
    media_questoes_por_dia: float
    media_minutos_estudo_por_dia: float
    dias_estudados: int
    percentual_dias_estudados: float


class SessaoPorTipo(BaseModel):
    """Distribuição de sessões por tipo."""
    tipo_sessao: str
    quantidade: int
    total_minutos: int
    percentual_do_total: float
    media_foco: Optional[float]
    media_energia: Optional[float]


class SessaoPorMateria(BaseModel):
    """Desempenho de sessões por matéria."""
    materia_id: UUID
    materia_nome: str
    total_sessoes: int
    total_minutos: int
    percentual_tempo: float
    media_foco: Optional[float]
    media_energia: Optional[float]


class BlocoPorMateria(BaseModel):
    """Desempenho de blocos de questões por matéria."""
    materia_id: UUID
    materia_nome: str
    total_blocos: int
    total_questoes: int
    total_acertos: int
    percentual_acerto: float
    tempo_medio_por_questao: float
    ipr_medio: float


class BlocoPorAssunto(BaseModel):
    """Desempenho de blocos por assunto específico."""
    assunto_id: UUID
    assunto_nome: str
    materia_id: UUID
    materia_nome: str
    total_blocos: int
    total_questoes: int
    total_acertos: int
    percentual_acerto: float
    ipr_medio: float
    semana_do_ciclo: int
    status: str


class BlocoPorDificuldade(BaseModel):
    """Distribuição de blocos por nível de dificuldade."""
    dificuldade: int
    total_blocos: int
    total_questoes: int
    total_acertos: int
    percentual_acerto: float
    ipr_medio: float


class ErroPorTipo(BaseModel):
    """Estatísticas de erros categorizados por tipo."""
    tipo_erro: str
    total_ocorrencias: int
    percentual_do_total: float
    blocos_afetados: int


class AnaliseErros(BaseModel):
    """Análise completa de padrões de erro do mês."""
    total_erros: int
    tipos_mais_comuns: List[ErroPorTipo]
    tipos_criticos: List[ErroPorTipo]
    taxa_erro_distencao_pressa: float
    taxa_erro_conceito_calculo: float
    tendencia_erro: str


class SimuladoMensalDetalhe(BaseModel):
    """Detalhamento de cada simulado semanal do mês."""
    simulado_id: UUID
    numero_ciclo: int
    numero_semana: int
    total_questoes: int
    total_acertos: int
    percentual_acerto: float
    tempo_total_segundos: int
    tempo_medio_por_questao: float
    ipr: float
    nivel_ansiedade: Optional[int]
    nivel_fadiga: Optional[int]
    qualidade_sono: Optional[int]
    desempenhos: List[dict]


class MediaEstadoMental(BaseModel):
    """Médias de indicadores de estado mental e bem-estar."""
    nivel_ansiedade_medio: Optional[float]
    nivel_fadiga_medio: Optional[float]
    qualidade_sono_media: Optional[float]
    nivel_foco_medio: Optional[float]
    nivel_energia_medio: Optional[float]
    nivel_confianca_medio: Optional[float]


class ProvaOficialMensal(BaseModel):
    """Prova oficial realizada no mês."""
    prova_id: UUID
    ano: int
    nota_total: float
    tempo_total_segundos: int
    tempo_total_horas: float
    nivel_ansiedade: Optional[int]
    nivel_fadiga: Optional[int]
    qualidade_sono: Optional[int]
    desempenhos: List[dict]


class RedacaoMensal(BaseModel):
    """Redação realizada no mês."""
    redacao_id: UUID
    tema: str
    eixo_tematico: str
    data_escrita: datetime
    tempo_escrita_min: Optional[int]
    nota_total: int
    status: str
    competencia1: int
    competencia2: int
    competencia3: int
    competencia4: int
    competencia5: int
    competencia_mais_fraca: int


class EstatisticasRedacaoMensal(BaseModel):
    """Consolidado de redações do mês."""
    total_redacoes: int
    nota_media: float
    nota_maxima: int
    nota_minima: int
    media_competencia1: float
    media_competencia2: float
    media_competencia3: float
    media_competencia4: float
    media_competencia5: float
    competencia_mais_fraca_mais_comum: int
    distribuicao_status: dict
    evolucao_nota: List[dict]


class ComparativoMensal(BaseModel):
    """Comparação do mês atual vs mês anterior."""
    mes_atual: str
    mes_anterior: str
    variacao_horas: float
    variacao_horas_percentual: float
    variacao_questoes: float
    variacao_questoes_percentual: float
    variacao_acerto: float
    variacao_acerto_percentual: float
    variacao_ipr: float
    variacao_ipr_percentual: float
    variacao_redacoes: float
    comparativo_ipr: str
    comparativo_volume: str
    comparativo_qualidade: str


class ProjecaoFechamento(BaseModel):
    """Projeção do fechamento do mês baseado na média diária."""
    media_horas_diaria: float
    media_questoes_diaria: float
    projecao_horas_mes: float
    projecao_questoes_mes: float
    projecao_percentual_dias_estudados: float
    on_track_meta_horas: bool
    on_track_meta_questoes: bool
    dias_restantes: int
    horas_necessarias_por_dia: float
    questoes_necessarias_por_dia: float


class ScoreConsistencia(BaseModel):
    """Score de consistência e regularidade."""
    score: float
    classificacao: str
    dias_estudados_seguidos: int
    dias_falta_seguidos: int
    maior_streak_estudo: int
    variacao_diaria_horas: float
    variacao_diaria_questoes: float


class DiaDestaque(BaseModel):
    """Melhor ou pior dia do mês."""
    data: datetime
    dia_semana: str
    horas: float
    questoes: int
    percentual_acerto: float
    ipr_dia: float
    motivo: str


class CorrelacaoFocoPerformance(BaseModel):
    """Análise de correlação entre foco/energia e desempenho."""
    correlacao_foco_ipr: Optional[float]
    correlacao_energia_ipr: Optional[float]
    correlacao_sono_acerto: Optional[float]
    correlacao_ansiedade_erro: Optional[float]
    melhor_combinacao_estado: str
    pior_combinacao_estado: str


class BalanceamentoMaterias(BaseModel):
    """Análise de balanceamento entre matérias."""
    materia_id: UUID
    materia_nome: str
    peso_prova: float
    tempo_dedicado_percentual: float
    questoes_respondidas_percentual: float
    ipr: float
    nota_oficial_media: Optional[float]
    peso_vs_tempo: str
    status: str


class RecomendacaoMensal(BaseModel):
    """Recomendações estratégicas baseadas no mês."""
    categoria: str
    prioridade: str
    mensagem: str
    acao_sugerida: str


class RelatorioMensalCompleto(BaseModel):
    """
    Relatório mensal completo de performance acadêmica.

    Contém TODAS as informações disponíveis no sistema:
    - Métricas de volume (horas, questões, sessões)
    - Métricas de qualidade (IPR, percentual de acerto, análise de erros)
    - Estado mental e bem-estar (foco, energia, sono, ansiedade, fadiga)
    - Desempenho por matéria, assunto e dificuldade
    - Simulados, provas oficiais e redações
    - Comparação com mês anterior
    - Projeções e tendências
    - Análises avançadas (consistência, correlações, balanceamento)
    - Recomendações estratégicas
    """
    gerado_em: datetime
    periodo: PeriodoAnalise
    resumo_geral: ResumoGeralRelatorio
    sessoes: dict
    blocos: dict
    erros: AnaliseErros
    simulados: List[SimuladoMensalDetalhe]
    provas_oficiais: List[ProvaOficialMensal]
    redacoes: EstatisticasRedacaoMensal
    estado_mental: MediaEstadoMental
    comparativo_mes_anterior: ComparativoMensal
    projecao_fechamento: ProjecaoFechamento
    consistencia: ScoreConsistencia
    melhor_dia: Optional[DiaDestaque]
    pior_dia: Optional[DiaDestaque]
    correlacoes: CorrelacaoFocoPerformance
    balanceamento: List[BalanceamentoMaterias]
    recomendacoes: List[RecomendacaoMensal]
