from copy import deepcopy
from datetime import datetime,timedelta
from uuid import UUID
import pytest
from sqlalchemy.orm import Session
from test_flows import env,catalog,complete_data
from app import goals,models,metrics,planner
from app.planning_models import ConfigMetas,SemanaMetas

MONDAY=datetime(2026,9,21,12)  # 09:00 America/Sao_Paulo, before the first window.

@pytest.fixture
def clock(env,monkeypatch):
    c,engine=env
    now=[MONDAY]
    monkeypatch.setattr(goals,'utcnow',lambda:now[0])
    monkeypatch.setattr(metrics,'utcnow',lambda:now[0])
    monkeypatch.setattr(planner,'utcnow',lambda:now[0])
    with Session(engine) as db:
        db.add(ConfigMetas(id=1,dados=deepcopy(goals.DEFAULT),criada_em=MONDAY-timedelta(days=7)));db.commit()
    return c,engine,now

def test_initial_capacity_and_no_artificial_early_debt(clock):
    c,e,now=clock
    w=c.get('/api/v1/metas/semana').json()
    assert (w['meta_minutos'],w['meta_questoes'],w['meta_redacoes'])==(840,55,1)
    assert sum(d['janela_minutos'] for d in w['dias'])==1265
    assert sum(d['capacidade_minutos'] for d in w['dias'])==995
    assert w['esperado_minutos']==0 and w['status']['horas']=='EM ANDAMENTO'
    assert w['status_missao']=='SEMANA EM ANDAMENTO'
    assert w['dias'][6]['meta_minutos']==0
    now[0]=MONDAY.replace(hour=22)  # Monday 19:00 local: only Monday target expected.
    w=c.get('/api/v1/metas/semana').json()
    assert w['esperado_minutos']==180 and w['status']['horas']=='REAJUSTAR RITMO'
    assert w['status_missao']=='AJUSTAR PLANO'

def test_snapshot_profile_next_week_and_no_accumulated_debt(clock):
    c,e,now=clock
    before=c.get('/api/v1/metas/semana').json()
    config=deepcopy(goals.DEFAULT);config['dias'][0]['minutos']=120
    assert c.put('/api/v1/metas/configuracao',json=config).status_code==200
    assert c.get('/api/v1/metas/semana').json()['meta_minutos']==840
    now[0]+=timedelta(days=7)
    after=c.get('/api/v1/metas/semana').json()
    assert after['meta_minutos']==780 and after['realizado']['minutos']==0
    with Session(e) as db:assert db.query(SemanaMetas).count()==2

@pytest.mark.parametrize('change',[lambda p:p['dias'][0].update(minutos=240),lambda p:p['dias'][6].update(minutos=30),lambda p:p['dias'][1].update(dia=0),lambda p:p['dias'][0].update(inicio='25:00'),lambda p:p.update(percentual_pratica=99)])
def test_invalid_schedule_rejected(clock,change):
    c,_,_=clock;p=deepcopy(goals.DEFAULT);change(p)
    assert c.put('/api/v1/metas/configuracao',json=p).status_code==422
    assert c.get('/api/v1/metas/configuracao').json()==goals.DEFAULT

def test_pause_reduce_restore_preserve_actual_and_cycle(clock):
    c,e,now=clock;(m,a),_=catalog(c)
    c.post('/api/v1/estudos/ciclo',json={'nome':'Teste','metas':[{'materia_id':m,'minutos':120}]})
    with Session(e) as db:
        db.add(models.SessaoEstudo(materia_id=UUID(m),assunto_id=UUID(a),data=MONDAY-timedelta(hours=1),tipo_sessao='TEORIA',minutos_liquidos=30));db.commit()
    before=c.get('/api/v1/estudos/agora').json()['ciclo']['id']
    for pct in (50,0,100):
        r=c.patch('/api/v1/metas/semana/ajuste',json={'percentual':pct});assert r.status_code==200
        w=r.json();assert w['realizado']['minutos']==30
        assert w['percentual']==pct
        if pct==0:assert w['status_missao']=='SEMANA EM PAUSA' and w['meta_redacoes']==0
    assert c.get('/api/v1/estudos/agora').json()['ciclo']['id']==before
    assert c.patch('/api/v1/metas/semana/ajuste',json={'percentual':200}).status_code==422

