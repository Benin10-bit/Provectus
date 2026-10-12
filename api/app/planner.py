"""Ciclo por cotas, cobertura e conclusão atômica. Regras explícitas, sem pesos ocultos."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schemas
from .planning_models import Ciclo, MetaCiclo, Planejamento, AcaoEstudo
from .clock import utcnow, iso_utc, utc_naive
from .metrics import session_seconds, block_seconds, precisao, valid_questions

router = APIRouter(prefix="/api/v1/estudos", tags=["Ciclo e próxima sessão"])

def validar_assunto(db, materia_id, assunto_id):
    a = db.get(models.Assunto, assunto_id)
    m = db.get(models.Materia, materia_id)
    if not a or not m:
        raise HTTPException(404, "Matéria ou assunto não encontrado.")
    if a.materia_id != materia_id:
        raise HTTPException(422, "O assunto não pertence à matéria selecionada.")
    if not a.ativo or not m.ativa:
        raise HTTPException(422, "Selecione uma matéria e um assunto ativos.")
    return a

def active_cycle_for_date(db, date, state=None):
    state = state or db.get(Planejamento, 1)
    cycle = db.get(Ciclo, state.ciclo_id) if state and state.ciclo_id else None
    return cycle.id if cycle and not cycle.encerrado_em and utc_naive(date) >= cycle.iniciado_em else None

class MetaInput(schemas.APIModel):
    materia_id: UUID
    minutos: int = Field(gt=0, le=60000)

class CicloInput(schemas.APIModel):
    nome: str = Field(default="Meu ciclo", min_length=1, max_length=100)
    metas: list[MetaInput] = Field(min_length=1, max_length=100)
    @model_validator(mode="after")
    def distinct(self):
        if len({m.materia_id for m in self.metas}) != len(self.metas):
            raise ValueError("Uma única cota por matéria.")
        self.nome = self.nome.strip()
        if not self.nome: raise ValueError("Informe o nome do ciclo.")
        return self

class AssuntoPatch(schemas.APIModel):
    nome: str = Field(min_length=1, max_length=120)
    ordem: int = Field(ge=0, le=100000)
    referencia: str | None = Field(None, max_length=300)
    model_config = {"str_strip_whitespace": True}

class BlocoIntegrado(schemas.APIModel):
    total_questoes: int = Field(gt=0, le=10000)
    total_acertos: int = Field(ge=0)
    dificuldade: int | None = Field(None, ge=1, le=5)
    tempo_total_segundos: int | None = Field(None, gt=0, le=86400)
    _contagem = model_validator(mode="after")(schemas.validar_contagem)

class AcaoInput(schemas.APIModel):
    assunto_id: UUID
    descricao: str = Field(min_length=1, max_length=300)
    causa: Literal["CONCEITO", "INTERPRETACAO", "CALCULO", "DISTRACAO", "PRESSA", "CONTEUDO_ESQUECIDO"] | None = None
    prevista_em: datetime | None = None
    bloco_id: UUID | None = None
    consequencia: str | None = Field(None, min_length=1, max_length=300)
    uso_em: datetime | None = None
    @field_validator("uso_em")
    @classmethod
    def use_utc(cls,v): return utc_naive(v) if v else None
    model_config = {"str_strip_whitespace": True}
    @field_validator("prevista_em")
    @classmethod
    def date_utc(cls,v): return utc_naive(v) if v else None

class Conclusao(schemas.APIModel):
    chave_registro: UUID
    materia_id: UUID
    assunto_id: UUID
    data: datetime
    segundos: int = Field(gt=0, le=86400)
    atividade: Literal["TEORIA", "QUESTOES", "REVISAO", "ANALISE_ERROS"]
    finalidade: Literal['AVANCO','CONSOLIDACAO','REVISAO'] | None = None
    objetivo_revisao: str | None = Field(None,max_length=200)
    classe_revisao: Literal['MANUTENCAO','RECORRENTE','PRIORITARIA'] | None = None
    proximo_passo: str | None = Field(None, max_length=300)
    bloco: BlocoIntegrado | None = None
    acao_id: UUID | None = None
    resultado_acao: Literal["CONSEGUI", "REPETIR"] | None = None
    nova_acao: AcaoInput | None = None
    _data = field_validator("data")(schemas.validar_data)
    @model_validator(mode="after")
    def consistencia(self):
        if self.finalidade != 'REVISAO' and (self.objetivo_revisao or self.classe_revisao):
            raise ValueError('Metadados revisionais exigem finalidade de revisão.')
        if self.bloco and self.bloco.tempo_total_segundos is not None and self.bloco.tempo_total_segundos > self.segundos:
            raise ValueError("O tempo de questões não pode superar a duração líquida da sessão.")
        if bool(self.acao_id) != bool(self.resultado_acao):
            raise ValueError("Informe o resultado da ação selecionada.")
        if self.nova_acao and self.nova_acao.assunto_id != self.assunto_id:
            raise ValueError("A ação deve ser do assunto estudado.")
        return self

class AcaoResultado(schemas.APIModel):
    resultado: Literal["CONSEGUI", "REPETIR"]


def cycle_view(db):
    state = db.get(Planejamento, 1)
    cycle = db.get(Ciclo, state.ciclo_id) if state and state.ciclo_id else None
    if not cycle: return None
    goals = db.query(MetaCiclo).filter_by(ciclo_id=cycle.id).order_by(MetaCiclo.ordem, MetaCiclo.id).all()
    used = defaultdict(int)
    last = {}
    sessions = db.query(models.SessaoEstudo).filter_by(ciclo_id=cycle.id).all()
    blocks = db.query(models.BlocoQuestoes).filter_by(ciclo_id=cycle.id).all()
    for s in sessions:
        used[s.materia_id] += session_seconds(s)
        last[s.materia_id] = max(last.get(s.materia_id, datetime.min), s.data)
    for b in blocks:
        used[b.materia_id] += block_seconds(b)
        last[b.materia_id] = max(last.get(b.materia_id, datetime.min), b.data)
    materias = {m.id:m for m in db.query(models.Materia).all()}
    rows = [dict(materia_id=str(g.materia_id), nome=materias[g.materia_id].nome,
        minutos=g.minutos, segundos_consumidos=used[g.materia_id], proporcao=used[g.materia_id]/(g.minutos*60),
        ultima_sessao=iso_utc(last.get(g.materia_id)), ordem=g.ordem, ativa=bool(materias[g.materia_id].ativa)) for g in goals]
    return dict(id=str(cycle.id), nome=cycle.nome, iniciado_em=iso_utc(cycle.iniciado_em), metas=rows,
        completo=bool(rows) and all(r['proporcao']>=1 for r in rows))

@router.get("/ciclo")
def get_cycle(db: Session=Depends(get_db)):
    return cycle_view(db)

@router.post("/ciclo", status_code=201)
def create_cycle(payload:CicloInput, db:Session=Depends(get_db)):
    state = db.get(Planejamento,1,with_for_update=True)
    if not state: raise HTTPException(503,"Execute as migrações antes de configurar o ciclo.")
    current = cycle_view(db)
    if current and not current['completo']:
        raise HTTPException(409,"O ciclo atual ainda tem saldo. Continue nele; os minutos já registrados serão preservados.")
    for g in payload.metas:
        m=db.get(models.Materia,g.materia_id)
        if not m or not m.ativa: raise HTTPException(422,"Cota com matéria inexistente ou inativa.")
    if state.ciclo_id: db.get(Ciclo,state.ciclo_id).encerrado_em=utcnow()
    cycle=Ciclo(nome=payload.nome);db.add(cycle);db.flush()
    for i,g in enumerate(payload.metas): db.add(MetaCiclo(ciclo_id=cycle.id, materia_id=g.materia_id,minutos=g.minutos,ordem=i))
    state.ciclo_id=cycle.id
    # If no cycle existed when this week's snapshot was created, fill only its
    # missing subject distribution. Never reset targets or an existing distribution.
    from .planning_models import SemanaMetas
    from .goals import monday
    from copy import deepcopy
    week=db.get(SemanaMetas,monday(utcnow()),with_for_update=True)
    if week and not week.plano['materias']:
        data=deepcopy(week.plano)
        data['materias']=[dict(materia_id=str(g.materia_id),nome=db.get(models.Materia,g.materia_id).nome,peso=g.minutos) for g in payload.metas]
        data['ciclo_id']=str(cycle.id);week.plano=data
    db.commit()
    return cycle_view(db)

@router.get("/cobertura")
def coverage(materia_id:UUID|None=None, db:Session=Depends(get_db)):
    topics = db.query(models.Assunto).join(models.Materia).filter(models.Assunto.ativo.is_(True),models.Materia.ativa.is_(True))
    if materia_id: topics=topics.filter(models.Assunto.materia_id==materia_id)
    topics=topics.order_by(models.Assunto.ordem,models.Assunto.nome,models.Assunto.id).all()
    ids=[a.id for a in topics]
    if not ids:return []
    sessions=db.query(models.SessaoEstudo).filter(models.SessaoEstudo.assunto_id.in_(ids),models.SessaoEstudo.data<=utcnow()).all()
    blocks=db.query(models.BlocoQuestoes).filter(models.BlocoQuestoes.assunto_id.in_(ids),models.BlocoQuestoes.data<=utcnow()).all()
    actions=db.query(AcaoEstudo).filter(AcaoEstudo.assunto_id.in_(ids),AcaoEstudo.concluida_em.is_(None)).all()
    sm,bm,am=defaultdict(list),defaultdict(list),defaultdict(list)
    associations={a.id:a.materia_id for a in topics}
    for s in sessions:
        if associations.get(s.assunto_id)==s.materia_id and session_seconds(s)>0:sm[s.assunto_id].append(s)
    for b in blocks:
        if valid_questions(b) and associations.get(b.assunto_id)==b.materia_id:bm[b.assunto_id].append(b)
    for a in actions:am[a.assunto_id].append(a)
    out=[];recent=utcnow()-timedelta(days=60)
    for a in topics:
        ss=sm[a.id];bs=bm[a.id];latest=max(ss,key=lambda s:s.data) if ss else None
        contacts=[s.data for s in ss]+[b.data for b in bs]
        last=max(contacts) if contacts else None
        practice=[b for b in bs if b.data>=recent]
        n=sum(b.total_questoes for b in practice)
        state="SEM REGISTRO" if not contacts else "TEORIA SEM PRÁTICA" if not bs else "POUCA PRÁTICA" if n<20 or len(practice)<2 else "PRÁTICA REGISTRADA"
        if bs and not practice:state="EVIDÊNCIA ANTIGA"
        out.append(dict(id=str(a.id),materia_id=str(a.materia_id),nome=a.nome,ordem=a.ordem,referencia=a.referencia,
            familiaridade='REGISTRADO' if contacts else 'DECLARADO_ESTUDADO' if a.familiaridade_declarada=='ESTUDADO' else 'NAO_ESTUDADO' if a.familiaridade_declarada=='NAO_ESTUDADO' else 'DESCONHECIDO',
            familiaridade_declarada=a.familiaridade_declarada,estado=state,ultimo_contato=iso_utc(last),total_questoes=sum(b.total_questoes for b in bs),
            questoes_recentes=n,blocos_recentes=len(practice),precisao=round(precisao(practice)*100,2) if n else None,
            teoria_registrada=any(s.tipo_sessao=="TEORIA" for s in ss),
            proximo_passo=latest.proximo_passo if latest else None,ultima_atividade=latest.atividade or latest.tipo_sessao if latest else None,
            pendencias=[action_view(x) for x in sorted(am[a.id],key=lambda x:(x.prevista_em,str(x.id))) ]))
    return out

def action_view(a):
    return dict(id=str(a.id),assunto_id=str(a.assunto_id),bloco_id=str(a.bloco_id) if a.bloco_id else None,descricao=a.descricao,causa=a.causa,
        consequencia=a.consequencia,uso_em=iso_utc(a.uso_em),prevista_em=iso_utc(a.prevista_em),concluida_em=iso_utc(a.concluida_em),resultado=a.resultado)

def review_items(db, topics):
    from .recommender import queue
    return queue(db, now=utcnow(), topic_ids={t['id'] for t in topics})

@router.get('/revisoes')
def review_queue(materia_id:UUID|None=None,db:Session=Depends(get_db)):
    return review_items(db,coverage(materia_id,db))

@router.get('/agora')
def recommend(minutos:int|None=Query(default=None,ge=0,le=600),db:Session=Depends(get_db)):
    from .recommender import decide
    return decide(db, now=utcnow(), minutes=minutos)

class FamiliaridadeInput(schemas.APIModel):
    declaracao: Literal['ESTUDADO','NAO_ESTUDADO'] | None = None

@router.patch('/assuntos/{id}/familiaridade')
def declare_familiarity(id:UUID,payload:FamiliaridadeInput,db:Session=Depends(get_db)):
    topic=db.get(models.Assunto,id)
    if not topic:raise HTTPException(404,'Assunto não encontrado.')
    if topic.familiaridade_declarada!=payload.declaracao:
        topic.familiaridade_declarada=payload.declaracao
        topic.familiaridade_alterada_em=utcnow()
    db.commit()
    return dict(id=str(id),declaracao=topic.familiaridade_declarada)

@router.patch("/assuntos/{id}")
def update_topic(id:UUID,payload:AssuntoPatch,db:Session=Depends(get_db)):
    a=db.get(models.Assunto,id)
    if not a:raise HTTPException(404,"Assunto não encontrado.")
    other=db.query(models.Assunto).filter(models.Assunto.id!=id,models.Assunto.materia_id==a.materia_id,func.lower(models.Assunto.nome)==payload.nome.lower()).first()
    if other:raise HTTPException(409,"Já existe um assunto com esse nome na matéria.")
    for k,v in payload.model_dump().items():setattr(a,k,v)
    db.commit();return dict(id=str(a.id),nome=a.nome,ordem=a.ordem,referencia=a.referencia)

def add_action(db,payload,block=None):
    topic=db.get(models.Assunto,payload.assunto_id)
    if not topic:raise HTTPException(404,"Assunto não encontrado.")
    block=block or (db.get(models.BlocoQuestoes,payload.bloco_id) if payload.bloco_id else None)
    if payload.bloco_id and not block:raise HTTPException(404,"Bloco não encontrado.")
    if block and block.assunto_id!=topic.id:raise HTTPException(422,"Bloco de outro assunto.")
    if block and payload.causa and block.total_acertos>=block.total_questoes:raise HTTPException(422,"Bloco sem erros: programe uma revisão sem indicar causa de erro.")
    a=AcaoEstudo(assunto_id=topic.id,bloco_id=block.id if block else None,descricao=payload.descricao,causa=payload.causa,prevista_em=payload.prevista_em or utcnow(),consequencia=payload.consequencia,uso_em=payload.uso_em)
    db.add(a)
    if block and payload.causa and block.total_questoes>block.total_acertos:
        # One occurrence is an explicitly selected return action, not all errors in the block.
        db.add(models.ErroQuestao(bloco_id=block.id,tipo_erro=payload.causa,quantidade=1))
    return a

@router.post("/acoes",status_code=201)
def create_action(payload:AcaoInput,db:Session=Depends(get_db)):
    if payload.bloco_id:
        db.get(models.BlocoQuestoes,payload.bloco_id,with_for_update=True)
        count=db.query(func.coalesce(func.sum(models.ErroQuestao.quantidade),0)).filter_by(bloco_id=payload.bloco_id).scalar()
        b=db.get(models.BlocoQuestoes,payload.bloco_id)
        if b and payload.causa and count>=b.total_questoes-b.total_acertos:raise HTTPException(422,"Todos os erros deste bloco já foram classificados.")
    a=add_action(db,payload);db.commit();return action_view(a)

def resolve_action(db,id,resultado,assunto_id=None):
    a=db.get(AcaoEstudo,id,with_for_update=True)
    if not a:raise HTTPException(404,"Ação não encontrada.")
    if assunto_id and a.assunto_id!=assunto_id:raise HTTPException(422,"Ação de outro assunto.")
    if a.concluida_em:raise HTTPException(409,"Ação já concluída.")
    a.resultado=resultado
    if resultado=='CONSEGUI':a.concluida_em=utcnow()
    else:a.prevista_em=utcnow()+timedelta(days=2)
    return a

@router.patch("/acoes/{id}")
def finish_action(id:UUID,payload:AcaoResultado,db:Session=Depends(get_db)):
    a=resolve_action(db,id,payload.resultado);db.commit();return action_view(a)

@router.post("/concluir",status_code=201)
def complete(payload:Conclusao,db:Session=Depends(get_db)):
    state=db.get(Planejamento,1,with_for_update=True)
    fingerprint=hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    existing=db.query(models.SessaoEstudo).filter_by(chave_registro=payload.chave_registro).first()
    if existing:
        compatible_hashes = {fingerprint}
        import json
        legacy = payload.model_dump(mode='json')
        if payload.finalidade is None and payload.objetivo_revisao is None and payload.classe_revisao is None:
            for key in ('finalidade','objetivo_revisao','classe_revisao'):legacy.pop(key,None)
            compatible_hashes.add(hashlib.sha256(json.dumps(legacy,ensure_ascii=False,separators=(',',':')).encode()).hexdigest())
        if payload.bloco and payload.bloco.tempo_total_segundos is None:
            legacy['bloco'].pop('tempo_total_segundos', None)
            if payload.bloco.dificuldade is None:
                legacy['bloco']['dificuldade'] = 3
            import json
            compatible_hashes.add(hashlib.sha256(json.dumps(legacy, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest())
        if existing.conteudo_hash not in compatible_hashes:raise HTTPException(409,"Esta sessão já foi salva com outros dados. Edite o registro no histórico.")
        return dict(sessao_id=str(existing.id),repetido=True)
    validar_assunto(db,payload.materia_id,payload.assunto_id)
    cycle_id=active_cycle_for_date(db,payload.data,state)
    s=models.SessaoEstudo(materia_id=payload.materia_id,assunto_id=payload.assunto_id,data=payload.data,
        tipo_sessao='REVISAO' if payload.atividade=='ANALISE_ERROS' else payload.atividade,
        minutos_liquidos=max(1,(payload.segundos+59)//60),segundos_exatos=payload.segundos,
        atividade=payload.atividade,proximo_passo=payload.proximo_passo or None,ciclo_id=cycle_id,
        finalidade=payload.finalidade,objetivo_revisao=payload.objetivo_revisao,classe_revisao=payload.classe_revisao,
        chave_registro=payload.chave_registro,conteudo_hash=fingerprint)
    db.add(s);db.flush();b=None
    if payload.bloco:
        b=models.BlocoQuestoes(**payload.bloco.model_dump(),materia_id=s.materia_id,assunto_id=s.assunto_id,
            data=s.data,sessao_id=s.id,ciclo_id=cycle_id,
            dificuldade_informada=payload.bloco.dificuldade is not None,
            tempo_questoes_informado=payload.bloco.tempo_total_segundos is not None)
        db.add(b);db.flush()
    if payload.acao_id:resolve_action(db,payload.acao_id,payload.resultado_acao,s.assunto_id)
    if payload.nova_acao:add_action(db,payload.nova_acao,b)
    db.commit()
    return dict(sessao_id=str(s.id),repetido=False)

# Full validated updates: existing IDs/cycle membership remain, no delete/recreate.
@router.put("/sessoes/{id}",response_model=schemas.SessaoEstudoResponse)
def edit_session(id:UUID,payload:schemas.SessaoEstudoCreate,db:Session=Depends(get_db)):
    s=db.get(models.SessaoEstudo,id,with_for_update=True)
    if not s:raise HTTPException(404,"Sessão não encontrada.")
    validar_assunto(db,payload.materia_id,payload.assunto_id)
    b=db.query(models.BlocoQuestoes).filter_by(sessao_id=id).first()
    if b and b.tempo_questoes_informado is True and b.tempo_total_segundos is not None and b.tempo_total_segundos > payload.minutos_liquidos*60:
        raise HTTPException(422,"A sessão deve comportar o tempo de questões registrado. Corrija o bloco primeiro.")
    if s.materia_id!=payload.materia_id or s.assunto_id!=payload.assunto_id or s.tipo_sessao!=payload.tipo_sessao:
        s.finalidade=None;s.objetivo_revisao=None;s.classe_revisao=None
    for k,v in payload.model_dump().items():setattr(s,k,v)
    s.segundos_exatos=payload.minutos_liquidos*60
    s.atividade=payload.tipo_sessao
    b=db.query(models.BlocoQuestoes).filter_by(sessao_id=id).first()
    if b:
        b.materia_id=s.materia_id;b.assunto_id=s.assunto_id;b.data=s.data
        db.query(AcaoEstudo).filter_by(bloco_id=b.id).update({AcaoEstudo.assunto_id:s.assunto_id})
    db.commit();db.refresh(s);return s

@router.put("/blocos/{id}",response_model=schemas.BlocoQuestoesResponse)
def edit_block(id:UUID,payload:schemas.BlocoQuestoesCreate,db:Session=Depends(get_db)):
    b=db.get(models.BlocoQuestoes,id,with_for_update=True)
    if not b:raise HTTPException(404,"Bloco não encontrado.")
    validar_assunto(db,payload.materia_id,payload.assunto_id)
    count=db.query(func.coalesce(func.sum(models.ErroQuestao.quantidade),0)).filter_by(bloco_id=id).scalar()
    if count>payload.total_questoes-payload.total_acertos:raise HTTPException(422,"A correção deixaria mais erros classificados do que questões erradas.")
    if b.sessao_id:
        s=db.get(models.SessaoEstudo,b.sessao_id,with_for_update=True)
        if payload.tempo_total_segundos is not None and payload.tempo_total_segundos > session_seconds(s) and (payload.confirmar_tempo_questoes or payload.tempo_total_segundos != b.tempo_total_segundos or b.tempo_questoes_informado is True):
            raise HTTPException(422,"O tempo de questões não pode superar a duração líquida da sessão.")
    if payload.dificuldade != b.dificuldade or payload.confirmar_dificuldade:
        b.dificuldade_informada=payload.dificuldade is not None
    if payload.tempo_total_segundos != b.tempo_total_segundos or payload.confirmar_tempo_questoes:
        b.tempo_questoes_informado=payload.tempo_total_segundos is not None
    for k,v in payload.model_dump(exclude={'confirmar_dificuldade','confirmar_tempo_questoes'}).items():setattr(b,k,v)
    db.query(AcaoEstudo).filter_by(bloco_id=b.id).update({AcaoEstudo.assunto_id:b.assunto_id})
    if b.sessao_id:
        s=db.get(models.SessaoEstudo,b.sessao_id)
        if s.materia_id!=b.materia_id or s.assunto_id!=b.assunto_id:
            s.finalidade=None;s.objetivo_revisao=None;s.classe_revisao=None
        s.materia_id=b.materia_id;s.assunto_id=b.assunto_id;s.data=b.data
    db.commit();db.refresh(b);return b

@router.put("/simulados/{id}",response_model=schemas.SimuladoSemanalResponse)
def edit_sim(id:UUID,payload:schemas.SimuladoSemanalCreate,db:Session=Depends(get_db)):
    s=db.get(models.SimuladoSemanal,id,with_for_update=True)
    if not s:raise HTTPException(404,"Simulado não encontrado.")
    for k,v in payload.model_dump().items():setattr(s,k,v)
    db.commit();db.refresh(s);return s

@router.get('/series')
def chart_series(periodo:Literal['semana','mes','ano','total']='semana',materia_id:UUID|None=None,db:Session=Depends(get_db)):
    from .metrics import limites_periodo
    start,end=limites_periodo(periodo)
    q=db.query(models.BlocoQuestoes).filter(models.BlocoQuestoes.data>=start,models.BlocoQuestoes.data<end)
    if materia_id:q=q.filter_by(materia_id=materia_id)
    blocks=q.order_by(models.BlocoQuestoes.data.desc(),models.BlocoQuestoes.id).limit(100).all()
    sims=db.query(models.SimuladoSemanal).filter(models.SimuladoSemanal.criado_em>=start,models.SimuladoSemanal.criado_em<end).order_by(models.SimuladoSemanal.criado_em.desc(),models.SimuladoSemanal.id).limit(10).all()
    return dict(blocos=[schemas.BlocoQuestoesResponse.model_validate(b).model_dump(mode='json') for b in blocks],simulados=[schemas.SimuladoSemanalResponse.model_validate(s).model_dump(mode='json') for s in sims])

@router.get('/materias-performance')
def subject_performance(periodo:Literal['semana','mes','ano','total']='semana',db:Session=Depends(get_db)):
    from .metrics import limites_periodo
    from sqlalchemy import case
    start,end=limites_periodo(periodo)
    s,b=models.SessaoEstudo,models.BlocoQuestoes
    session_totals=dict(db.query(s.materia_id,func.sum(func.coalesce(s.segundos_exatos,s.minutos_liquidos*60))).filter(s.data>=start,s.data<end).group_by(s.materia_id).all())
    valid=(b.total_questoes>0)&(b.total_acertos>=0)&(b.total_acertos<=b.total_questoes)
    block_totals={row[0]:row[1:] for row in db.query(b.materia_id,func.sum(case((valid,b.total_questoes),else_=0)),func.sum(case((valid,b.total_acertos),else_=0)),func.sum(case((b.sessao_id.is_(None),func.coalesce(b.tempo_total_segundos,0)),else_=0)),func.sum(case((valid,1),else_=0))).filter(b.data>=start,b.data<end).group_by(b.materia_id).all()}
    result=[]
    for m in db.query(models.Materia).filter(models.Materia.ativa.is_(True)).order_by(models.Materia.nome):
        q,a,sec,n=block_totals.get(m.id,(0,0,0,0))
        result.append(dict(materia=dict(id=str(m.id),nome=m.nome),ipr=round(a/q*100,2) if q else 0,total_questoes=q,total_acertos=a,amostra_blocos=n,horas_estudo=round((session_totals.get(m.id,0)+sec)/3600,2)))
    return result
