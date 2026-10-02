"""Isolated HTTP/ORM tests; TEST_DATABASE_URL must never point to user data."""
import os
os.environ.setdefault('DATABASE_URL','sqlite://')
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from app import models, services
from app.planning_models import Planejamento, Ciclo, MetaCiclo, AcaoEstudo
from app.clock import utcnow, iso_utc, local_date, month_bounds
from app.metrics import precisao

@pytest.fixture
def env():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    @event.listens_for(engine,'connect')
    def enable_fk(conn,record):conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as db:db.add(Planejamento(id=1));db.commit()
    def override():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_db]=override
    client=TestClient(app)
    yield client,engine
    app.dependency_overrides.clear();engine.dispose()

def catalog(client):
    def subject(name):
        r=client.post('/api/v1/performance/materias',json={'nome':name,'peso_prova':1});assert r.status_code==201,r.text
        m=r.json()['id']
        r=client.post('/api/v1/performance/assuntos',json={'nome':'Assunto '+name,'materia_id':m,'semana_do_ciclo':1});assert r.status_code==201,r.text
        return m,r.json()['id']
    return subject('Matemática'),subject('Física')

def complete_data(m,a,**changes):
    return dict(chave_registro=str(uuid4()),materia_id=m,assunto_id=a,data=iso_utc(utcnow()-timedelta(seconds=1)),segundos=3600,atividade='QUESTOES',bloco={'total_questoes':20,'total_acertos':16},**changes)

def test_empty_routes(env):
    c,e=env
    for url in ['/configuracoes/materias','/configuracoes/assuntos','/api/v1/performance/dashboard','/api/v1/performance/analytics','/api/v1/performance/assuntos?skip=0&limit=20','/api/v1/estudos/agora','/api/v1/estudos/cobertura','/api/v1/estudos/series','/api/v1/performance/relatorio/mensal?mes=8&ano=2026']:
        r=c.get(url);assert r.status_code==200,(url,r.text)
    d=c.get('/api/v1/performance/dashboard').json();assert not d['tem_evidencia'];assert 'Pare questões' not in str(d)

@pytest.mark.parametrize('kind,extra',[('simulados',{'numero_ciclo':1,'numero_semana':1}),('blocos',{'dificuldade':3})])
def test_bad_counts(env,kind,extra):
    c,e=env;(m,a),_=catalog(c)
    payload={'total_questoes':10,'total_acertos':11,'tempo_total_segundos':600,**extra}
    if kind=='blocos':payload.update(materia_id=m,assunto_id=a)
    assert c.post('/api/v1/performance/'+kind,json=payload).status_code==422

def test_cross_subject_rejected(env):
    c,e=env;(m,a),(n,b)=catalog(c)
    r=c.post('/api/v1/performance/sessoes',json={'materia_id':m,'assunto_id':b,'tipo_sessao':'TEORIA','minutos_liquidos':60})
    assert r.status_code==422
    with Session(e) as db:assert db.query(models.SessaoEstudo).count()==0

def test_future_rejected(env):
    c,e=env;(m,a),_=catalog(c)
    p={'materia_id':m,'assunto_id':a,'tipo_sessao':'TEORIA','minutos_liquidos':60,'data':iso_utc(utcnow()+timedelta(days=2))}
    assert c.post('/api/v1/performance/sessoes',json=p).status_code==422

def test_subject_excludes_global_simulation(env):
    c,e=env;(m,a),_=catalog(c)
    r=c.post('/api/v1/performance/simulados',json={'numero_ciclo':1,'numero_semana':1,'total_questoes':70,'total_acertos':56,'tempo_total_segundos':14000});assert r.status_code==201,r.text
    d=c.get(f'/api/v1/performance/dashboard?periodo=total&materia_id={m}').json()
    assert (d['total_questoes'],d['percentual_medio'],d['horas_liquidas'])==(0,0,0)
    d=c.get('/api/v1/performance/dashboard?periodo=total').json();assert d['ipr_geral']==80;assert d['total_acertos']==56