def test_cycle_can_fill_empty_snapshot_and_distribution_is_stable(clock):
    c,e,now=clock;(m,a),(n,b)=catalog(c)
    assert c.get('/api/v1/metas/semana').json()['materias']==[]
    response=c.post('/api/v1/estudos/ciclo',json={'nome':'Teste','metas':[{'materia_id':m,'minutos':120},{'materia_id':n,'minutos':60}]})
    assert response.status_code==201,response.text
    w=c.get('/api/v1/metas/semana').json()
    assert {x['materia_id']:x['meta_minutos'] for x in w['materias']}=={m:560,n:280}
    assert sum(x['meta_minutos'] for x in w['materias'])==w['meta_minutos']

def test_count_linked_block_once_and_ignore_future(clock):
    c,e,now=clock;(m,a),_=catalog(c)
    # Use ORM test fixtures so fixed future clock does not conflict with API's actual current date.
    with Session(e) as db:
        s=models.SessaoEstudo(materia_id=UUID(m),assunto_id=UUID(a),data=MONDAY-timedelta(hours=1),tipo_sessao='QUESTOES',minutos_liquidos=60,segundos_exatos=3599)
        db.add(s);db.flush()
        for linked,total,hits,seconds,dt in [(s.id,20,16,3599,s.data),(None,10,5,600,s.data),(None,40,40,600,MONDAY+timedelta(hours=1))]:
            db.add(models.BlocoQuestoes(materia_id=UUID(m),assunto_id=UUID(a),sessao_id=linked,total_questoes=total,total_acertos=hits,tempo_total_segundos=seconds,dificuldade=3,data=dt))
        db.commit()
    w=c.get('/api/v1/metas/semana').json()
    assert w['realizado']['minutos']==69.98 and w['realizado']['questoes']==30
    assert w['realizado']['acertos']==21
    d=c.get('/api/v1/performance/dashboard?periodo=semana').json()
    assert d['meta_horas']==14 and d['meta_questoes']==55 and d['variante_missao']=='default'
    assert round(d['horas_liquidas']*60)==round(w['realizado']['minutos'])

def test_calibrate_only_eligible_prior_blocks_and_freeze(clock):
    c,e,now=clock;(m,a),_=catalog(c)
    with Session(e) as db:
        for i in range(3):
            db.add(models.BlocoQuestoes(materia_id=UUID(m),assunto_id=UUID(a),total_questoes=10,total_acertos=8,tempo_total_segundos=1200,dificuldade=3,data=MONDAY-timedelta(days=i+1)))
        db.commit()
    w=c.get('/api/v1/metas/semana').json()
    assert w['calibracao']['minutos_por_questao']==3 and w['meta_questoes']==110
    with Session(e) as db:
        for b in db.query(models.BlocoQuestoes):b.tempo_total_segundos=6000
        db.commit()
    assert c.get('/api/v1/metas/semana').json()['meta_questoes']==110
    now[0]+=timedelta(days=7)
    assert c.get('/api/v1/metas/semana').json()['meta_questoes']==20

def test_first_partial_week_and_sunday_context(clock):
    c,e,now=clock;now[0]=MONDAY+timedelta(days=5)
    with Session(e) as db:
        conf=db.get(ConfigMetas,1);conf.criada_em=now[0];db.commit()
    w=c.get('/api/v1/metas/semana').json()
    assert w['parcial'] and w['meta_minutos']==270 and w['meta_questoes']==15
    now[0]+=timedelta(days=1)
    with Session(e) as db:
        context=goals.session_context(db,'REVISAO');assert context['duracao_sugerida_minutos']==0
    advice=c.get('/api/v1/metas/orientacoes').json()
    assert advice and all(a['passos'] for a in advice)
    assert not any('Domingo' in a['titulo'] or 'plano sem criar' in a['titulo'] for a in advice)

