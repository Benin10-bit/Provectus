"""Single deterministic study decision. Thresholds are editable product heuristics.

Reads never write study events. Episodes/ages are derived from general records;
question_bank, simulations and page views are deliberately absent.
"""
from collections import Counter, defaultdict
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from . import models, clock
from .metrics import valid_questions, session_seconds
from .planning_models import AcaoEstudo, ConfigMetas


@dataclass(frozen=True)
class Policy:
    maintenance: int = 4
    recurring: int = 2
    priority: int = 1
    recent_days: int = 14
    productive_gap: int = 2

    def __post_init__(self):
        if not (1 <= self.priority <= self.recurring <= self.maintenance and self.recent_days >= 1 and self.productive_gap >= 2):
            raise ValueError('Parâmetros revisionais inválidos: 1 <= prioritária <= recorrente <= manutenção; intervalo produtivo >= 2.')

    @classmethod
    def configured(cls):
        return cls(**{k:int(os.getenv('RECOMMENDER_'+k.upper(),v)) for k,v in cls().__dict__.items()})

    def limit(self, kind):
        return {'MANUTENCAO':self.maintenance,'RECORRENTE':self.recurring,'PRIORITARIA':self.priority}[kind]


def availability(db, now, minutes=None):
    """Current confirmed schedule, never weekly debt or historical school hours."""
    if minutes is not None:
        return dict(duracao_sugerida_minutos=min(50,minutes),origem_duracao='INFORMADA',
                    disponivel=minutes >= 5,aviso='Tempo informado para agora; registre somente o tempo realizado.')
    conf=db.get(ConfigMetas,1)
    data=conf.dados if conf else {}
    # Old seeds cannot establish that the student's historical schedule is current.
    # A different persisted schedule is usable; saving any schedule confirms it.
    from .goals import DEFAULT, DayInput
    confirmed=data.get('_agenda_confirmada') or (data.get('dias') is not None and data['dias'] != DEFAULT['dias'])
    unknown=dict(duracao_sugerida_minutos=None,origem_duracao='DESCONHECIDA',disponivel=True,
                 aviso='Disponibilidade não confirmada. Comece quando puder ou informe minutos para agora.')
    if not confirmed:return unknown
    local=now.replace(tzinfo=timezone.utc).astimezone(clock.TZ)
    day=next((d for d in data.get('dias',[]) if d.get('dia')==local.weekday()),None)
    if not day:return unknown
    try:DayInput.model_validate(day)
    except (ValueError,TypeError):return unknown
    if not day.get('inicio') or not day.get('fim'):
        return dict(duracao_sugerida_minutos=0,origem_duracao='AGENDA',disponivel=False,
                    aviso='Não há janela configurada hoje. Informe minutos se estiver disponível excepcionalmente.')
    def mins(value):
        h,m=map(int,value.split(':'));return 60*h+m
    current=local.hour*60+local.minute
    start,end=mins(day['inicio']),mins(day['fim'])
    # Conservative reserve: pauses may still be needed; no subtraction of weekly goals.
    remaining=max(0,end-current-day.get('pausas',0)) if start<=current<end else 0
    return dict(duracao_sugerida_minutos=min(50,remaining),origem_duracao='AGENDA',disponivel=remaining>=5,
                aviso=(f"Janela atual: {day['inicio']}–{day['fim']}; pausas preservadas." if remaining>=5 else
                       f"Fora de uma janela útil agora ({day['inicio']}–{day['fim']}). Informe minutos para uma disponibilidade excepcional."))


def purpose(session):
    return session.finalidade or ('REVISAO' if session.tipo_sessao=='REVISAO' else 'DESCONHECIDA')