def test_integrated_idempotency_hours_and_edit(env):
    c,e=env;(m,a),_=catalog(c)
    payload=complete_data(m,a)
    r=c.post('/api/v1/estudos/concluir',json=payload);assert r.status_code==201,r.text
    id=r.json()['sessao_id'];assert c.post('/api/v1/estudos/concluir',json=payload).json()['repetido']
    assert c.post('/api/v1/estudos/concluir',json={**payload,'segundos':60}).status_code==409
    d=c.get('/api/v1/performance/dashboard?periodo=total').json();assert d['horas_liquidas']==1;assert d['total_questoes']==20
    r=c.put(f'/api/v1/estudos/sessoes/{id}',json={'materia_id':m,'assunto_id':a,'tipo_sessao':'QUESTOES','minutos_liquidos':30,'data':payload['data']});assert r.status_code==200,r.text
    assert c.get('/api/v1/performance/dashboard?periodo=total').json()['horas_liquidas']==.5
    with Session(e) as db:
        assert db.query(models.SessaoEstudo).count()==1;assert db.query(models.BlocoQuestoes).count()==1
        assert db.query(models.BlocoQuestoes).first().tempo_total_segundos==1800
    day=local_date(datetime.fromisoformat(payload['data']))
    report=c.get(f'/api/v1/performance/relatorio/mensal?mes={day.month}&ano={day.year}')
    assert report.status_code==200,report.text
    assert report.json()['resumo_geral']['horas_totais']==.5

def test_cycle_and_override_and_no_history_rewrite(env):
    c,e=env;(m,a),(n,b)=catalog(c)
    # Existing session does not silently enter a new cycle.
    c.post('/api/v1/performance/sessoes',json={'materia_id':m,'assunto_id':a,'tipo_sessao':'TEORIA','minutos_liquidos':100})
    goals={'nome':'Ciclo teste','metas':[{'materia_id':m,'minutos':60},{'materia_id':n,'minutos':60}]}
    r=c.post('/api/v1/estudos/ciclo',json=goals);assert r.status_code==201,r.text
    assert all(g['segundos_consumidos']==0 for g in r.json()['metas'])
    assert c.post('/api/v1/estudos/ciclo',json=goals).status_code==409
    first=c.get('/api/v1/estudos/agora').json()['recomendacao'];assert first['materia_id']==m
    p=complete_data(m,a);p['data']=iso_utc(utcnow());assert c.post('/api/v1/estudos/concluir',json=p).status_code==201
    assert c.get('/api/v1/estudos/agora').json()['recomendacao']['materia_id']==n
    p=complete_data(n,b);p['data']=iso_utc(utcnow());assert c.post('/api/v1/estudos/concluir',json=p).status_code==201
    assert c.get('/api/v1/estudos/ciclo').json()['completo']
    assert c.post('/api/v1/estudos/ciclo',json=goals).status_code==201
    with Session(e) as db:assert db.query(Ciclo).count()==2;assert db.query(models.SessaoEstudo).count()==3

def test_never_studied_and_recent_evidence(env):
    c,e=env;(m,a),(n,b)=catalog(c)
    coverage=c.get('/api/v1/estudos/cobertura').json();assert len(coverage)==2;assert all(t['estado']=='SEM REGISTRO' for t in coverage)
    p=complete_data(m,a);c.post('/api/v1/estudos/concluir',json=p)
    t=next(x for x in c.get('/api/v1/estudos/cobertura').json() if x['id']==a)
    assert t['estado']=='POUCA PRÁTICA';assert t['precisao']==80;assert t['total_questoes']==20

def test_action_and_atomic_failure(env):
    c,e=env;(m,a),(n,b)=catalog(c)
    r=c.post('/api/v1/estudos/acoes',json={'assunto_id':a,'descricao':'Refazer questão 12','causa':'CALCULO'});assert r.status_code==201,r.text
    action=r.json()['id']
    p=complete_data(n,b,acao_id=action,resultado_acao='CONSEGUI')
    assert c.post('/api/v1/estudos/concluir',json=p).status_code==422
    with Session(e) as db:assert db.query(models.SessaoEstudo).count()==0
    p=complete_data(m,a,acao_id=action,resultado_acao='CONSEGUI')
    assert c.post('/api/v1/estudos/concluir',json=p).status_code==201
    assert c.get('/api/v1/estudos/cobertura').json()[0]['pendencias']==[]

