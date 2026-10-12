"""Executable R01–R34 + T01–T15. Isolated records, deterministic local dates."""
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from test_flows import env, catalog
from app import models, planner, clock, goals, metrics
from app.planning_models import ConfigMetas, AcaoEstudo
from app.recommender import decide, snapshot, queue, select, Policy, assessment

MONDAY=datetime(2026,9,21,15)


@pytest.fixture
def world(env,monkeypatch):
    c,e=env;now=[MONDAY]
    for module in (clock,planner,goals,metrics):monkeypatch.setattr(module,'utcnow',lambda:now[0])
    (m,a),(n,b)=catalog(c)
    return c,e,now,m,a,n,b


def session(w,topic=None,mode='AVANCO',days=0,when=None,activity=None,linked=False):
    c,e,now,m,a,n,b=w;topic=topic or b;mid=m if topic==a else n
    with Session(e) as db:
        t=db.get(models.Assunto,UUID(topic));mid=t.materia_id
        s=models.SessaoEstudo(materia_id=mid,assunto_id=t.id,data=when or now[0]-timedelta(days=days,minutes=1),
                             tipo_sessao=activity or ('REVISAO' if mode=='REVISAO' else 'TEORIA'),
                             atividade=activity or ('REVISAO' if mode=='REVISAO' else 'TEORIA'),
                             finalidade=mode,minutos_liquidos=15,segundos_exatos=900)
        db.add(s);db.flush()
        if linked:db.add(models.BlocoQuestoes(materia_id=mid,assunto_id=t.id,data=s.data,sessao_id=s.id,total_questoes=10,total_acertos=8))
        id=str(s.id);db.commit();return id


def practice(w,topic=None,days=3,hits=4,total=10,difficulty=None):
    c,e,now,m,a,n,b=w;topic=topic or a
    with Session(e) as db:
        t=db.get(models.Assunto,UUID(topic))
        record=models.BlocoQuestoes(materia_id=t.materia_id,assunto_id=t.id,data=now[0]-timedelta(days=days),
            total_questoes=total,total_acertos=hits,dificuldade=difficulty,dificuldade_informada=difficulty is not None)
        db.add(record);db.commit();return str(record.id)


def declaration(w,topic=None,value='ESTUDADO',days=10):
    c,e,now,m,a,n,b=w;topic=topic or a
    with Session(e) as db:
        t=db.get(models.Assunto,UUID(topic));t.familiaridade_declarada=value;t.familiaridade_alterada_em=now[0]-timedelta(days=days);db.commit()


def opportunities(w,count=4):
    for i in range(count):session(w,when=w[2][0]-timedelta(hours=count-i))


def result(w,minutes=None):
    with Session(w[1]) as db:return decide(db,now=w[2][0],minutes=minutes)


def rec(w,minutes=None):return result(w,minutes)['recomendacao']


def rows(w):
    with Session(w[1]) as db:return queue(db,now=w[2][0])


def complete_recommendation(w,r):
    c,e,now,*_=w
    payload=dict(chave_registro=str(uuid4()),materia_id=r['materia_id'],assunto_id=r['assunto_id'],
                 data=clock.iso_utc(now[0]),segundos=900,atividade=r['atividade'],finalidade=r['finalidade'],
                 objetivo_revisao=r.get('objetivo_revisao'),classe_revisao=r.get('classe_revisao'))
    if r['acao_id']:payload.update(acao_id=r['acao_id'],resultado_acao='CONSEGUI')
    response=c.post('/api/v1/estudos/concluir',json=payload);assert response.status_code==201,response.text
    now[0]+=timedelta(minutes=16)
    return payload


def test_R01_automatic_and_T09_no_history(world):
    r=rec(world)
    assert r['finalidade']=='AVANCO' and r['variante']=='EXPLORACAO'
    assert r['assunto_id'] in (world[4],world[6]) and r['atividade']=='TEORIA'
    assert r['evidencia']['precisao'] is None and r['duracao_sugerida_minutos'] is None


def test_R02_backlog_is_not_urgency(world):
    declaration(world,days=300);opportunities(world)
    r=rec(world);assert r['classe_revisao']=='MANUTENCAO'
    complete_recommendation(world,r)
    assert rec(world)['finalidade']!='REVISAO'


def test_R03_multiple_blocks(world):
    declaration(world);opportunities(world)
    assert rec(world)['finalidade']=='REVISAO'
    complete_recommendation(world,rec(world));assert rec(world)['finalidade']!='REVISAO'