def assessment(blocks, now):
    """Two substantive attempts on distinct local days; tiny later blocks do not erase evidence.
    Accuracy is descriptive. Unknown level never becomes 3 or a speed comparison.
    """
    substantial=[b for b in blocks if b.total_questoes>=10]
    pair=[]
    for b in reversed(substantial):
        if not pair or clock.local_date(b.data)!=clock.local_date(pair[0].data):pair.insert(0,b)
        if len(pair)==2:break
    total=sum(b.total_questoes for b in pair)
    enough=len(pair)==2 and total>=20
    accuracy=sum(b.total_acertos for b in pair)/total if total else None
    low=False;baseline=[]
    daily={clock.local_date(b.data):b for b in substantial}
    attempts=list(daily.values())
    for index in range(1,len(attempts)):
        previous,current=attempts[index-1:index+1]
        batch=[previous,current]
        ratio=sum(b.total_acertos for b in batch)/sum(b.total_questoes for b in batch)
        if ratio<.7:
            low=True;baseline=[b.dificuldade for b in batch if b.dificuldade_informada is True and b.dificuldade is not None]
        elif all(b.total_acertos/b.total_questoes>=.7 for b in batch):
            qualified=not baseline or all(b.dificuldade_informada is True and b.dificuldade is not None and b.dificuldade>=max(baseline) for b in batch)
            if qualified:low=False

    recurring=low and all(b.total_acertos/b.total_questoes<.7 for b in pair) and pair[0].data>=now-timedelta(days=60)
    known=[b.dificuldade for b in pair if b.dificuldade_informada is True and b.dificuldade is not None]
    # Conflicting known levels limit inference of recurrence and improvement.
    comparable=len(set(known))<=1
    return dict(critico=low,recorrente=recurring and comparable,
                estado='DIFICULDADE_OBSERVADA' if low else 'RESULTADOS_FAVORAVEIS' if enough and accuracy>=.7 and comparable else 'EVIDENCIA_INSUFICIENTE',
                precisao=round(accuracy*100,2) if total else None,questoes=total,tentativas=len(pair),
                nivel_comparavel=len(known)==2 and comparable,
                origem=clock.iso_utc(pair[0].data) if pair else None)


def snapshot(db, now):
    topics=db.query(models.Assunto).join(models.Materia).filter(models.Assunto.ativo.is_(True),models.Materia.ativa.is_(True)).all()
    lookup={t.id:t for t in db.query(models.Assunto).all()}
    subjects={m.id:m.nome for m in db.query(models.Materia).filter(models.Materia.ativa.is_(True)).all()}
    sessions=db.query(models.SessaoEstudo).filter(models.SessaoEstudo.data<=now).all()
    blocks=db.query(models.BlocoQuestoes).filter(models.BlocoQuestoes.data<=now).all()
    sm,bm,am=defaultdict(list),defaultdict(list),defaultdict(list)
    units=[]
    valid_sessions={s.id:s for s in sessions if s.assunto_id in lookup and lookup[s.assunto_id].materia_id==s.materia_id and session_seconds(s)>0}
    for s in valid_sessions.values():
        sm[s.assunto_id].append(s)
        units.append(dict(id=str(s.id),date=s.data,topic=s.assunto_id,purpose=purpose(s),kind=s.classe_revisao))
    for b in blocks:
        if b.assunto_id not in lookup or lookup[b.assunto_id].materia_id!=b.materia_id or not valid_questions(b):continue
        if b.sessao_id and (b.sessao_id not in valid_sessions or valid_sessions[b.sessao_id].assunto_id!=b.assunto_id):continue
        bm[b.assunto_id].append(b)
        if not b.sessao_id:units.append(dict(id=str(b.id),date=b.data,topic=b.assunto_id,purpose='DESCONHECIDA',kind=None))
    for action in db.query(AcaoEstudo).filter(AcaoEstudo.concluida_em.is_(None)).all():
        if action.assunto_id in lookup:am[action.assunto_id].append(action)
    errors=defaultdict(set)
    for error in db.query(models.ErroQuestao).all():
        if error.quantidade>0:errors[error.bloco_id].add(str(error.tipo_erro))
    records=[]
    for t in topics:
        ss=sorted(sm[t.id],key=lambda x:(x.data,str(x.id)))
        bs=sorted(bm[t.id],key=lambda x:(x.data,str(x.id)))
        contacts=sorted([*ss,*bs],key=lambda x:(x.data,str(x.id)))
        familiarity='REGISTRADO' if contacts else 'DECLARADO_ESTUDADO' if t.familiaridade_declarada=='ESTUDADO' else 'NAO_ESTUDADO' if t.familiaridade_declarada=='NAO_ESTUDADO' else 'DESCONHECIDO'
        records.append(dict(topic=t,subject=subjects[t.materia_id],sessions=ss,blocks=bs,contacts=contacts,
                            actions=sorted(am[t.id],key=lambda a:(a.prevista_em,str(a.id))),familiarity=familiarity,
                            evidence=assessment(bs,now),errors=errors))
    return records,sorted(units,key=lambda u:(u['date'],u['id']))


