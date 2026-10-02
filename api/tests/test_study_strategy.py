from datetime import datetime, timedelta
from types import SimpleNamespace
from test_flows import env, catalog
from app.study_strategy import study_strategy
from test_goals import clock, MONDAY
from test_study_analysis import block


def test_strategy_uses_sample_accuracy_time_and_distribution():
    s=SimpleNamespace(data=datetime(2026,9,21,18), segundos_exatos=3600, minutos_liquidos=60, atividade='TEORIA', tipo_sessao='TEORIA')
    low=study_strategy(2,40,50,2,[s])
    assert '50%' in low[0] and 'carga atual' in low[0]
    assert any('2.0h' in x for x in low)
    assert any('100%' in x for x in low)
    assert any('único dia' in x for x in low)
    assert 'amostra ainda é limitada' in study_strategy(2,4,100,1)[0]
    assert 'resultado favorável' in study_strategy(2,40,90,2)[0]
    assert 'não é possível avaliar' in study_strategy(0,0,0,0)[0]


def test_strategic_and_operational_guidance_have_different_scope(clock):
    c,e,_=clock;(m,a),_=catalog(c)
    for hour in (1,2):block(e,m,a,MONDAY-timedelta(hours=hour),hits=5,total=10)
    d=c.get('/api/v1/performance/dashboard').json()
    assert d['recomendacoes_estudo']==d['recomendacao']
    assert '50%' in d['recomendacoes_estudo'][0]
    r=c.get('/api/v1/metas/orientacoes');assert r.status_code==200
    guidance=r.json();assert 'último bloco' in guidance[0]['motivo']
    assert any('5 questões novas' in x for x in guidance[0]['passos'])
    assert a in guidance[0]['destino']
    assert not set(d['recomendacoes_estudo']) & {x['motivo'] for x in guidance}
    assert all('Reduza a meta' not in str(x) for x in guidance)
