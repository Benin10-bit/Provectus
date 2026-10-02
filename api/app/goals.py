"""Weekly, schedule-bounded goals. Snapshots never move with each new record."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from statistics import median
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from . import models
from .database import get_db
from .clock import TZ, utcnow, utc_naive, local_date
from .planning_models import ConfigMetas, SemanaMetas, Planejamento, MetaCiclo
from .metrics import session_seconds, block_seconds, valid_questions
from .evidence import SOURCES, guidance

router=APIRouter(prefix='/api/v1/metas',tags=['Metas semanais'])
DAYS=['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
DEFAULT=dict(dias=[
    dict(dia=0,inicio='14:45',fim='19:00',pausas=45,minutos=180),
    dict(dia=1,inicio='15:15',fim='19:00',pausas=45,minutos=150),
    dict(dia=2,inicio='15:25',fim='19:00',pausas=40,minutos=150),
    dict(dia=3,inicio='20:00',fim='21:00',pausas=10,minutos=45),
    dict(dia=4,inicio='21:00',fim='22:00',pausas=10,minutos=45),
    dict(dia=5,inicio='07:30',fim='15:00',pausas=120,minutos=270),
    dict(dia=6,inicio=None,fim=None,pausas=0,minutos=0)],
    percentual_pratica=40,minutos_por_questao=6,redacoes=1)

class DayInput(BaseModel):
    dia:int=Field(ge=0,le=6)
    inicio:str|None=None
    fim:str|None=None
    pausas:int=Field(ge=0,le=600)
    minutos:int=Field(ge=0,le=600)
    @model_validator(mode='after')
    def valid(self):
        if not self.inicio and not self.fim:
            if self.minutos or self.pausas:raise ValueError('Dia sem janela não pode ter meta de horas.')
            return self
        try:
            for value in (self.inicio,self.fim):
                if not value or len(value)!=5:raise ValueError()
                datetime.strptime(value,'%H:%M')
            span=minutes(self.fim)-minutes(self.inicio)
        except (ValueError,TypeError):raise ValueError('Horários devem usar HH:MM.')
        if span<=0 or self.pausas>span or self.minutos>span-self.pausas:
            raise ValueError('Meta deve caber na janela após descontar pausas; horários no mesmo dia.')
        return self

class ProfileInput(BaseModel):
    meta_questoes:int|None=Field(default=None,ge=1,le=5000)
    dias:list[DayInput]=Field(min_length=7,max_length=7)
    percentual_pratica:int=Field(ge=10,le=70)
    minutos_por_questao:float=Field(ge=2,le=15)
    redacoes:int=Field(ge=0,le=2)
    @model_validator(mode='after')
    def valid(self):
        if sorted(d.dia for d in self.dias)!=list(range(7)):raise ValueError('Informe cada dia da semana uma vez.')
        self.dias.sort(key=lambda d:d.dia)
        return self

class Adjustment(BaseModel):
    percentual:Literal[0,50,75,100]

class QuestionGoalInput(BaseModel):
    meta_questoes:int|None=Field(default=None,ge=1,le=5000)
    proximas_semanas:bool=True

def minutes(hhmm):
    h,m=map(int,hhmm.split(':'));return h*60+m

def bounds(start):
    return utc_naive(datetime.combine(start,time.min,TZ)),utc_naive(datetime.combine(start+timedelta(days=7),time.min,TZ))

def monday(now):
    today=local_date(now);return today-timedelta(days=today.weekday())

def profile(db):
    conf=db.get(ConfigMetas,1)
    if not conf:
        db.get(Planejamento,1,with_for_update=True)
        conf=db.get(ConfigMetas,1,populate_existing=True)
        if not conf:
            conf=ConfigMetas(id=1,dados=deepcopy(DEFAULT));db.add(conf);db.commit()
    return conf

def calibration(db,start,config):
    hi=bounds(start)[0];lo=hi-timedelta(days=28)
    rows=db.query(models.BlocoQuestoes).filter(models.BlocoQuestoes.data>=lo,models.BlocoQuestoes.data<hi).all()
    # Mixed theory + questions sessions do not measure question-solving pace.
    eligible_sessions={s.id for s in db.query(models.SessaoEstudo).filter(models.SessaoEstudo.data>=lo,models.SessaoEstudo.data<hi).all() if (s.atividade or s.tipo_sessao)=='QUESTOES'}
    rows=[b for b in rows if valid_questions(b) and (not b.sessao_id or b.sessao_id in eligible_sessions) and 30<=b.tempo_total_segundos/b.total_questoes<=1800]
    n=sum(b.total_questoes for b in rows)
    if len(rows)>=3 and n>=30:
        cost=max(2,min(15,median(b.tempo_total_segundos/b.total_questoes/60 for b in rows)*1.5))
        source='Mediana do tempo por questão nos blocos elegíveis dos 28 dias anteriores + 50% de reserva para correção (heurística).'
    else:
        cost=config['minutos_por_questao'];source='Estimativa inicial editável, incluindo tentativa e correção; histórico insuficiente para calibrar.'
    return dict(minutos_por_questao=round(cost,2),blocos=len(rows),questoes=n,origem=source)

def split_minutes(total,weights):
    if not weights:return []
    denominator=sum(w['peso'] for w in weights)
    exact=[total*w['peso']/denominator for w in weights]
    result=[int(v) for v in exact]
    for i in sorted(range(len(weights)),key=lambda i:(-(exact[i]-result[i]),i))[:total-sum(result)]:result[i]+=1
    return [{**w,'meta_minutos':value} for w,value in zip(weights,result)]

def ensure_week(db,now=None):
    now=now or utcnow();start=monday(now)
    week=db.get(SemanaMetas,start)
    if week:return week
    conf=profile(db)
    db.get(Planejamento,1,with_for_update=True)
    week=db.get(SemanaMetas,start,populate_existing=True)
    if week:return week
    days=deepcopy(conf.dados['dias']);effective=max(start,local_date(conf.criada_em))
    for day in days:
        if start+timedelta(days=day['dia'])<effective:day['minutos']=0
    target=sum(d['minutos'] for d in days);pace=calibration(db,start,conf.dados)
    questions=int(target*conf.dados['percentual_pratica']/100/pace['minutos_por_questao']//5)*5
    automatic_questions=questions
    manual=conf.dados.get('meta_questoes')
    if manual is not None:
        full=sum(d['minutos'] for d in conf.dados['dias'])
        questions=int(manual*target/full) if full else manual
    state=db.get(Planejamento,1)
    quotas=db.query(MetaCiclo).filter_by(ciclo_id=state.ciclo_id).order_by(MetaCiclo.ordem,MetaCiclo.id).all() if state and state.ciclo_id else []
    subjects={m.id:m for m in db.query(models.Materia).filter_by(ativa=True).all()}
    weights=[dict(materia_id=str(g.materia_id),nome=subjects[g.materia_id].nome,peso=g.minutos) for g in quotas if g.materia_id in subjects]
    plan=dict(dias=days,base_minutos=target,base_questoes=questions,base_redacoes=conf.dados['redacoes'],
        percentual=100,calibracao=pace,percentual_pratica=conf.dados['percentual_pratica'],
        materias=weights,ciclo_id=str(state.ciclo_id) if state and state.ciclo_id else None,
        parcial=effective>start,inicio_efetivo=effective.isoformat(),questoes_automaticas=automatic_questions,
        origem_questoes='manual' if manual is not None else 'automatica')
    week=SemanaMetas(inicio=start,plano=plan);db.add(week);db.commit()
    return week

def totals(db,start,end):
    sessions=db.query(models.SessaoEstudo).filter(models.SessaoEstudo.data>=start,models.SessaoEstudo.data<end).all()
    blocks=db.query(models.BlocoQuestoes).filter(models.BlocoQuestoes.data>=start,models.BlocoQuestoes.data<end).all()
    sims=db.query(models.SimuladoSemanal).filter(models.SimuladoSemanal.criado_em>=start,models.SimuladoSemanal.criado_em<end).all()
    essays=db.query(models.Redacao).filter(models.Redacao.data_escrita>=start,models.Redacao.data_escrita<end).count()
    daily={i:0.0 for i in range(7)};subjects={};count=0;hits=0
    for rows,seconds,dt in [(sessions,session_seconds,lambda s:s.data),(blocks,block_seconds,lambda b:b.data),(sims,lambda s:s.tempo_total_segundos,lambda s:s.criado_em)]:
        for x in rows:
            value=max(0,seconds(x))/60;daily[local_date(dt(x)).weekday()]+=value
            if hasattr(x,'materia_id'):subjects[str(x.materia_id)]=subjects.get(str(x.materia_id),0)+value
    for b in blocks+sims:
        if valid_questions(b):count+=b.total_questoes;hits+=b.total_acertos
    return dict(minutos=sum(daily.values()),questoes=count,acertos=hits,redacoes=essays,dias=daily,materias=subjects)

def status(actual,target,expected,closed=False):
    if target<=0:return 'SEM META'
    if actual>=target:return 'META ATINGIDA'
    if closed:return 'SEMANA ENCERRADA'
    if actual<expected:return 'REAJUSTAR RITMO'
    return 'NO RITMO' if expected>0 else 'EM ANDAMENTO'

def mission_guidance(mission, actual, target, questions, essays, capacity):
    hours_left=max(0,target-actual['minutos'])
    q_left=max(0,questions-actual['questoes'])
    r_left=max(0,essays-actual['redacoes'])
    if mission=='SEMANA EM PAUSA':
        return 'Semana pausada. Quando puder retomar, reative o plano em Metas; seus registros estão preservados.'
    if mission=='METAS DA SEMANA CONCLUÍDAS':
        return 'Metas concluídas. Confira dúvidas e erros na Lista de revisão, sem aumentar a carga só para manter os indicadores verdes.'
    if mission=='SEMANA ENCERRADA':
        return f'Semana encerrada: faltaram {hours_left/60:.1f}h, {q_left:.0f} questões e {r_left:.0f} redações. Ajuste o próximo ciclo sem acumular dívida.'
    if mission=='AJUSTAR PLANO':
        return f'Faltam {hours_left/60:.1f}h, mas restam {capacity/60:.1f}h nas janelas cadastradas. Confira o cronograma ou reduza a meta em Metas, preservando as pausas.'
    if mission=='RETOMAR O RITMO':
        return f'Abaixo do ritmo previsto: faltam {hours_left/60:.1f}h e {q_left:.0f} questões. Ainda há {capacity/60:.1f}h disponíveis no cronograma; retome a próxima sessão em Estudar agora.'
    if q_left and not hours_left:
        return f'Meta de tempo concluída; faltam {q_left:.0f} questões. Priorize a prática do assunto indicado em Estudar agora e confira os erros.'
    if r_left and not hours_left and not q_left:
        return f'Tempo e questões concluídos; faltam {r_left:.0f} redação(ões). Reserve a próxima atividade para escrever e registrar sua redação.'
    return f'Continue pela próxima sessão em Estudar agora. Saldo da semana: {hours_left/60:.1f}h, {q_left:.0f} questões e {r_left:.0f} redação(ões).'

def week_view(db,week=None,now=None):
    now=now or utcnow();week=week or ensure_week(db,now);plan=week.plano
    local=now.replace(tzinfo=timezone.utc).astimezone(TZ);start,end=bounds(week.inicio)
    actual=totals(db,start,min(end,now));factor=plan['percentual']/100
    days=[];expected=0.;remaining_capacity=0.
    for d in plan['dias']:
        day=week.inicio+timedelta(days=d['dia']);target=int(d['minutos']*factor)
        window=minutes(d['fim'])-minutes(d['inicio']) if d['inicio'] else 0
        capacity=max(0,window-d['pausas'])
        elapsed=1 if day<local.date() else 0
        if day==local.date() and window:
            elapsed=max(0,min(1,(local.hour*60+local.minute+local.second/60-minutes(d['inicio']))/window))
        expected+=target*elapsed
        if day>=local.date():remaining_capacity+=max(0,min(capacity-actual['dias'][d['dia']],capacity*(1-elapsed)))
        days.append({**d,'nome':DAYS[d['dia']],'data':day.isoformat(),'meta_minutos':target,'janela_minutos':window,
            'capacidade_minutos':capacity,'realizado_minutos':round(actual['dias'][d['dia']],1)})
    target=sum(d['meta_minutos'] for d in days)
    qtarget=int(plan['base_questoes']*factor);rtarget=plan['base_redacoes'] if factor else 0
    closed=now>=end;pace_ratio=expected/target if target else 0
    statuses=dict(horas=status(actual['minutos'],target,expected,closed),questoes=status(actual['questoes'],qtarget,qtarget*pace_ratio,closed),
        redacoes=status(actual['redacoes'],rtarget,rtarget if closed else 0,closed))
    all_done=bool(target or qtarget or rtarget) and actual['minutos']>=target and actual['questoes']>=qtarget and actual['redacoes']>=rtarget
    mission='METAS DA SEMANA CONCLUÍDAS' if all_done else 'SEMANA ENCERRADA' if closed else 'AJUSTAR PLANO' if actual['minutos']+remaining_capacity+1<target else 'RETOMAR O RITMO' if 'REAJUSTAR RITMO' in statuses.values() else 'NO RITMO' if expected>0 else 'SEMANA EM ANDAMENTO'
    if not target and not qtarget and not rtarget:mission='SEMANA EM PAUSA'
    weights=split_minutes(target,plan['materias'])
    return dict(inicio=week.inicio.isoformat(),fim=(week.inicio+timedelta(days=6)).isoformat(),fuso=str(TZ),parcial=plan['parcial'],
        meta_minutos=target,meta_questoes=qtarget,meta_redacoes=rtarget,percentual=plan['percentual'],dias=days,
        base_questoes=plan['base_questoes'],origem_questoes=plan.get('origem_questoes','automatica'),
        realizado={k:round(v,2) for k,v in actual.items() if k not in ('dias','materias')},
        esperado_minutos=round(expected,1),capacidade_restante_minutos=round(remaining_capacity,1),status=statuses,status_missao=mission,
        calibracao=plan['calibracao'],percentual_pratica=plan['percentual_pratica'],
        materias=[{**w,'realizado_minutos':round(actual['materias'].get(w['materia_id'],0),1)} for w in weights],
        diagnostico_missao=mission_guidance(mission, actual, target, qtarget, rtarget, remaining_capacity),
        distribuicao_ciclo_id=plan['ciclo_id'])

@router.get('/semana')
def current_week(db:Session=Depends(get_db)):
    return week_view(db)

@router.get('/configuracao')
def get_profile(db:Session=Depends(get_db)):
    return profile(db).dados

@router.put('/configuracao')
def set_profile(payload:ProfileInput,db:Session=Depends(get_db)):
    ensure_week(db)  # Preserve the current target before changing future weeks.
    conf=db.get(ConfigMetas,1,with_for_update=True);conf.dados=payload.model_dump();db.commit()
    return dict(mensagem='Configuração salva para as próximas semanas. A meta atual foi preservada.',configuracao=conf.dados)

@router.patch('/semana/ajuste')
def adjust(payload:Adjustment,db:Session=Depends(get_db)):
    week=ensure_week(db);week=db.get(SemanaMetas,week.inicio,with_for_update=True)
    week.plano={**week.plano,'percentual':payload.percentual};db.commit()
    return week_view(db,week)

@router.get('/fontes')
def sources():return SOURCES

@router.patch('/semana/questoes')
def question_goal(payload:QuestionGoalInput,db:Session=Depends(get_db)):
    week=ensure_week(db)
    conf=db.get(ConfigMetas,1,with_for_update=True)
    week=db.get(SemanaMetas,week.inicio,with_for_update=True)
    plan=deepcopy(week.plano)
    automatic=plan.get('questoes_automaticas',plan['base_questoes'])
    plan.update(questoes_automaticas=automatic,
        base_questoes=payload.meta_questoes if payload.meta_questoes is not None else automatic,
        origem_questoes='manual' if payload.meta_questoes is not None else 'automatica')
    week.plano=plan
    if payload.proximas_semanas:
        conf.dados={**conf.dados,'meta_questoes':payload.meta_questoes}
    db.commit()
    return week_view(db,week)

@router.get('/metodos')
def methods():return {a:guidance(a) for a in ('TEORIA','QUESTOES','REVISAO','ANALISE_ERROS')}

@router.get('/orientacoes')
def suggestions(db:Session=Depends(get_db)):
    from .block_guidance import block_guidance
    return block_guidance(db)

def session_context(db,activity):
    week=week_view(db);local=utcnow().replace(tzinfo=timezone.utc).astimezone(TZ);day=week['dias'][local.weekday()]
    remaining=max(0,day['meta_minutos']-day['realizado_minutos'])
    proposed=min(45 if local.weekday() in (3,4) else 50,int(remaining))
    notice='Referência de duração; pause quando precisar e confirme o tempo real ao concluir.'
    if day['inicio']:
        clock=local.hour*60+local.minute
        if minutes(day['inicio'])<=clock<minutes(day['fim']):proposed=min(proposed,minutes(day['fim'])-clock)
        elif clock>=minutes(day['fim']):proposed=0;notice='A janela de hoje terminou. Não há obrigação de compensar agora.'
        else:notice=f'Próxima janela de hoje: {day["inicio"]}–{day["fim"]}. Comece quando estiver disponível.'
    else:proposed=0;notice='Hoje não há meta de horas. No domingo, mantenha redação leve e descanso.'
    return dict(duracao_sugerida_minutos=proposed,aviso=notice,orientacao=guidance(activity))