def test_R04_unknown_activity_does_not_release_guard(world):
    declaration(world);opportunities(world)
    session(world,mode='REVISAO',when=MONDAY-timedelta(minutes=5))
    session(world,mode=None,when=MONDAY-timedelta(minutes=2))
    assert rec(world)['finalidade']!='REVISAO'
    assert result(world)['contagens']['DESCONHECIDA']==1


def test_R05_favorable_results_release_new_content(world):
    declaration(world,world[6],value='NAO_ESTUDADO')
    session(world,world[4],mode='CONSOLIDACAO',days=1,activity='QUESTOES')
    practice(world,days=2,hits=9);practice(world,days=1,hits=9)
    assert rec(world)['assunto_id']==world[6] and rec(world)['finalidade']=='AVANCO'


def test_R06_T04_saturday_known_only(world):
    declaration(world,world[6],value='NAO_ESTUDADO');session(world,world[4],days=1)
    world[2][0]=MONDAY+timedelta(days=5)
    r=rec(world);assert r['assunto_id']==world[4] and r['finalidade']=='REVISAO'


def test_R07_saturday_unplanned_retention(world):
    session(world,world[4]);world[2][0]+=timedelta(days=5)
    assert not rows(world)[0]['disponivel']
    assert rec(world)['finalidade']=='REVISAO'


def test_R08_T05_saturday_empty(world):
    world[2][0]+=timedelta(days=5)
    assert rec(world) is None and 'Sábado' in result(world)['motivo']


def configure(w,day=6,start='11:00',end='14:00'):
    data=deepcopy(goals.DEFAULT);data['_agenda_confirmada']=True
    data['dias'][day]=dict(dia=day,inicio=start,fim=end,pausas=0,minutos=min(60,(int(end[:2])*60+int(end[3:]))-(int(start[:2])*60+int(start[3:]))) if start else 0)
    with Session(w[1]) as db:
        conf=db.get(ConfigMetas,1)
        if conf:conf.dados=data
        else:db.add(ConfigMetas(id=1,dados=data))
        db.commit()


def test_R09_sunday_current_window(world):
    world[2][0]+=timedelta(days=6);configure(world)
    assert rec(world)['duracao_sugerida_minutos']==50
    configure(world,start=None,end=None)
    assert rec(world) is None
    assert rec(world,15)['duracao_sugerida_minutos']==15


def test_R10_short_or_unusable_window_preserves_age(world):
    declaration(world);opportunities(world)
    assert rec(world,5)['finalidade']=='REVISAO'
    before=rows(world)[0]['espera'];assert rec(world,2) is None
    assert rows(world)[0]['espera']==before


def test_R11_current_schedule_not_legacy(world):
    configure(world,day=0,start='11:45',end='12:15')
    assert rec(world)['duracao_sugerida_minutos']==15
    assert rec(world)['origem_duracao']=='AGENDA'


def test_R12_short_failure_unknown_level(world):
    practice(world,hits=0,total=3)
    r=rows(world)[0]
    assert r['classe_revisao']=='MANUTENCAO' and not r['evidencia']['critico']
    assert r['evidencia']['estado']=='EVIDENCIA_INSUFICIENTE'


def test_R13_T06_review_does_not_erase_difficulty(world):
    practice(world,days=5);practice(world,days=3)
    session(world,world[4],mode='REVISAO')
    r=rows(world)[0]
    assert r['evidencia']['critico'] and not r['disponivel']
    assert 'ainda precisa' in r['motivo']
    assert rec(world)['finalidade']=='AVANCO'


def test_R14_new_failure_new_episode(world):
    practice(world,days=5);practice(world,days=3)
    old=rows(world)[0]['objetivo_revisao']
    id=session(world,world[4],mode='REVISAO')
    practice(world,days=0)
    new=rows(world)[0]
    assert new['objetivo_revisao']!=old and id in new['objetivo_revisao']
    assert new['espera']==0 and new['evidencia']['critico']


def test_R15_T13_question_bank_isolation(world):
    c,e,*_=world;before=result(world)
    dashboard=c.get('/api/v1/performance/dashboard?periodo=total').json()
    with e.begin() as conn:
        conn.execute(text("ATTACH DATABASE ':memory:' AS question_bank"))
        conn.execute(text('CREATE TABLE question_bank.answers (id TEXT, correct BOOLEAN, answered_at TEXT)'))
        conn.execute(text("INSERT INTO question_bank.answers VALUES ('1',1,'2026-09-21')"))
        conn.execute(text('CREATE TABLE question_bank.solved_questions (question_id TEXT, correct BOOLEAN)'))
        conn.execute(text("INSERT INTO question_bank.solved_questions VALUES ('1',1)"))
    assert result(world)==before
    after=c.get('/api/v1/performance/dashboard?periodo=total').json()
    assert (after['horas_liquidas'],after['total_questoes'])==(dashboard['horas_liquidas'],dashboard['total_questoes'])


