import uuid
from sqlalchemy import Column, String, Integer, DateTime, Date, JSON, Boolean, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from .database import Base
from .clock import utcnow

class Ciclo(Base):
    __tablename__ = "tb_ciclo"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), nullable=False)
    iniciado_em = Column(DateTime, nullable=False, default=utcnow)
    encerrado_em = Column(DateTime)
    # All writes are serialized by the single planner state row.

class Planejamento(Base):
    __tablename__ = "tb_planejamento"
    id = Column(Integer, primary_key=True)
    ciclo_id = Column(UUID(as_uuid=True), ForeignKey("tb_ciclo.id"))

class MetaCiclo(Base):
    __tablename__ = "tb_meta_ciclo"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ciclo_id = Column(UUID(as_uuid=True), ForeignKey("tb_ciclo.id"), nullable=False)
    materia_id = Column(UUID(as_uuid=True), ForeignKey("tb_materia.id"), nullable=False)
    minutos = Column(Integer, nullable=False)
    ordem = Column(Integer, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("ciclo_id", "materia_id", name="uq_meta_ciclo_materia"), CheckConstraint("minutos > 0", name="ck_meta_minutos"))

class AcaoEstudo(Base):
    __tablename__ = "tb_acao_estudo"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assunto_id = Column(UUID(as_uuid=True), ForeignKey("tb_assunto.id"), nullable=False)
    bloco_id = Column(UUID(as_uuid=True), ForeignKey("tb_bloco_questoes.id"))
    descricao = Column(String(300), nullable=False)
    causa = Column(String(30))
    prevista_em = Column(DateTime, nullable=False, default=utcnow)
    criada_em = Column(DateTime, nullable=False, default=utcnow)
    concluida_em = Column(DateTime)
    resultado = Column(String(30))

class ConfigMetas(Base):
    __tablename__ = 'tb_config_metas'
    id = Column(Integer, primary_key=True)
    dados = Column(JSON, nullable=False)
    criada_em = Column(DateTime, nullable=False, default=utcnow)

class SemanaMetas(Base):
    __tablename__ = 'tb_semana_metas'
    inicio = Column(Date, primary_key=True)
    plano = Column(JSON, nullable=False)
    criada_em = Column(DateTime, nullable=False, default=utcnow)
