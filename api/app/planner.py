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
    dificuldade: int = Field(default=3, ge=1, le=5)
    _contagem = model_validator(mode="after")(schemas.validar_contagem)

class AcaoInput(schemas.APIModel):
    assunto_id: UUID
    descricao: str = Field(min_length=1, max_length=300)
    causa: Literal["CONCEITO", "INTERPRETACAO", "CALCULO", "DISTRACAO", "PRESSA", "CONTEUDO_ESQUECIDO"] | None = None
    prevista_em: datetime | None = None
    bloco_id: UUID | None = None
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
    proximo_passo: str | None = Field(None, max_length=300)
    bloco: BlocoIntegrado | None = None
    acao_id: UUID | None = None
    resultado_acao: Literal["CONSEGUI", "REPETIR"] | None = None
    nova_acao: AcaoInput | None = None
    _data = field_validator("data")(schemas.validar_data)
    @model_validator(mode="after")
    def consistencia(self):
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
        if associations.get(s.assunto_id)==s.materia_id:sm[s.assunto_id].append(s)
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
            estado=state,ultimo_contato=iso_utc(last),total_questoes=sum(b.total_questoes for b in bs),
            questoes_recentes=n,blocos_recentes=len(practice),precisao=round(precisao(practice)*100,2) if n else None,
            teoria_registrada=any(s.tipo_sessao=="TEORIA" for s in ss),
            proximo_passo=latest.proximo_passo if latest else None,ultima_atividade=latest.atividade or latest.tipo_sessao if latest else None,
            pendencias=[action_view(x) for x in sorted(am[a.id],key=lambda x:(x.prevista_em,str(x.id))) ]))
    return out

def action_view(a):
    return dict(id=str(a.id),assunto_id=str(a.assunto_id),bloco_id=str(a.bloco_id) if a.bloco_id else None,descricao=a.descricao,causa=a.causa,
        prevista_em=iso_utc(a.prevista_em),concluida_em=iso_utc(a.concluida_em),resultado=a.resultado)