def test_R16_T11_read_only_refresh(world):
    declaration(world);opportunities(world);c,e,*_=world
    first=c.get('/api/v1/estudos/agora').json()
    with Session(e) as db:before=(db.query(models.SessaoEstudo).count(),db.query(AcaoEstudo).count())
    for _ in range(5):assert c.get('/api/v1/estudos/agora').json()==first
    with Session(e) as db:assert (db.query(models.SessaoEstudo).count(),db.query(AcaoEstudo).count())==before


def test_R17_T08_global_cycle_vs_recurring(world):
    c,e,now,m,a,n,b=world
    practice(world,days=5);practice(world,days=3);opportunities(world,2)
    response=c.post('/api/v1/estudos/ciclo',json={'metas':[{'materia_id':m,'minutos':1},{'materia_id':n,'minutos':600}]});assert response.status_code==201
    with Session(e) as db:
        s=db.query(models.SessaoEstudo).first();s.materia_id=UUID(m);s.assunto_id=UUID(a);s.ciclo_id=UUID(response.json()['id']);db.commit()
    r=rec(world);assert r['assunto_id']==a and r['classe_revisao']=='RECORRENTE'
    complete_recommendation(world,r);assert rec(world)['finalidade']!='REVISAO'


def test_R18_active_draft_is_client_owned_and_reads_create_no_sessions(world):
    # Browser-level assertion of resumption is in stage3Recommender.test.tsx.
    c,e,*_=world
    for _ in range(3):c.get('/api/v1/estudos/agora')
    with Session(e) as db:assert db.query(models.SessaoEstudo).count()==0


def test_R19_dashboard_reuses_main_decision(world):
    c,*_=world;r=rec(world)
    card=c.get('/api/v1/performance/dashboard').json()['orientacoes'][0]
    assert card['assunto']==r['assunto'] and card['acao']==r['tarefa']
    assert card['motivo']==r['explicacao'] and card['destino']=='/estudar'


def test_R20_future_action_stays_future(world):
    declaration(world);opportunities(world,10)
    with Session(world[1]) as db:
        db.add(AcaoEstudo(assunto_id=UUID(world[4]),descricao='Retomar',prevista_em=MONDAY+timedelta(days=8)));db.commit()
    r=rows(world)[0];assert not r['disponivel'] and r['classe_revisao']=='MANUTENCAO'
    assert rec(world)['finalidade']!='REVISAO'


def test_R21_one_block_unripe(world):
    declaration(world);opportunities(world,1)
    assert rec(world,15)['finalidade']!='REVISAO'
    complete_recommendation(world,rec(world,15))
    assert next(r for r in rows(world) if r['assunto_id']==world[4])['espera']==2


def test_R22_T01_one_block_mature_guaranteed(world):
    declaration(world);opportunities(world,4)
    r=rec(world,15);assert r['finalidade']=='REVISAO' and r['espera']==4 and r['limite']==4


def test_R23_old_wait_beats_new_priority():
    def row(id,b,k,kind):return dict(assunto_id=id,disponivel=True,madura=True,espera=b,excesso=b-k,prioridade=1 if kind=='PRIORITARIA' else 4,classe_revisao=kind,consequencia='uso próximo' if kind=='PRIORITARIA' else None,cota=0,contato=None,prevista_em='2026-09-01')
    chosen,_,_=select([], [row('old',6,4,'MANUTENCAO'),row('new',1,1,'PRIORITARIA')],[],MONDAY,Policy())
    assert chosen['assunto_id']=='old'


def test_R24_wait_crosses_weeks_and_recent_window(world):
    declaration(world,days=40)
    for days in (30,25,20,15):session(world,days=days)
    r=rec(world);assert r['espera']==4 and r['finalidade']=='REVISAO'
    assert result(world)['contagens']['AVANCO']==0


