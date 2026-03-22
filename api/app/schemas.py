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