def review_items(db, topics):
    """Derived queue: reads never create obligations or rewrite historical records."""
    ids=[UUID(t['id']) for t in topics]
    if not ids:return []
    now=utcnow()
    blocks=db.query(models.BlocoQuestoes).filter(models.BlocoQuestoes.assunto_id.in_(ids),models.BlocoQuestoes.data<=now).all()
    sessions=db.query(models.SessaoEstudo).filter(models.SessaoEstudo.assunto_id.in_(ids),models.SessaoEstudo.data<=now).all()
    errors=db.query(models.ErroQuestao).join(models.BlocoQuestoes).filter(models.BlocoQuestoes.assunto_id.in_(ids),models.BlocoQuestoes.data<=now).all()
    completed=db.query(AcaoEstudo).filter(AcaoEstudo.assunto_id.in_(ids),AcaoEstudo.concluida_em.is_not(None),AcaoEstudo.concluida_em<=now).all()
    finished=defaultdict(list)
    for a in completed:finished[str(a.assunto_id)].append(a.concluida_em)
    causes=defaultdict(set)
    for error in errors:
        if error.quantidade>0:causes[error.bloco_id].add(str(error.tipo_erro))
    bm,sm=defaultdict(list),defaultdict(list)
    associations={t['id']:t['materia_id'] for t in topics}
    for b in blocks:
        if valid_questions(b) and associations.get(str(b.assunto_id))==str(b.materia_id):bm[str(b.assunto_id)].append(b)
    for s in sessions:
        if associations.get(str(s.assunto_id))==str(s.materia_id):sm[str(s.assunto_id)].append(s)
    names={str(m.id):m.nome for m in db.query(models.Materia).all()}
    result=[]
    for t in topics:
        def item(kind,activity,task,reason,due,priority,action=None):
            return dict(id=action['id'] if action else 'auto:'+t['id'],origem=kind,
                materia_id=t['materia_id'],materia=names.get(t['materia_id'],''),assunto_id=t['id'],assunto=t['nome'],
                atividade=activity,tarefa=task,motivo=reason,prevista_em=iso_utc(due),disponivel=due<=now,
                prioridade=priority,acao_id=action['id'] if action else None,referencia=t['referencia'])
        for a in t['pendencias']:
            due=utc_naive(datetime.fromisoformat(a['prevista_em']))
            result.append(item('PROGRAMADA','ANALISE_ERROS' if a['causa'] else 'REVISAO',a['descricao'],
                'Ação programada por você; a data não representa dívida de estudo.',due,0,a))
        # One action per topic at a time; scheduled actions also suppress duplicate suggestions.
        if t['pendencias'] or not t['ultimo_contato']:continue
        bs=sorted(bm[t['id']],key=lambda b:(b.data,str(b.id)))
        ss=sorted(sm[t['id']],key=lambda s:(s.data,str(s.id)))
        last_review=max([s.data for s in ss if s.atividade in ('REVISAO','ANALISE_ERROS') or s.tipo_sessao=='REVISAO']+finished[t['id']],default=None)
        last_session=ss[-1] if ss else None
        latest=bs[-1] if bs else None
        last=utc_naive(datetime.fromisoformat(t['ultimo_contato']))
        floor=last_review+timedelta(days=2) if last_review else datetime.min
        unresolved=[b for b in bs if causes[b.id] and b.total_acertos<b.total_questoes and (not last_review or b.data>last_review)]
        if unresolved:
            b=unresolved[-1]
            result.append(item('AUTOMATICA','ANALISE_ERROS','Refaça sem consulta alguns erros deste assunto, confira a solução e resolva duas questões semelhantes.',
                f'Há erros classificados sem uma sessão posterior de revisão/análise. Causas informadas: {", ".join(sorted(causes[b.id]))}.',max(b.data,floor),1))
        elif last_session and last_session.proximo_passo and (not latest or latest.data<=last_session.data):
            result.append(item('AUTOMATICA','QUESTOES' if bs else 'REVISAO',last_session.proximo_passo,
                'Próximo passo deixado na última sessão deste assunto.',max(last_session.data,floor),2))
        elif not bs:
            result.append(item('AUTOMATICA','QUESTOES','Resolva 5–10 questões sem consulta; confira as soluções e registre total e acertos.',
                'Há estudo registrado, mas nenhuma prática válida. Faça um diagnóstico, não uma releitura obrigatória.',max(last,floor),3))
        else:
            recent=[b for b in bs if b.data>=now-timedelta(days=60)][-2:]
            n=sum(b.total_questoes for b in recent)
            hits=sum(b.total_acertos for b in recent)
            from .study_analysis import critical, performance_change
            change=performance_change([b for b in bs if b.data>=now-timedelta(days=60)])
            if not recent:
                activity='REVISAO';task='Resolva 5–10 questões sem consulta para verificar retenção; reveja somente os pontos que não conseguir explicar.'
                reason='A última prática tem mais de 60 dias. Isso pede uma verificação, não comprova esquecimento.';priority=3;due=latest.data+timedelta(days=7)
            elif critical(recent):
                activity='REVISAO';task='Confira os erros das duas últimas tentativas, reveja o ponto de teoria necessário e faça 5–10 questões novas.'
                reason=f'{hits} acertos em {n} questões nas duas últimas tentativas recentes. Verifique a dificuldade sem presumir sua causa.';priority=2;due=latest.data+timedelta(days=1)
            elif change:
                _,activity,reason,task=change;priority=3;due=latest.data+timedelta(days=1)
            elif n<20 or len(recent)<2:
                activity='QUESTOES';task='Faça 5–10 questões novas sem consulta e confira os erros para ampliar a evidência.'
                reason=f'Amostra pequena: {n} questões em {len(recent)} tentativa(s) recente(s).';priority=4;due=latest.data+timedelta(days=1)
            else:
                activity='REVISAO';task='Faça um pequeno bloco sem consulta e explique uma solução; reveja a teoria apenas se necessário.'
                reason='Retorno periódico para verificar retenção, sem flashcards nem diagnóstico automático de domínio.';priority=5;due=latest.data+timedelta(days=7)
            result.append(item('AUTOMATICA',activity,task,reason,max(due,floor),priority))
    return sorted(result,key=lambda r:(not r['disponivel'],r['prioridade'],r['prevista_em'],r['materia'],r['assunto'],r['id']))