def test_R25_successive_reviews_protect_productivity(world):
    declaration(world);opportunities(world)
    session(world,mode='REVISAO',when=MONDAY-timedelta(minutes=4));session(world,mode='REVISAO',when=MONDAY-timedelta(minutes=2))
    # Another unknown topic offers real progression, without renaming old recovery.
    c,e,now,m,a,n,b=world
    c.post('/api/v1/performance/assuntos',json={'materia_id':n,'nome':'Novo candidato','semana_do_ciclo':1})
    assert rec(world)['finalidade']=='AVANCO'


def test_R26_declared_studied_no_fabricated_metrics(world):
    declaration(world);world[2][0]+=timedelta(days=5)
    r=rec(world);assert r['familiaridade']=='DECLARADO_ESTUDADO' and r['classe_revisao']=='MANUTENCAO'
    assert r['evidencia']['precisao'] is None
    with Session(world[1]) as db:assert db.query(models.SessaoEstudo).count()==0


def test_R27_explicit_new_weekday_and_saturday(world):
    declaration(world,world[4],'NAO_ESTUDADO');declaration(world,world[6],'NAO_ESTUDADO')
    assert rec(world)['variante']=='NOVO'
    world[2][0]+=timedelta(days=5);assert rec(world) is None


def test_R28_T03_unknown_can_start_and_continue(world):
    r=rec(world);assert r['variante']=='EXPLORACAO'
    complete_recommendation(world,r)
    r=rec(world);assert r['finalidade']=='CONSOLIDACAO' and r['familiaridade']=='REGISTRADO'


def test_R29_saturday_multiple_reviews_no_productive_guard(world):
    declaration(world);declaration(world,world[6]);world[2][0]+=timedelta(days=5)
    first=rec(world);complete_recommendation(world,first)
    second=rec(world);assert second['finalidade']=='REVISAO' and second['assunto_id']!=first['assunto_id']


def test_R30_saturday_known_record_or_declaration(world):
    session(world,world[4],days=20);declaration(world,world[6]);world[2][0]+=timedelta(days=5)
    with Session(world[1]) as db:assert db.query(AcaoEstudo).count()==0
    assert rec(world)['finalidade']=='REVISAO'


def test_R31_no_curricular_order_id_tiebreak(world):
    c,e,now,m,a,n,b=world
    with Session(e) as db:
        for t in db.query(models.Assunto):t.ordem=999 if str(t.id)==min(a,b) else 0
        db.commit()
    r=rec(world);assert r['assunto_id']==min(a,b)
    assert not any(word in r['tarefa'].lower() for word in ('próximo capítulo','pré-requisito','subassunto'))


def test_R32_insufficient_known_performance(world):
    declaration(world);world[2][0]+=timedelta(days=5)
    r=rec(world);assert r['classe_revisao']=='MANUTENCAO' and r['evidencia']['estado']=='EVIDENCIA_INSUFICIENTE'


def test_R33_dedup_and_other_review_keeps_wait(world):
    declaration(world);session(world,linked=True)
    for i in range(3):practice(world,world[6],days=1,hits=8)
    session(world,mode='REVISAO')
    r=next(r for r in rows(world) if r['assunto_id']==world[4]);assert r['espera']==4
    with Session(world[1]) as db:
        _,units=snapshot(db,MONDAY)
        assert len(units)==5


def test_R34_conflict_and_removal(world):
    declaration(world,value='NAO_ESTUDADO');session(world,world[4]);declaration(world,world[6])
    c,e,*_=world
    assert c.patch(f'/api/v1/estudos/assuntos/{world[6]}/familiaridade',json={'declaracao':None}).status_code==200
    states={r['id']:r['familiaridade'] for r in c.get('/api/v1/estudos/cobertura').json()}
    assert states[world[4]]=='REGISTRADO' and states[world[6]]=='DESCONHECIDO'


def test_T02_backlog_long_run_actual_completions(world):
    c,e,now,m,a,n,b=world
    with Session(e) as db:
        for i in range(12):db.add(models.Assunto(materia_id=UUID(m),nome=f'Antigo {i}',semana_do_ciclo=1,familiaridade_declarada='ESTUDADO',familiaridade_alterada_em=MONDAY-timedelta(days=20)))
        for i in range(30):db.add(models.Assunto(materia_id=UUID(n),nome=f'Explorar {i}',semana_do_ciclo=1))
        db.commit()
    opportunities(world)
    modes=[];reviewed=set()
    for _ in range(36):
        r=rec(world);modes.append(r['finalidade'])
        if r['finalidade']=='REVISAO':reviewed.add(r['assunto_id'])
        complete_recommendation(world,r)
    indices=[i for i,m in enumerate(modes) if m=='REVISAO']
    assert len(indices)>=10 and len(reviewed)>=10
    assert all(b-a>=3 for a,b in zip(indices,indices[1:]))
    assert len(indices)<len(modes)/2