def candidates(records, units, now, cycle, policy):
    quotas={g['materia_id']:g['proporcao'] for g in cycle['metas'] if g['ativa']} if cycle else {}
    coverage=Counter(str(r['topic'].materia_id) for r in records if r['familiarity'] in ('REGISTRADO','DECLARADO_ESTUDADO'))
    productive=[];reviews=[]
    opportunity_dates=sorted(u["date"] for u in units if u["purpose"]!="REVISAO")
    for r in records:
        t=r['topic'];ss=r['sessions'];bs=r['blocks'];contacts=r['contacts'];ev=r['evidence']
        last=contacts[-1].data if contacts else None
        base=dict(materia_id=str(t.materia_id),materia=r['subject'],assunto_id=str(t.id),assunto=t.nome,
                  referencia=t.referencia,familiaridade=r['familiarity'],evidencia=ev,acao_id=None,
                  cota=quotas.get(str(t.materia_id)),cobertura=coverage[str(t.materia_id)],contato=last)
        def product(mode,activity,task,reason,rank,variant):
            productive.append(dict(base,finalidade=mode,atividade=activity,tarefa=task,motivo=reason,
                                   prioridade=rank,variante=variant,objetivo_revisao=None,classe_revisao=None))
        latest=ss[-1] if ss else None
        returns=[s for s in ss if purpose(s)=='REVISAO']
        latest_return=returns[-1] if returns else None
        if r['familiarity']=='DESCONHECIDO':
            product('AVANCO','TEORIA','Verifique o que reconhece neste assunto; tente um exemplo. Se for novo para você, comece pelo material introdutório.',
                    'Familiaridade desconhecida: comece com uma exploração breve, sem cadastro prévio.',2,'EXPLORACAO')
        elif r['familiarity']=='NAO_ESTUDADO':
            product('AVANCO','TEORIA','Inicie este assunto no seu material e tente reconstruir um exemplo.',
                    'Você indicou que ainda não estudou este assunto.',2,'NOVO')
        elif latest and last>=now-timedelta(days=7) and purpose(latest)!='REVISAO' and (not latest_return or latest.data>latest_return.data):
            if latest.proximo_passo:
                product('AVANCO','TEORIA',latest.proximo_passo,'Continuidade indicada na última sessão deste mesmo assunto.',1,'CONTINUIDADE')
            elif latest.tipo_sessao=='TEORIA' and (not bs or bs[-1].data<latest.data):
                product('CONSOLIDACAO','QUESTOES','Tente uma aplicação sem consulta e confira o raciocínio; registre as questões realizadas.',
                        'Teoria recente ainda sem aplicação registrada.',0,'APLICACAO')
            elif bs and len(bs)<2 and purpose(latest)!='CONSOLIDACAO':
                product('CONSOLIDACAO','QUESTOES','Tente uma nova aplicação e confira os erros; a amostra ainda é pequena.',
                        'Amostra insuficiente: uma aplicação ajuda a orientar a continuidade.',1,'APLICACAO')
        if r['familiarity'] not in ('REGISTRADO','DECLARADO_ESTUDADO'):continue
        kind='RECORRENTE' if ev['recorrente'] else 'MANUTENCAO'
        # One open scheduled goal per topic; future manual goals remain future.
        action=r['actions'][0] if r['actions'] else None
        if action and ev['recorrente'] and action.consequencia and action.uso_em and now<=action.uso_em<=now+timedelta(days=7):kind='PRIORITARIA'
        if action:
            due=action.prevista_em;origin='acao:'+str(action.id)
        elif latest_return:
            due=latest_return.data+timedelta(days=2)
            origin='retorno:'+str(latest_return.id)
        elif contacts:
            # Stable eligibility does not slide with every additional practice.
            first=contacts[0]
            initial_practice=hasattr(first,'total_questoes') or getattr(first,'tipo_sessao',None)=='QUESTOES'
            due=first.data+timedelta(days=1 if initial_practice else 7)
            origin='contato:'+str(first.id)
        else:
            due=t.familiaridade_alterada_em
            if due is None:continue  # No retroactive availability date invented.
            origin='declaracao:'+str(t.id)+':'+due.isoformat()
        b=len(opportunity_dates)-bisect_left(opportunity_dates,due)
        k=policy.limit(kind)
        recent=bs[-2:];n=sum(x.total_questoes for x in recent);hits=sum(x.total_acertos for x in recent)
        reason=('Dificuldade recorrente e uso próximo informado: '+action.consequencia if kind=='PRIORITARIA' else
                f'{hits} acertos em {n} questões nas duas últimas tentativas; verifique a dificuldade observada.' if ev['critico'] else
                'A última prática tem mais de 60 dias; verifique retenção, sem presumir esquecimento.' if bs and bs[-1].data<now-timedelta(days=60) else
                f'Amostra pequena: {n} questões em {len(recent)} tentativa(s); verifique o que consegue recuperar.' if len(recent)<2 or n<20 else
                'Retorno para verificar retenção; contato registrado não comprova domínio.')
        if r['familiarity']=='DECLARADO_ESTUDADO':reason='Você declarou já ter estudado; verifique o que consegue recuperar, sem estimativa de domínio.'
        if latest_return and ev['critico']:reason='Revisão realizada; a dificuldade observada ainda precisa de verificação por novas questões.'
        from .study_analysis import performance_change
        change=performance_change([b for b in bs if b.data>=now-timedelta(days=60)])
        classified=[b for b in bs if r['errors'][b.id] and b.total_acertos<b.total_questoes and (not latest_return or b.data>latest_return.data)]
        if classified:reason='Erros classificados pedem verificação; a classificação é um indício, não diagnóstico de causa.'
        if change:reason=change[2]
        task=action.descricao if action else 'Tente recuperar um conceito ou resolver uma questão sem consulta; confira a solução e corrija o que faltar.'
        if change and not action:task=change[3]
        activity='ANALISE_ERROS' if (action and action.causa) or classified else change[1] if change and not action else 'REVISAO' if ev['critico'] or n>=20 else 'QUESTOES'
        reviews.append(dict(base,id=origin,origem='PROGRAMADA' if action else 'AUTOMATICA',
                            finalidade='REVISAO',atividade=activity,
                            tarefa=task,motivo=reason,prevista_em=clock.iso_utc(due),disponivel=due<=now,
                            prioridade={'PRIORITARIA':1,'RECORRENTE':2,'MANUTENCAO':4}[kind],
                            acao_id=str(action.id) if action else None,objetivo_revisao=origin,classe_revisao=kind,
                            espera=b,limite=k,excesso=b-k,madura=b>=k,consequencia=action.consequencia if action else None))
    return productive,reviews