def test_redacao_validation_and_status(env):
    c,e=env
    p={'tema':'Tema teste','competencia1':160,'competencia2':160,'competencia3':160,'competencia4':160,'competencia5':160}
    assert c.post('/api/v1/performance/redacoes',json={**p,'tema':'  '}).status_code==422
    assert c.post('/api/v1/performance/redacoes',json={**p,'tempo_escrita_min':-2}).status_code==422
    r=c.post('/api/v1/performance/redacoes',json=p);assert r.status_code==201,r.text
    assert r.json()['status']=='muito_boa';assert r.json()['nota_total']==800
    assert c.get('/api/v1/performance/redacoes/'+r.json()['id']).status_code==200

def test_utc_and_rounding(env):
    c,e=env;(m,a),_=catalog(c)
    p=complete_data(m,a);p['segundos']=25
    assert c.post('/api/v1/estudos/concluir',json=p).status_code==201
    s=c.get('/api/v1/performance/sessoes').json()[0]
    assert s['data'].endswith('+00:00');assert s['segundos_exatos']==25
    assert local_date(datetime(2026,9,15,2)).isoformat()=='2026-09-14'
    assert month_bounds(2026,9)[0]==datetime(2026,9,1,3)

def test_mean_independent_of_block_grouping():
    from types import SimpleNamespace as N
    assert precisao([N(total_questoes=1,total_acertos=0),N(total_questoes=99,total_acertos=99)])==precisao([N(total_questoes=100,total_acertos=99)])

def test_pagination_and_extended_contract(env):
    c,e=env;(m,a),_=catalog(c)
    assert 'ordem' in c.get('/configuracoes/assuntos').json()[0]
    assert 'peso_prova' in c.get('/configuracoes/materias').json()[0]
    with Session(e) as db:
        from uuid import UUID
        db.add_all([models.SessaoEstudo(materia_id=UUID(m),assunto_id=UUID(a),tipo_sessao='TEORIA',minutos_liquidos=1) for _ in range(105)]);db.commit()
    assert len(c.get('/api/v1/performance/sessoes?skip=100&limit=100').json())==5
    assert c.get('/api/v1/performance/assuntos?skip=-1').status_code==422

def test_subject_aggregation_uses_linked_time_once(env):
    c,e=env;(m,a),_=catalog(c)
    assert c.post('/api/v1/estudos/concluir',json=complete_data(m,a)).status_code==201
    rows=c.get('/api/v1/estudos/materias-performance?periodo=total')
    assert rows.status_code==200,rows.text
    row=next(r for r in rows.json() if r['materia']['id']==m)
    assert row['horas_estudo']==1 and row['ipr']==80 and row['total_questoes']==20

def test_invalid_legacy_record_preserved_and_not_counted(env):
    c,e=env;(m,a),_=catalog(c)
    r=c.post('/api/v1/estudos/concluir',json=complete_data(m,a));assert r.status_code==201
    with Session(e) as db:
        block=db.query(models.BlocoQuestoes).one();block.total_acertos=21;db.commit()
    d=c.get('/api/v1/performance/dashboard?periodo=total').json()
    assert d['total_questoes']==0 and d['registros_inconsistentes']==1 and d['horas_liquidas']==1
    from app.clock import TZ
    today=datetime.now(TZ)
    assert c.get(f'/api/v1/performance/relatorio/mensal?mes={today.month}&ano={today.year}').status_code==422
    with Session(e) as db:assert db.query(models.BlocoQuestoes).one().total_acertos==21

def review_rows(c):
    response=c.get('/api/v1/estudos/revisoes')
    assert response.status_code==200,response.text
    return response.json()

def test_review_queue_empty_without_history(env):
    c,e=env;catalog(c)
    assert review_rows(c)==[]

def test_review_queue_uses_legacy_history_without_creating_actions(env):
    c,e=env;(m,a),_=catalog(c)
    p=complete_data(m,a);p['data']=iso_utc(utcnow()-timedelta(days=80))
    assert c.post('/api/v1/estudos/concluir',json=p).status_code==201
    with Session(e) as db:
        # Emulate old independent records, with no cycle or linked session.
        b=db.query(models.BlocoQuestoes).one();b.sessao_id=None;db.commit()
    rows=review_rows(c);assert len(rows)==1
    assert rows[0]['disponivel'] and rows[0]['origem']=='AUTOMATICA' and '60 dias' in rows[0]['motivo']
    review_rows(c)
    with Session(e) as db:assert db.query(AcaoEstudo).count()==0

