import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    String,
    Integer,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from .database import Base


# ==========================================================
# MATERIA
# ==========================================================

class Materia(Base):
    __tablename__ = "tb_materia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(50), unique=True, nullable=False)
    peso_prova = Column(Numeric(5, 2), nullable=False)
    ativa = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    assuntos = relationship("Assunto", back_populates="materia")
    sessoes_estudo = relationship("SessaoEstudo", back_populates="materia")
    blocos_questoes = relationship("BlocoQuestoes", back_populates="materia")


# ==========================================================
# ASSUNTO
# ==========================================================

class Assunto(Base):
    __tablename__ = "tb_assunto"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    materia_id = Column(UUID(as_uuid=True), ForeignKey("tb_materia.id"), nullable=False)
    nome = Column(String(120), nullable=False)
    semana_do_ciclo = Column(Integer, nullable=False)  # 1 a 4
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    materia = relationship("Materia", back_populates="assuntos")
    sessoes_estudo = relationship("SessaoEstudo", back_populates="assunto")
    blocos_questoes = relationship("BlocoQuestoes", back_populates="assunto")


# ==========================================================
# SESSAO DE ESTUDO
# ==========================================================

class SessaoEstudo(Base):
    __tablename__ = "tb_sessao_estudo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(DateTime, default=datetime.utcnow, nullable=False)

    materia_id = Column(UUID(as_uuid=True), ForeignKey("tb_materia.id"), nullable=False)
    assunto_id = Column(UUID(as_uuid=True), ForeignKey("tb_assunto.id"), nullable=False)

    tipo_sessao = Column(String(20), nullable=False)  # TEORIA, QUESTOES, REVISAO
    minutos_liquidos = Column(Integer, nullable=False)

    nivel_foco = Column(Integer)      # 1-5
    nivel_energia = Column(Integer)   # 1-5

    criado_em = Column(DateTime, default=datetime.utcnow)

    materia = relationship("Materia", back_populates="sessoes_estudo")
    assunto = relationship("Assunto", back_populates="sessoes_estudo")


# ==========================================================
# BLOCO DE QUESTOES (TREINO DIÁRIO)
# ==========================================================

class BlocoQuestoes(Base):
    __tablename__ = "tb_bloco_questoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(DateTime, default=datetime.utcnow, nullable=False)

    materia_id = Column(UUID(as_uuid=True), ForeignKey("tb_materia.id"), nullable=False)
    assunto_id = Column(UUID(as_uuid=True), ForeignKey("tb_assunto.id"), nullable=False)

    dificuldade = Column(Integer, nullable=False)  # 1-5

    total_questoes = Column(Integer, nullable=False)
    total_acertos = Column(Integer, nullable=False)

    tempo_total_segundos = Column(Integer, nullable=False)
    nivel_confianca_medio = Column(Integer)  # 1-5

    criado_em = Column(DateTime, default=datetime.utcnow)

    materia = relationship("Materia", back_populates="blocos_questoes")
    assunto = relationship("Assunto", back_populates="blocos_questoes")
    erros = relationship("ErroQuestao", back_populates="bloco", cascade="all, delete")


    @hybrid_property
    def percentual_acerto(self):
        if self.total_questoes > 0:
            return (self.total_acertos / self.total_questoes) * 100
        return 0

    @hybrid_property
    def tempo_medio_por_questao(self):
        if self.total_questoes > 0:
            return self.tempo_total_segundos / self.total_questoes
        return 0


# ==========================================================
# ERRO DE QUESTAO
# ==========================================================

class ErroQuestao(Base):
    __tablename__ = "tb_erro_questao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bloco_id = Column(UUID(as_uuid=True), ForeignKey("tb_bloco_questoes.id"), nullable=False)

    tipo_erro = Column(String(30), nullable=False)
    quantidade = Column(Integer, nullable=False)

    criado_em = Column(DateTime, default=datetime.utcnow)

    bloco = relationship("BlocoQuestoes", back_populates="erros")


# ==========================================================
# SIMULADO SEMANAL (SÁBADO - 4H30)
# ==========================================================

class SimuladoSemanal(Base):
    __tablename__ = "tb_simulado_semanal"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    numero_ciclo = Column(Integer, nullable=False)
    numero_semana = Column(Integer, nullable=False)  # 1 a 4

    total_questoes = Column(Integer, nullable=False)
    total_acertos = Column(Integer, nullable=False)
    tempo_total_segundos = Column(Integer, nullable=False)

    nivel_ansiedade = Column(Integer)  # 1-5
    nivel_fadiga = Column(Integer)     # 1-5
    qualidade_sono = Column(Integer)   # 1-5

    criado_em = Column(DateTime, default=datetime.utcnow)

    desempenhos = relationship("DesempenhoSimuladoMateria", back_populates="simulado", cascade="all, delete")

    @hybrid_property
    def percentual_acerto(self):
        if self.total_questoes > 0:
            return (self.total_acertos / self.total_questoes) * 100
        return 0