def ordered_reviews(rows):
    # Pairwise missing-data comparisons can be non-transitive: only use a
    # criterion when ALL candidates in this tier have comparable values.
    complete_quota=all(r.get('cota') is not None for r in rows)
    complete_date=all(r.get('contato') is not None for r in rows)
    return sorted(rows,key=lambda r:(not r['madura'],-r['excesso'] if r['madura'] else 0,r['prioridade'],
                                     not bool(r['consequencia']),r['cota'] if complete_quota else 0,
                                     r['contato'] if complete_date else datetime.min,r['prevista_em'],r['assunto_id']))


def select(productive, reviews, units, now, policy):
    recent=[u for u in units if u['date']>=now-timedelta(days=policy.recent_days)]
    counts=Counter(u['purpose'] for u in recent)
    available=[r for r in reviews if r['disponivel']]
    saturday=clock.local_date(now).weekday()==5
    if saturday:return (ordered_reviews(available)[0] if available else None),counts,'SABADO'
    # Fair productive ordering: observed imbalance only selects existing goals.
    missing_application=counts['CONSOLIDACAO']==0 and counts['AVANCO']>0
    missing_advance=counts['AVANCO']==0 and counts['CONSOLIDACAO']>0
    # Coverage outside a configured cycle is fallback; an actual application or
    # explicit continuation outside it can still compete for a pedagogical reason.
    if any(r['cota'] is not None for r in productive):
        productive=[r for r in productive if r['cota'] is not None or r['prioridade']<2]
    quota_known=all(r['cota'] is not None for r in productive)
    date_known=all(r['contato'] is not None for r in productive)
    def key(r):
        rank=r['prioridade']
        if missing_advance and r['finalidade']=='AVANCO':rank=-1
        if missing_application and r['variante']=='APLICACAO':rank=-1
        repeat=bool(recent and str(recent[-1]['topic'])==r['assunto_id'])
        return rank,r['cota'] if quota_known else 0,repeat,r['cobertura'],r['contato'] if date_known else datetime.min,r['assunto_id']
    productive=sorted(productive,key=key)
    # A Saturday review also preserves productive space on the following weekday.
    mixed=recent
    last_review=next((i for i in range(len(mixed)-1,-1,-1) if mixed[i]['purpose']=='REVISAO'),None)
    gap=sum(u['purpose'] in ('AVANCO','CONSOLIDACAO') for u in mixed[last_review+1:]) if last_review is not None else policy.productive_gap
    mature=ordered_reviews([r for r in available if r['madura']])
    if mature:
        chosen=mature[0]
        urgent_exception=(chosen['classe_revisao']=='PRIORITARIA' and gap>=1 and last_review is not None and mixed[last_review]['kind']!='PRIORITARIA')
        if not productive or gap>=policy.productive_gap or urgent_exception:
            return chosen,counts,'URGENCIA_DOCUMENTADA' if urgent_exception else 'OPORTUNIDADE_REVISIONAL'
    if productive:return productive[0],counts,'PROGRESSO_PROTEGIDO' if gap<policy.productive_gap else 'PROGRESSAO'
    return (ordered_reviews(available)[0] if available else None),counts,'SEM_PRODUTIVO'


