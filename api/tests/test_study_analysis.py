from datetime import timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from test_flows import env, catalog
from test_goals import clock, MONDAY
from app import models
from app.planning_models import AcaoEstudo

def block(engine,m,a,when,hits=5,total=10,seconds=600,difficulty=3):
    with Session(engine) as db:
        db.add(models.BlocoQuestoes(materia_id=UUID(m),assunto_id=UUID(a),data=when,total_questoes=total,total_acertos=hits,tempo_total_segundos=seconds,dificuldade=difficulty));db.commit()

def test_critical_topics_keep_granularity_and_periods(clock):
    c,e,now=clock;(m,a),(n,b)=catalog(c)
    good=c.post('/api/v1/performance/assuntos',json={'nome':'Outro assunto','materia_id':m,'semana_do_ciclo':1}).json()['id']
    for hour in (1,2):
        block(e,m,a,MONDAY-timedelta(hours=hour))
        block(e,m,good,MONDAY-timedelta(hours=hour),hits=9)
    for period in ('semana','mes','ano','total'):
        d=c.get('/api/v1/performance/dashboard',params={'periodo':period}).json()
        assert d['assuntos_criticos']==[a]
        detail=d['assuntos_criticos_detalhes'][0]
        assert detail['materia_id']==m and detail['precisao']==50
        assert detail['questoes']==20 and detail['registros']==2
        assert a in detail['destino'] and good not in d['assuntos_criticos']
        assert d['status_academico']=='ASSUNTOS EXIGEM ATENÇÃO'
    assert c.get('/api/v1/performance/dashboard',params={'materia_id':n}).json()['assuntos_criticos']==[]
    now[0]+=timedelta(days=7)
    assert c.get('/api/v1/performance/dashboard').json()['assuntos_criticos']==[]
    assert c.get('/api/v1/performance/dashboard?periodo=mes').json()['assuntos_criticos']==[a]

def test_small_and_empty_samples_never_critical(clock):
    c,e,now=clock;(m,a),_=catalog(c)
    empty=c.get('/api/v1/performance/dashboard').json()
    assert empty['status_academico']=='DADOS INSUFICIENTES'
    assert 'Ainda não há histórico' in empty['orientacoes'][0]['motivo']
    block(e,m,a,MONDAY-timedelta(hours=1),hits=0,total=2)
    d=c.get('/api/v1/performance/dashboard').json()
    assert not d['assuntos_criticos'] and 'insuficiente' in d['criticidade_contexto']
    now[0]+=timedelta(days=2)
    d=c.get('/api/v1/performance/dashboard').json()
    assert d['orientacoes'][0]['categoria']=='Ampliar evidência'
    assert d['orientacoes'][0]['variante']=='default'

def test_due_review_reuses_queue_and_prepared_session(clock):
    c,e,now=clock;(m,a),_=catalog(c)
    with Session(e) as db:
        db.add(AcaoEstudo(assunto_id=UUID(a),descricao='Explicar a regra sem consulta',prevista_em=MONDAY-timedelta(days=1)));db.commit()
    d=c.get('/api/v1/performance/dashboard').json()
    queue=c.get('/api/v1/estudos/revisoes').json()
    assert d['orientacoes'][0]['acao']==queue[0]['tarefa']
    assert queue[0]['acao_id'] in d['orientacoes'][0]['destino']
    assert d['status_academico']=='REVISÃO PRIORITÁRIA'
    assert 'Saldo da semana' not in str(d['recomendacao'])

def test_speed_rule_is_shared_and_requires_comparable_difficulty(clock):
    c,e,now=clock;(m,a),_=catalog(c)
    now[0]=MONDAY+timedelta(days=5)
    for i in range(4):block(e,m,a,MONDAY+timedelta(hours=i),hits=8,seconds=600 if i<2 else 1000)
    d=c.get('/api/v1/performance/dashboard').json()
    assert 'tempo por questão aumentou' in d['orientacoes'][0]['motivo']
    assert 'cronometrado' in d['orientacoes'][0]['acao']
    assert c.get('/api/v1/estudos/revisoes').json()[0]['tarefa']==d['orientacoes'][0]['acao']
    with Session(e) as db:
        b=db.query(models.BlocoQuestoes).order_by(models.BlocoQuestoes.data.desc()).first();b.dificuldade=5;db.commit()
    assert 'tempo por questão aumentou' not in str(c.get('/api/v1/performance/dashboard').json()['orientacoes'])

def test_inconsistent_legacy_association_not_used_for_topic_diagnosis(clock):
    c,e,now=clock;(m,a),(n,b)=catalog(c)
    for hour in (1,2):block(e,n,a,MONDAY-timedelta(hours=hour),hits=0)
    now[0]+=timedelta(days=2)
    d=c.get('/api/v1/performance/dashboard').json()
    assert not d['assuntos_criticos']
    assert all(not r['assunto'] for r in d['orientacoes'])
    with Session(e) as db:assert db.query(models.BlocoQuestoes).count()==2