def test_essay_only_goal_and_scientific_contract(clock):
    c,e,now=clock
    with Session(e) as db:
        conf=db.get(ConfigMetas,1);p=deepcopy(goals.DEFAULT)
        for d in p['dias']:d['minutos']=0
        conf.dados=p;db.commit()
        db.add(models.Redacao(tema='Teste',eixo_tematico='Teste',data_escrita=MONDAY-timedelta(hours=1)));db.commit()
    w=c.get('/api/v1/metas/semana').json()
    assert w['meta_redacoes']==1 and w['realizado']['redacoes']==1
    assert w['status_missao']=='METAS DA SEMANA CONCLUÍDAS'
    methods=c.get('/api/v1/metas/metodos').json()
    assert set(methods)=={'TEORIA','QUESTOES','REVISAO','ANALISE_ERROS'}
    assert all(len(g['passos'])==4 and g['fonte']['url'].startswith('https://') and g['fonte']['limite'] for g in methods.values())

def test_small_sample_is_exposed_without_fake_trend(clock):
    c,e,now=clock;(m,a),_=catalog(c)
    rows=c.get('/api/v1/estudos/materias-performance').json()
    assert all(x['amostra_blocos']==0 and x['total_questoes']==0 for x in rows)
    d=c.get('/api/v1/performance/dashboard?periodo=semana').json()
    assert d['tendencia']=='SEM PRÁTICA'
    assert '20 questões e 2 registros' in d['tendencia_contexto']

def test_manual_questions_persist_next_week_and_reset(clock):
    c,e,now=clock
    before=c.get('/api/v1/metas/semana').json()
    r=c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':175,'proximas_semanas':True})
    assert r.status_code==200
    w=r.json();assert w['meta_questoes']==175 and w['origem_questoes']=='manual'
    assert w['meta_minutos']==before['meta_minutos'] and w['realizado']==before['realizado']
    assert c.get('/api/v1/performance/dashboard').json()['meta_questoes']==175
    now[0]+=timedelta(days=7)
    assert c.get('/api/v1/metas/semana').json()['meta_questoes']==175
    w=c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':None}).json()
    assert w['meta_questoes']==55 and w['origem_questoes']=='automatica'
    assert c.get('/api/v1/metas/configuracao').json()['meta_questoes'] is None

def test_manual_current_only_respects_pause_and_reduction(clock):
    c,e,now=clock
    c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':175,'proximas_semanas':False})
    assert c.patch('/api/v1/metas/semana/ajuste',json={'percentual':50}).json()['meta_questoes']==87
    assert c.patch('/api/v1/metas/semana/ajuste',json={'percentual':0}).json()['meta_questoes']==0
    assert c.patch('/api/v1/metas/semana/ajuste',json={'percentual':100}).json()['meta_questoes']==175
    assert c.get('/api/v1/metas/configuracao').json().get('meta_questoes') is None
    now[0]+=timedelta(days=7)
    assert c.get('/api/v1/metas/semana').json()['meta_questoes']==55

def test_question_goal_validation_and_existing_week_compatibility(clock):
    c,e,now=clock
    w=c.get('/api/v1/metas/semana').json()
    with Session(e) as db:
        week=db.get(SemanaMetas,goals.monday(now[0]));p=deepcopy(week.plano)
        p.pop('questoes_automaticas');p.pop('origem_questoes');week.plano=p;db.commit()
    for invalid in (-1,0,5001,2.5):
        assert c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':invalid}).status_code==422
    assert c.get('/api/v1/metas/semana').json()['meta_questoes']==55
    c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':175})
    c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':200})
    assert c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':None}).json()['meta_questoes']==55

