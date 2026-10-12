"""A06: one projection policy, persistent reference, no speculative history."""
from copy import deepcopy
from datetime import timedelta, datetime
import pytest
from sqlalchemy.orm import Session
from test_flows import env, catalog
from test_goals import clock, MONDAY
from app import goals, models, services
from app.clock import local_date
from app.planning_models import ConfigMetas, SemanaMetas


def reference_25h_200(engine):
    p=deepcopy(goals.DEFAULT)
    for d in p['dias']:
        d.update(inicio='06:00',fim='12:00',pausas=0,minutos=300 if d['dia']<5 else 0)
    p['meta_questoes']=200
    with Session(engine) as db:
        conf=db.get(ConfigMetas,1);conf.dados=p;db.commit()


@pytest.mark.parametrize('period,hours,questions',[('mes',100,800),('ano',1200,9600)])
def test_25h_200_projection_and_exceptions(clock,period,hours,questions):
    c,e,now=clock;reference_25h_200(e)
    w=c.get('/api/v1/metas/semana').json();assert w['meta_minutos']==1500 and w['meta_questoes']==200
    for pct in (100,50,0):
        c.patch('/api/v1/metas/semana/ajuste',json={'percentual':pct})
        c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':100,'proximas_semanas':False})
        d=c.get('/api/v1/performance/dashboard',params={'periodo':period}).json()
        assert d['meta_horas']==hours and d['meta_questoes']==questions
        assert d['status_missao']=='SEM PRÁTICA REGISTRADA'
        assert d['percentual_medio']==0 and d['tem_evidencia'] is False
        assert d['natureza_meta']=='PROJECAO_DE_PLANEJAMENTO'


def test_partial_week_does_not_shrink_reference(clock):
    c,e,now=clock;reference_25h_200(e);now[0]+=timedelta(days=2)
    with Session(e) as db:
        conf=db.get(ConfigMetas,1);conf.criada_em=now[0];db.commit()
    w=c.get('/api/v1/metas/semana').json()
    assert w['parcial'] and w['meta_minutos']==900 and w['meta_questoes']==120
    assert w['projecoes']['mes']['minutos']==6000 and w['projecoes']['ano']['questoes']==9600


def test_dashboard_report_agree_and_unknown_history_stays_null(clock,monkeypatch):
    c,e,now=clock;reference_25h_200(e)
    monkeypatch.setattr(services,'utcnow',lambda:now[0])
    d=c.get('/api/v1/performance/dashboard?periodo=mes').json()
    r=c.get('/api/v1/performance/relatorio/mensal?mes=9&ano=2026');assert r.status_code==200,r.text
    p=r.json()['projecao_fechamento']
    assert (p['meta_horas_mes'],p['meta_questoes_mes'])==(d['meta_horas'],d['meta_questoes'])==(100,800)
    assert p['horas_necessarias_por_dia'] is None and p['questoes_necessarias_por_dia'] is None
    old=c.get('/api/v1/performance/relatorio/mensal?mes=8&ano=2026').json()['projecao_fechamento']
    assert old['meta_horas_mes'] is None and old['meta_questoes_mes'] is None
    assert old['on_track_meta_horas'] is None and old['natureza_meta']=='INFORMACAO_INDISPONIVEL'


def test_explicit_future_changes_activate_next_monday_and_keep_past(clock,monkeypatch):
    c,e,now=clock;reference_25h_200(e);monkeypatch.setattr(services,'utcnow',lambda:now[0])
    c.get('/api/v1/metas/semana')
    assert c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':300,'proximas_semanas':True}).status_code==200
    assert c.get('/api/v1/performance/dashboard?periodo=mes').json()['meta_questoes']==800
    now[0]+=timedelta(days=7)
    assert c.get('/api/v1/performance/dashboard?periodo=mes').json()['meta_questoes']==1200
    assert c.get('/api/v1/performance/dashboard?periodo=ano').json()['meta_questoes']==14400
    now[0]=datetime(2026,10,5,12)
    p=c.get('/api/v1/metas/configuracao').json();p['meta_questoes']=400
    assert c.put('/api/v1/metas/configuracao',json=p).status_code==200
    now[0]+=timedelta(days=7)
    d=c.get('/api/v1/performance/dashboard?periodo=mes').json();assert d['meta_questoes']==1600
    old=c.get('/api/v1/performance/relatorio/mensal?mes=9&ano=2026').json()['projecao_fechamento']
    assert old['meta_questoes_mes']==1200 and old['on_track_meta_questoes'] is None
    assert old['referencia_semanal']['registrada_em'].startswith('2026-09')


def test_reference_survives_new_db_session_and_week_recalibration(clock):
    c,e,now=clock;reference_25h_200(e)
    first=c.get('/api/v1/metas/semana').json()['projecoes']
    (m,a),_=catalog(c)
    with Session(e) as db:
        conf=db.get(ConfigMetas,1);assert conf.dados['_referencias_projecao']
        from uuid import UUID
        for i in range(3):
            db.add(models.BlocoQuestoes(materia_id=UUID(m),assunto_id=UUID(a),total_questoes=10,total_acertos=8,dificuldade=3,tempo_total_segundos=600,data=MONDAY-timedelta(days=i+1)))
        db.commit()
    now[0]+=timedelta(days=7)
    with Session(e) as db:
        current=goals.period_projection(db,'mes',now=now[0])
        assert current==first['mes']
    assert c.get('/api/v1/metas/semana').json()['projecoes']==first


def test_subject_filter_preserves_week_quota_without_period_invention(clock):
    c,e,now=clock;reference_25h_200(e);(m,a),(n,b)=catalog(c)
    c.post('/api/v1/estudos/ciclo',json={'metas':[{'materia_id':m,'minutos':100},{'materia_id':n,'minutos':100}]})
    d=c.get('/api/v1/performance/dashboard',params={'periodo':'semana','materia_id':m}).json()
    assert d['meta_horas']==12.5 and d['meta_questoes'] is None
    for period in ('mes','ano','total'):
        d=c.get('/api/v1/performance/dashboard',params={'periodo':period,'materia_id':m}).json()
        assert d['meta_horas'] is None and d['meta_questoes'] is None


def test_historical_snapshots_untouched_when_initializing_reference(clock):
    c,e,now=clock;reference_25h_200(e)
    old={'base_minutos':333,'base_questoes':25,'percentual':50,'parcial':True}
    old_date=(MONDAY-timedelta(days=35)).date()
    with Session(e) as db:
        db.add(SemanaMetas(inicio=old_date,plano=deepcopy(old)));db.commit()
    c.get('/api/v1/metas/semana')
    with Session(e) as db:
        assert db.get(SemanaMetas,old_date).plano==old
        assert len(db.get(ConfigMetas,1).dados['_referencias_projecao'])==1
    now[0]+=timedelta(days=2)
    c.get('/api/v1/metas/semana')
    with Session(e) as db:assert len(db.get(ConfigMetas,1).dados['_referencias_projecao'])==1


def test_fractional_hour_reference_has_same_rounding_in_report_and_dashboard(clock,monkeypatch):
    c,e,now=clock;reference_25h_200(e)
    with Session(e) as db:
        conf=db.get(ConfigMetas,1);p=deepcopy(conf.dados);p['dias'][0]['minutos']=301;conf.dados=p;db.commit()
    monkeypatch.setattr(services,'utcnow',lambda:now[0])
    d=c.get('/api/v1/performance/dashboard?periodo=mes').json()
    p=c.get('/api/v1/performance/relatorio/mensal?mes=9&ano=2026').json()['projecao_fechamento']
    assert d['meta_horas']==p['meta_horas_mes']==100.07