def decide(db, now=None, minutes=None, policy=None):
    from .planner import cycle_view
    now=clock.utc_naive(now or clock.utcnow());policy=policy or Policy.configured()
    cycle=cycle_view(db);records,units=snapshot(db,now)
    productive,reviews=candidates(records,units,now,cycle,policy)
    # Saturday's fallback is diagnostic ONLY for known topics; future manual
    # actions are never pulled forward. Completed same-day reviews stay closed.
    if clock.local_date(now).weekday()==5:
        by_id={str(r['topic'].id):r for r in records}
        for row in reviews:
            r=by_id[row['assunto_id']]
            done_today=any(purpose(s)=='REVISAO' and clock.local_date(s.data)==clock.local_date(now) for s in r['sessions'])
            if not row['disponivel'] and row['origem']=='AUTOMATICA' and not done_today:
                row['disponivel']=True;row['motivo']='Sábado: verifique a retenção de um assunto já estudado.'
    chosen,counts,rule=select(productive,reviews,units,now,policy)
    timing=availability(db,now,minutes)
    reason=None
    if not timing['disponivel']:chosen=None;reason=timing['aviso']
    elif not chosen:reason=('Sábado é revisional. Não há retorno disponível de assunto conhecido. Você pode indicar um assunto já estudado em Conteúdos.' if clock.local_date(now).weekday()==5 else 'Não há atividade elegível agora. Consulte seus conteúdos ou informe uma continuidade no próximo registro.')
    if chosen:
        chosen={**chosen,**timing,'regra':rule,'explicacao':chosen['motivo']}
        if chosen.get('acao_id') and chosen['duracao_sugerida_minutos'] is not None:
            chosen['tarefa']='Faça uma tentativa ou correção deste objetivo dentro do tempo disponível: '+chosen['tarefa']
        if rule=='OPORTUNIDADE_REVISIONAL' and chosen.get('madura'):
            chosen['explicacao']+=f" Retorno disponível durante {chosen['espera']} atividades concluídas."
        if rule=='PROGRESSO_PROTEGIDO':chosen['explicacao']+=' Avanço e consolidação têm espaço protegido após as revisões recentes.'
        if rule=='SEM_PRODUTIVO':chosen['explicacao']+=' Não há avanço ou consolidação com objetivo atual identificado.'
        chosen.pop('contato',None)
    return dict(ciclo=cycle,recomendacao=chosen,motivo=reason,contagens={p:counts[p] for p in ('AVANCO','CONSOLIDACAO','REVISAO','DESCONHECIDA')},disponibilidade=timing)


def queue(db, now=None, topic_ids=None):
    from .planner import cycle_view
    now=clock.utc_naive(now or clock.utcnow())
    records,units=snapshot(db,now)
    _,rows=candidates(records,units,now,cycle_view(db),Policy.configured())
    if topic_ids is not None:rows=[r for r in rows if r['assunto_id'] in topic_ids]
    ordered=ordered_reviews(rows)
    for r in ordered:r.pop('contato',None)
    return ordered