def test_future_profile_editor_preserves_manual_goal(clock):
    c,e,now=clock
    c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':175})
    p=c.get('/api/v1/metas/configuracao').json();p['dias'][0]['minutos']=200
    assert c.put('/api/v1/metas/configuracao',json=p).status_code==200
    now[0]+=timedelta(days=7)
    w=c.get('/api/v1/metas/semana').json()
    assert w['meta_questoes']==175 and w['meta_minutos']==860


def test_mission_recoverable_and_actionable(clock):
    c,e,now=clock
    c.get('/api/v1/metas/semana')
    now[0]=MONDAY.replace(hour=18)  # Monday 15:00 local, recoverable delay.
    w=c.get('/api/v1/metas/semana').json()
    assert w['status_missao']=='RETOMAR O RITMO'
    assert 'Estudar agora' in w['diagnostico_missao']
    d=c.get('/api/v1/performance/dashboard').json()
    assert d['variante_missao']=='warning'
    assert d['recomendacao'] and w['diagnostico_missao'] not in d['recomendacao']
    now[0]=MONDAY.replace(hour=22)
    w=c.get('/api/v1/metas/semana').json()
    assert w['status_missao']=='AJUSTAR PLANO'
    assert 'janelas cadastradas' in w['diagnostico_missao']


def test_trend_explains_missing_history_and_compares_equal_windows(clock):
    c,e,now=clock;(m,a),_=catalog(c)
    def add(dt,hits):
        with Session(e) as db:
            db.add(models.BlocoQuestoes(materia_id=UUID(m),assunto_id=UUID(a),total_questoes=10,total_acertos=hits,tempo_total_segundos=600,dificuldade=3,data=dt));db.commit()
    add(MONDAY-timedelta(hours=2),9)
    d=c.get('/api/v1/performance/dashboard').json()
    assert d['tendencia']=='AMOSTRA INSUFICIENTE'
    add(MONDAY-timedelta(hours=1),9)
    assert c.get('/api/v1/performance/dashboard').json()['tendencia']=='HISTÓRICO INSUFICIENTE'
    for hours in (1,2):add(MONDAY-timedelta(days=7,hours=hours),6)
    # Later in the previous week must not contaminate equal elapsed comparison.
    add(MONDAY-timedelta(days=6),0)
    d=c.get('/api/v1/performance/dashboard').json()
    assert d['tendencia']=='ASCENDENTE'
    assert '+30.0 pontos' in d['tendencia_contexto']
    assert c.get('/api/v1/performance/dashboard?periodo=total').json()['tendencia']=='SEM COMPARAÇÃO'


@pytest.mark.parametrize('period,factor', [('mes',4),('ano',48)])
def test_dashboard_period_targets_follow_current_week(clock,period,factor):
    c,e,now=clock
    c.patch('/api/v1/metas/semana/questoes',json={'meta_questoes':200})
    for adjustment in (100,50,0):
        w=c.patch('/api/v1/metas/semana/ajuste',json={'percentual':adjustment}).json()
        d=c.get(f'/api/v1/performance/dashboard?periodo={period}').json()
        assert d['meta_horas']==round(w['meta_minutos']/60*factor,2)
        assert d['meta_questoes']==w['meta_questoes']*factor
        assert d['status_horas']==('SEM META' if adjustment==0 else 'EM ANDAMENTO')
    assert c.get('/api/v1/performance/dashboard?periodo=total').json()['meta_horas'] is None


def test_period_subject_targets_are_not_global(clock):
    c,e,now=clock;(m,a),(n,b)=catalog(c)
    c.post('/api/v1/estudos/ciclo',json={'nome':'Teste','metas':[{'materia_id':m,'minutos':120},{'materia_id':n,'minutos':60}]})
    w=c.get('/api/v1/metas/semana').json()
    quota=next(x for x in w['materias'] if x['materia_id']==m)
    d=c.get(f'/api/v1/performance/dashboard?periodo=mes&materia_id={m}').json()
    assert d['meta_horas']==round(quota['meta_minutos']*4/60,2)
    assert d['meta_questoes'] is None