def test_low_precision_and_small_sample_have_different_tasks(env):
    c,e=env;(m,a),(n,b)=catalog(c)
    for days in (4,2):
        p=complete_data(m,a);p['data']=iso_utc(utcnow()-timedelta(days=days));p['bloco']={'total_questoes':10,'total_acertos':4}
        assert c.post('/api/v1/estudos/concluir',json=p).status_code==201
    p=complete_data(n,b);p['data']=iso_utc(utcnow()-timedelta(days=2));p['bloco']={'total_questoes':5,'total_acertos':1}
    c.post('/api/v1/estudos/concluir',json=p)
    rows=review_rows(c)
    assert rows[0]['assunto_id']==a and rows[0]['atividade']=='REVISAO' and '8 acertos em 20' in rows[0]['motivo']
    assert rows[1]['atividade']=='QUESTOES' and 'Amostra pequena' in rows[1]['motivo']

def test_review_completion_delays_next_return_and_preserves_cycle(env):
    c,e=env;(m,a),_=catalog(c)
    p=complete_data(m,a);p['data']=iso_utc(utcnow()-timedelta(days=80));c.post('/api/v1/estudos/concluir',json=p)
    assert review_rows(c)[0]['disponivel']
    p=complete_data(m,a);p['atividade']='REVISAO';c.post('/api/v1/estudos/concluir',json=p)
    row=review_rows(c)[0];assert not row['disponivel']
    assert datetime.fromisoformat(row['prevista_em'])>datetime.now(timezone.utc)+timedelta(hours=47)

def test_programmed_actions_do_not_duplicate_automatic_returns(env):
    c,e=env;(m,a),_=catalog(c)
    p=complete_data(m,a);p['data']=iso_utc(utcnow()-timedelta(days=80));c.post('/api/v1/estudos/concluir',json=p)
    r=c.post('/api/v1/estudos/acoes',json={'assunto_id':a,'descricao':'Refazer o exemplo','prevista_em':iso_utc(utcnow()+timedelta(days=3))})
    assert r.status_code==201
    rows=review_rows(c);assert len(rows)==1 and rows[0]['origem']=='PROGRAMADA' and not rows[0]['disponivel']

def test_classified_errors_return_then_leave_queue_after_analysis(env):
    c,e=env;(m,a),_=catalog(c)
    p=complete_data(m,a);p['data']=iso_utc(utcnow()-timedelta(days=10));c.post('/api/v1/estudos/concluir',json=p)
    with Session(e) as db:
        b=db.query(models.BlocoQuestoes).one();db.add(models.ErroQuestao(bloco_id=b.id,tipo_erro='CALCULO',quantidade=1));db.commit()
    assert review_rows(c)[0]['atividade']=='ANALISE_ERROS'
    p=complete_data(m,a);p['atividade']='ANALISE_ERROS';p['bloco']=None;c.post('/api/v1/estudos/concluir',json=p)
    row=review_rows(c)[0];assert row['atividade']!='ANALISE_ERROS' and not row['disponivel']

def test_now_uses_automatic_queue_with_cycle_subject_selection(env):
    c,e=env;(m,a),(n,b)=catalog(c)
    p=complete_data(m,a);p['data']=iso_utc(utcnow()-timedelta(days=80));c.post('/api/v1/estudos/concluir',json=p)
    goals={'nome':'Meu ciclo','metas':[{'materia_id':m,'minutos':60},{'materia_id':n,'minutos':60}]}
    assert c.post('/api/v1/estudos/ciclo',json=goals).status_code==201
    now=c.get('/api/v1/estudos/agora').json()['recomendacao'];row=review_rows(c)[0]
    assert now['assunto_id']==a and now['tarefa']==row['tarefa'] and now['atividade']=='REVISAO'
    p=complete_data(m,a);p['data']=iso_utc(utcnow());p['atividade']='REVISAO';c.post('/api/v1/estudos/concluir',json=p)
    assert c.get('/api/v1/estudos/agora').json()['recomendacao']['materia_id']==n