def test_T07_consistent_improvement_not_one_tiny_or_easy_block(world):
    practice(world,days=6,difficulty=3);practice(world,days=5,difficulty=3)
    practice(world,days=4,hits=1,total=1,difficulty=3)
    practice(world,days=3,hits=10,difficulty=3)
    assert rows(world)[0]['evidencia']['critico']
    practice(world,days=2,hits=10,difficulty=1)
    assert rows(world)[0]['evidencia']['critico']
    practice(world,days=1,hits=10,difficulty=3);practice(world,days=0,hits=10,difficulty=3)
    assert not rows(world)[0]['evidencia']['critico'] and rows(world)[0]['evidencia']['estado']=='RESULTADOS_FAVORAVEIS'


def test_T10_unknown_difficulty_time_no_speed_or_fabrication(world):
    for days in (5,4,3,2):practice(world,days=days,hits=8)
    row=rows(world)[0];assert row['classe_revisao']=='MANUTENCAO' and not row['evidencia']['nivel_comparavel']
    assert 'tempo por questão' not in row['motivo']
    with Session(world[1]) as db:assert all(b.dificuldade is None and b.tempo_total_segundos is None for b in db.query(models.BlocoQuestoes))


def test_T12_T15_completion_idempotency_and_legacy_unknown(world):
    c,e,*_=world;session(world,mode=None,activity='QUESTOES',days=2)
    before=c.get('/api/v1/performance/dashboard?periodo=total').json()['horas_liquidas']
    r=rec(world)
    for _ in range(3):c.get('/api/v1/estudos/agora')
    assert c.get('/api/v1/performance/dashboard?periodo=total').json()['horas_liquidas']==before
    payload=complete_recommendation(world,r)
    assert c.post('/api/v1/estudos/concluir',json=payload).json()['repetido']
    assert result(world)['contagens']['DESCONHECIDA']==1
    with Session(e) as db:
        ss=db.query(models.SessaoEstudo).all();assert len(ss)==2 and sum(s.finalidade is None for s in ss)==1


@pytest.mark.parametrize('utc_hour,zone,expected',[(2,'America/Maceio',False),(3,'America/Maceio',True),(2,'UTC',True)])
def test_T14_timezone_day_transition(world,monkeypatch,utc_hour,zone,expected):
    monkeypatch.setattr(clock,'TZ',ZoneInfo(zone));declaration(world)
    world[2][0]=datetime(2026,9,26,utc_hour)
    assert (rec(world)['finalidade']=='REVISAO') is expected


def test_policy_validation():
    with pytest.raises(ValueError):Policy(priority=5)
    with pytest.raises(ValueError):Policy(productive_gap=1)


def test_urgent_exception_needs_evidence_consequence_and_productive_block(world):
    practice(world,days=5);practice(world,days=3);opportunities(world,4)
    session(world,mode='REVISAO',when=MONDAY-timedelta(minutes=30))
    session(world,mode='AVANCO',when=MONDAY-timedelta(minutes=10))
    with Session(world[1]) as db:
        db.add(AcaoEstudo(assunto_id=UUID(world[4]),descricao='Verificar antes do uso',prevista_em=MONDAY-timedelta(days=2),consequencia='Prova do assunto',uso_em=MONDAY+timedelta(days=1)));db.commit()
    r=rec(world);assert r['classe_revisao']=='PRIORITARIA' and r['regra']=='URGENCIA_DOCUMENTADA'
    complete_recommendation(world,r);assert rec(world)['finalidade']!='REVISAO'


def test_cycle_incomplete_does_not_disappear_behind_unknown_quota(world):
    c,e,now,m,a,n,b=world
    assert c.post('/api/v1/estudos/ciclo',json={'metas':[{'materia_id':m,'minutos':60}]}).status_code==201
    assert rec(world)['assunto_id']==a
    with Session(e) as db:
        topic=db.get(models.Assunto,UUID(a));topic.ativo=False;db.commit()
    assert rec(world)['assunto_id']==b  # Useful fallback, no invented quota.


def test_incomplete_availability_still_allows_start(world):
    with Session(world[1]) as db:
        db.add(ConfigMetas(id=1,dados={'dias':[{'dia':0,'inicio':'invalid'}],'_agenda_confirmada':True}));db.commit()
    r=rec(world);assert r and r['duracao_sugerida_minutos'] is None