# ==========================================================
# DESEMPENHO POR MATERIA NO SIMULADO
# ==========================================================

class DesempenhoSimuladoMateria(Base):
    __tablename__ = "tb_desempenho_simulado_materia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulado_id = Column(UUID(as_uuid=True), ForeignKey("tb_simulado_semanal.id"), nullable=False)
    materia_id = Column(UUID(as_uuid=True), ForeignKey("tb_materia.id"), nullable=False)

    total_questoes = Column(Integer, nullable=False)
    total_acertos = Column(Integer, nullable=False)
    tempo_total_segundos = Column(Integer, nullable=False)

    simulado = relationship("SimuladoSemanal", back_populates="desempenhos")
    materia = relationship("Materia")


# ==========================================================
# PROVA OFICIAL (PROVA ANTERIOR MENSAL)
# ==========================================================

class ProvaOficial(Base):
    __tablename__ = "tb_prova_oficial"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    ano = Column(Integer, nullable=False)
    nota_total = Column(Numeric(5,2), nullable=False)
    tempo_total_segundos = Column(Integer, nullable=False)

    nivel_ansiedade = Column(Integer)
    nivel_fadiga = Column(Integer)
    qualidade_sono = Column(Integer)

    criado_em = Column(DateTime, default=datetime.utcnow)

    desempenhos = relationship("DesempenhoProvaMateria", back_populates="prova", cascade="all, delete")


# ==========================================================
# DESEMPENHO POR MATERIA NA PROVA OFICIAL
# ==========================================================

class DesempenhoProvaMateria(Base):
    __tablename__ = "tb_desempenho_prova_materia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prova_id = Column(UUID(as_uuid=True), ForeignKey("tb_prova_oficial.id"), nullable=False)
    materia_id = Column(UUID(as_uuid=True), ForeignKey("tb_materia.id"), nullable=False)

    percentual_acerto = Column(Numeric(5,2), nullable=False)
    tempo_total_segundos = Column(Integer, nullable=False)

    prova = relationship("ProvaOficial", back_populates="desempenhos")
    materia = relationship("Materia")

# ==========================================================
# ENUM STATUS
# ==========================================================

class StatusRedacao(enum.Enum):
    critica = "critica"
    fraca = "fraca"
    regular = "regular"
    boa = "boa"
    muito_boa = "muito_boa"
    excelente = "excelente"

# ==========================================================
# REDAÇÃO
# ==========================================================

class Redacao(Base):
    __tablename__ = "tb_redacoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tema = Column(Text, nullable=False)

    eixo_tematico = Column(String(100), nullable=False)

    data_escrita = Column(DateTime, default=datetime.utcnow, nullable=False)

    tempo_escrita_min = Column(Integer, nullable=True)

    observacoes = Column(Text, nullable=True)

    repertorios = Column(Text, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    competencias = relationship(
        "CompetenciaRedacao",
        back_populates="redacao",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    analise = relationship(
        "AnaliseRedacao",
        back_populates="redacao",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    @hybrid_property
    def nota_total(self):
        if not self.competencias:
            return 0

        return sum((c.nota or 0) for c in self.competencias)


# ==========================================================
# COMPETÊNCIAS
# ==========================================================

class CompetenciaRedacao(Base):
    __tablename__ = "tb_competencias_redacao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    redacao_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tb_redacoes.id", ondelete="CASCADE"),
        nullable=False
    )

    competencia = Column(Integer, nullable=False)

    nota = Column(Integer, nullable=False)

    redacao = relationship(
        "Redacao",
        back_populates="competencias"
    )

    __table_args__ = (
        CheckConstraint("competencia BETWEEN 1 AND 5", name="check_competencia_range"),
        CheckConstraint("nota BETWEEN 0 AND 200", name="check_nota_range"),
    )


# ==========================================================
# ANÁLISE DA REDAÇÃO
# ==========================================================

class AnaliseRedacao(Base):
    __tablename__ = "tb_analises_redacao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    redacao_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tb_redacoes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    nota_total = Column(Integer, nullable=False)

    status = Column(Enum(StatusRedacao), nullable=False)

    competencia_mais_fraca = Column(Integer, nullable=False)

    diagnostico = Column(Text, nullable=True)

    recomendacao = Column(Text, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    redacao = relationship(
        "Redacao",
        back_populates="analise"
    )


# ==========================================================
# LÓGICA DE STATUS
# ==========================================================

def calcular_status(nota: int) -> StatusRedacao:

    if nota < 400:
        return StatusRedacao.critica

    if nota < 600:
        return StatusRedacao.fraca

    if nota < 700:
        return StatusRedacao.regular

    if nota < 800:
        return StatusRedacao.boa

    if nota < 900:
        return StatusRedacao.muito_boa

    return StatusRedacao.excelente