@router.get('/revisoes')
def review_queue(materia_id:UUID|None=None,db:Session=Depends(get_db)):
    return review_items(db,coverage(materia_id,db))

@router.get("/agora")
def recommend(db:Session=Depends(get_db)):
    cycle=cycle_view(db)
    if not cycle:return dict(ciclo=None,recomendacao=None,motivo="Informe as cotas do seu ciclo uma vez para receber uma sugestão.")
    eligible=[g for g in cycle['metas'] if g['proporcao']<1 and g['ativa']]
    if not eligible:return dict(ciclo=cycle,recomendacao=None,motivo="Ciclo concluído. Inicie o próximo com as mesmas cotas ou ajuste a distribuição." if cycle['completo'] else "Há cotas de matérias inativas. Reative-as para continuar o ciclo.")
    g=min(eligible,key=lambda g:(g['proporcao'],g['ultima_sessao'] or '',g['ordem'],g['materia_id']))
    topics=coverage(UUID(g['materia_id']),db)
    if not topics:return dict(ciclo=cycle,recomendacao=None,materia_id=g['materia_id'],motivo=f"Cadastre o próximo assunto de {g['nome']} para começar.")
    latest=db.query(models.SessaoEstudo).filter_by(materia_id=UUID(g['materia_id'])).order_by(models.SessaoEstudo.data.desc()).first()
    repair_last=latest and (latest.atividade in ('REVISAO','ANALISE_ERROS') or latest.tipo_sessao=='REVISAO')
    reviews=[r for r in review_items(db,topics) if r['disponivel']]
    fresh=[t for t in topics if t['estado'] in ('SEM REGISTRO','TEORIA SEM PRÁTICA','POUCA PRÁTICA')]
    continuation=next((t for t in topics if latest and t['id']==str(latest.assunto_id) and t['proximo_passo']),None)
    action=None
    review_reason=''
    if reviews and (not repair_last or not fresh):
        chosen=reviews[0];topic=next(t for t in topics if t['id']==chosen['assunto_id'])
        action={'id':chosen['acao_id']} if chosen['acao_id'] else None
        activity=chosen['atividade'];task=chosen['tarefa'];review_reason=chosen['motivo']
    elif continuation and not repair_last:
        topic=continuation;activity='TEORIA' if not topic['total_questoes'] else 'QUESTOES';task=topic['proximo_passo']
    else:
        topic=fresh[0] if fresh else min(topics,key=lambda t:(t['ultimo_contato'] or '',t['ordem'],t['id']))
        activity='TEORIA' if topic['estado']=='SEM REGISTRO' else 'QUESTOES'
        task='Estude este ponto e resolva um exemplo no seu material.' if activity=='TEORIA' else 'Resolva um pequeno bloco sem consulta e confira os erros. A amostra ajuda a definir o próximo passo.'
    from .goals import session_context
    return dict(ciclo=cycle,motivo=None,recomendacao=dict(materia_id=g['materia_id'],materia=g['nome'],assunto_id=topic['id'],assunto=topic['nome'],atividade=activity,tarefa=task,
        **session_context(db,activity),
        referencia=topic['referencia'],acao_id=action['id'] if action else None,
        explicacao=f"{g['proporcao']*100:.0f}% da cota de {g['nome']} concluída: menor proporção disponível; empates usam o maior tempo sem estudo e a ordem do ciclo. {review_reason or topic['estado'].capitalize()}."))

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
    a=AcaoEstudo(assunto_id=topic.id,bloco_id=block.id if block else None,descricao=payload.descricao,causa=payload.causa,prevista_em=payload.prevista_em or utcnow())
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
        if existing.conteudo_hash!=fingerprint:raise HTTPException(409,"Esta sessão já foi salva com outros dados. Edite o registro no histórico.")
        return dict(sessao_id=str(existing.id),repetido=True)
    validar_assunto(db,payload.materia_id,payload.assunto_id)
    cycle_id=active_cycle_for_date(db,payload.data,state)
    s=models.SessaoEstudo(materia_id=payload.materia_id,assunto_id=payload.assunto_id,data=payload.data,
        tipo_sessao='REVISAO' if payload.atividade=='ANALISE_ERROS' else payload.atividade,
        minutos_liquidos=max(1,(payload.segundos+59)//60),segundos_exatos=payload.segundos,
        atividade=payload.atividade,proximo_passo=payload.proximo_passo or None,ciclo_id=cycle_id,
        chave_registro=payload.chave_registro,conteudo_hash=fingerprint)
    db.add(s);db.flush();b=None
    if payload.bloco:
        b=models.BlocoQuestoes(**payload.bloco.model_dump(),materia_id=s.materia_id,assunto_id=s.assunto_id,
            data=s.data,tempo_total_segundos=payload.segundos,sessao_id=s.id,ciclo_id=cycle_id)
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
    for k,v in payload.model_dump().items():setattr(s,k,v)
    s.segundos_exatos=payload.minutos_liquidos*60
    s.atividade=payload.tipo_sessao
    b=db.query(models.BlocoQuestoes).filter_by(sessao_id=id).first()
    if b:
        b.materia_id=s.materia_id;b.assunto_id=s.assunto_id;b.data=s.data;b.tempo_total_segundos=s.segundos_exatos
        db.query(AcaoEstudo).filter_by(bloco_id=b.id).update({AcaoEstudo.assunto_id:s.assunto_id})
    db.commit();db.refresh(s);return s

@router.put("/blocos/{id}",response_model=schemas.BlocoQuestoesResponse)
def edit_block(id:UUID,payload:schemas.BlocoQuestoesCreate,db:Session=Depends(get_db)):
    b=db.get(models.BlocoQuestoes,id,with_for_update=True)
    if not b:raise HTTPException(404,"Bloco não encontrado.")
    validar_assunto(db,payload.materia_id,payload.assunto_id)
    count=db.query(func.coalesce(func.sum(models.ErroQuestao.quantidade),0)).filter_by(bloco_id=id).scalar()
    if count>payload.total_questoes-payload.total_acertos:raise HTTPException(422,"A correção deixaria mais erros classificados do que questões erradas.")
    for k,v in payload.model_dump().items():setattr(b,k,v)
    db.query(AcaoEstudo).filter_by(bloco_id=b.id).update({AcaoEstudo.assunto_id:b.assunto_id})
    if b.sessao_id:
        s=db.get(models.SessaoEstudo,b.sessao_id)
        s.materia_id=b.materia_id;s.assunto_id=b.assunto_id;s.data=b.data
        s.segundos_exatos=b.tempo_total_segundos;s.minutos_liquidos=max(1,(b.tempo_total_segundos+59)//60)
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
    block_totals={row[0]:row[1:] for row in db.query(b.materia_id,func.sum(case((valid,b.total_questoes),else_=0)),func.sum(case((valid,b.total_acertos),else_=0)),func.sum(case((b.sessao_id.is_(None),b.tempo_total_segundos),else_=0)),func.sum(case((valid,1),else_=0))).filter(b.data>=start,b.data<end).group_by(b.materia_id).all()}
    result=[]
    for m in db.query(models.Materia).filter(models.Materia.ativa.is_(True)).order_by(models.Materia.nome):
        q,a,sec,n=block_totals.get(m.id,(0,0,0,0))
        result.append(dict(materia=dict(id=str(m.id),nome=m.nome),ipr=round(a/q*100,2) if q else 0,total_questoes=q,total_acertos=a,amostra_blocos=n,horas_estudo=round((session_totals.get(m.id,0)+sec)/3600,2)))
    return result
