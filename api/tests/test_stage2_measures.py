"""A02/A09 contracts, conservative legacy interpretation and count-once behavior."""
import hashlib
import json
from datetime import timedelta, datetime
from uuid import UUID
import pytest
from sqlalchemy.orm import Session
from test_flows import env, catalog, complete_data
from app import models, schemas, planner, metrics, services, goals
from app.clock import utcnow, local_date
from app.study_analysis import performance_change


def submit(c, m, a, **block):
    payload = complete_data(m, a)
    payload['atividade'] = 'TEORIA'
    payload['bloco'] = dict(total_questoes=10,total_acertos=8,**block)
    result = c.post('/api/v1/estudos/concluir',json=payload)
    assert result.status_code == 201, result.text
    return payload, result.json()['sessao_id']


def one_block(c):
    response=c.get('/api/v1/performance/blocos')
    assert response.status_code==200,response.text
    return response.json()[0]


@pytest.mark.parametrize('block,expected_difficulty,expected_time', [({},None,None),({'dificuldade':3},3,None),({'dificuldade':5,'tempo_total_segundos':600},5,600)])
def test_integrated_optional_values_and_serialization(env,block,expected_difficulty,expected_time):
    c,e=env;(m,a),_=catalog(c)
    p,id=submit(c,m,a,**block)
    b=one_block(c)
    assert b['dificuldade']==expected_difficulty
    assert b['dificuldade_informada']==(expected_difficulty is not None)
    assert b['tempo_total_segundos']==expected_time
    assert b['tempo_medio_por_questao']==(60 if expected_time else None)
    assert b['tempo_questoes_informado']==(expected_time is not None)
    for url in ('/api/v1/performance/dashboard?periodo=total','/api/v1/estudos/series?periodo=total','/api/v1/estudos/materias-performance?periodo=total','/api/v1/metas/orientacoes'):
        assert c.get(url).status_code==200
    d=c.get('/api/v1/performance/dashboard?periodo=total').json()
    assert (d['horas_liquidas'],d['total_questoes'],d['total_acertos'])==(1,10,8)
    assert c.post('/api/v1/estudos/concluir',json=p).json()['repetido'] is True
    with Session(e) as db:
        assert db.query(models.SessaoEstudo).count()==1 and db.query(models.BlocoQuestoes).count()==1
    today=local_date(utcnow())
    report=c.get('/api/v1/performance/relatorio/mensal',params={'mes':today.month,'ano':today.year})
    assert report.status_code==200,report.text
    data=report.json()
    assert data['resumo_geral']['horas_totais']==1
    assert data['blocos']['por_materia'][0]['tempo_medio_por_questao']==b['tempo_medio_por_questao']
    assert data['blocos']['por_materia'][0]['questoes_com_tempo']==(10 if expected_time else 0)


@pytest.mark.parametrize('value',[0,-1,3601])
def test_integrated_rejects_invalid_time_atomically(env,value):
    c,e=env;(m,a),_=catalog(c);p=complete_data(m,a);p['bloco']['tempo_total_segundos']=value
    assert c.post('/api/v1/estudos/concluir',json=p).status_code==422
    with Session(e) as db:assert db.query(models.SessaoEstudo).count()==0 and db.query(models.BlocoQuestoes).count()==0


@pytest.mark.parametrize('value',[0,6,-1])
def test_difficulty_range(env,value):
    c,e=env;(m,a),_=catalog(c);p=complete_data(m,a);p['bloco']['dificuldade']=value
    assert c.post('/api/v1/estudos/concluir',json=p).status_code==422


@pytest.mark.parametrize('seconds',[None,600])
def test_independent_block_keeps_own_time(env,seconds):
    c,e=env;(m,a),_=catalog(c)
    p=dict(materia_id=m,assunto_id=a,total_questoes=10,total_acertos=8,dificuldade=3,tempo_total_segundos=seconds)
    r=c.post('/api/v1/performance/blocos',json=p);assert r.status_code==201,r.text
    b=r.json();assert b['tempo_medio_por_questao']==(60 if seconds else None)
    d=c.get('/api/v1/performance/dashboard?periodo=total').json()
    assert d['horas_liquidas']==(.17 if seconds else 0) and d['total_questoes']==10 and d['total_acertos']==8
    assert b['dificuldade_informada'] is True
    assert d['horas_incompletas'] is (seconds is None)
    assert d['blocos_sem_tempo_liquido']==(1 if seconds is None else 0)
    # No deletion endpoint exists in this version; preserve that contract.
    assert c.delete('/api/v1/performance/blocos/'+b['id']).status_code==404


def test_edits_keep_times_separate_and_reject_inconsistent_session(env):
    c,e=env;(m,a),_=catalog(c);p,id=submit(c,m,a,tempo_total_segundos=600)
    b=one_block(c)
    session=dict(materia_id=m,assunto_id=a,tipo_sessao='TEORIA',minutos_liquidos=30,data=p['data'])
    assert c.put('/api/v1/estudos/sessoes/'+id,json=session).status_code==200
    assert one_block(c)['tempo_total_segundos']==600
    assert c.get('/api/v1/performance/dashboard?periodo=total').json()['horas_liquidas']==.5
    r=c.put('/api/v1/estudos/sessoes/'+id,json={**session,'minutos_liquidos':5});assert r.status_code==422
    for seconds in (300,None,900):
        bp={**b,'tempo_total_segundos':seconds,'dificuldade':None}
        r=c.put('/api/v1/estudos/blocos/'+b['id'],json=bp);assert r.status_code==200,r.text
        assert r.json()['tempo_total_segundos']==seconds and r.json()['dificuldade'] is None
        sessions=c.get('/api/v1/performance/sessoes').json();assert sessions[0]['segundos_exatos']==1800
        d=c.get('/api/v1/performance/dashboard?periodo=total').json()
        assert (d['horas_liquidas'],d['total_questoes'],d['total_acertos'])==(.5,10,8)
    assert c.put('/api/v1/estudos/blocos/'+b['id'],json={**b,'tempo_total_segundos':1801}).status_code==422


def test_edit_session_with_unknown_block_time(env):
    c,e=env;(m,a),_=catalog(c);p,id=submit(c,m,a)
    assert c.put('/api/v1/estudos/sessoes/'+id,json=dict(materia_id=m,assunto_id=a,tipo_sessao='TEORIA',minutos_liquidos=15,data=p['data'])).status_code==200
    assert one_block(c)['tempo_total_segundos'] is None
    assert c.get('/api/v1/performance/dashboard?periodo=total').json()['horas_liquidas']==.25


def test_legacy_integrated_values_not_reclassified_by_reads_or_other_edits(env):
    c,e=env;(m,a),_=catalog(c);p,id=submit(c,m,a)
    with Session(e) as db:
        b=db.query(models.BlocoQuestoes).one();b.dificuldade=3;b.dificuldade_informada=None
        b.tempo_total_segundos=3600;b.tempo_questoes_informado=None;db.commit()
    b=one_block(c);assert b['tempo_medio_por_questao'] is None and b['tempo_total_segundos']==3600
    assert c.put('/api/v1/estudos/blocos/'+b['id'],json={**b,'total_acertos':7}).status_code==200
    assert c.put('/api/v1/estudos/sessoes/'+id,json=dict(materia_id=m,assunto_id=a,tipo_sessao='TEORIA',minutos_liquidos=30,data=p['data'])).status_code==200
    b=one_block(c)
    assert b['dificuldade']==3 and b['dificuldade_informada'] is None
    assert b['tempo_total_segundos']==3600 and b['tempo_questoes_informado'] is None and b['tempo_medio_por_questao'] is None
    assert c.put('/api/v1/estudos/blocos/'+b['id'],json={**b,'confirmar_tempo_questoes':True}).status_code==422
    assert c.put('/api/v1/estudos/blocos/'+b['id'],json={**b,'tempo_total_segundos':600,'confirmar_dificuldade':True}).status_code==200
    b=one_block(c);assert b['dificuldade_informada'] is True and b['tempo_medio_por_questao']==60


@pytest.mark.parametrize('mode',['explicit','unknown_difficulty','legacy_difficulty','different_difficulty','unknown_time','legacy_mixed_time','legacy_independent_time'])
def test_comparisons_require_qualified_difficulty_and_time(env,mode):
    c,e=env;(m,a),_=catalog(c)
    with Session(e) as db:
        rows=[]
        for i in range(4):
            s=None
            if mode=='legacy_mixed_time':
                s=models.SessaoEstudo(materia_id=UUID(m),assunto_id=UUID(a),tipo_sessao='TEORIA',minutos_liquidos=60);db.add(s);db.flush()
            b=models.BlocoQuestoes(materia_id=UUID(m),assunto_id=UUID(a),data=utcnow()-timedelta(days=4-i),total_questoes=10,total_acertos=8,
                dificuldade=None if mode=='unknown_difficulty' and i==3 else 5 if mode=='different_difficulty' and i==3 else 3,
                dificuldade_informada=None if mode=='legacy_difficulty' else True,
                tempo_total_segundos=None if mode=='unknown_time' and i==3 else 600 if i<2 else 1000,
                tempo_questoes_informado=None if mode.startswith('legacy_') else True,sessao_id=s.id if s else None)
            db.add(b);rows.append(b)
        db.flush();change=performance_change(rows)
        assert bool(change)==(mode in ('explicit','legacy_independent_time'))
        if change:assert change[0]=='TEMPO EM ALTA'
        if mode=='unknown_time':
            rows[2].total_acertos=rows[3].total_acertos=4
            assert performance_change(rows)[0]=='QUEDA RECENTE'  # Accuracy can compare qualified difficulties without pace.
        db.commit()


def test_report_handles_mixed_null_difficulties_and_weighted_known_times(env):
    c,e=env;(m,a),_=catalog(c)
    submit(c,m,a,tempo_total_segundos=600)
    p=complete_data(m,a);p['bloco']={'total_questoes':100,'total_acertos':80,'dificuldade':3}
    assert c.post('/api/v1/estudos/concluir',json=p).status_code==201
    today=local_date(utcnow());r=c.get('/api/v1/performance/relatorio/mensal',params={'mes':today.month,'ano':today.year})
    assert r.status_code==200,r.text;d=r.json()
    assert {x['dificuldade'] for x in d['blocos']['por_dificuldade']}=={None,3}
    item=d['blocos']['por_materia'][0]
    assert item['tempo_medio_por_questao']==60 and item['questoes_com_tempo']==10 and item['total_questoes']==110
    assert d['resumo_geral']['horas_totais']==2


def test_old_idempotency_hash_replays_without_rewriting_history(env):
    c,e=env;(m,a),_=catalog(c);p,id=submit(c,m,a,dificuldade=3)
    model=planner.Conclusao.model_validate(p);legacy=model.model_dump(mode='json');legacy['bloco'].pop('tempo_total_segundos')
    for key in ('finalidade','objetivo_revisao','classe_revisao'):legacy.pop(key,None)
    digest=hashlib.sha256(json.dumps(legacy,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    with Session(e) as db:
        s=db.get(models.SessaoEstudo,UUID(id));s.conteudo_hash=digest
        b=db.query(models.BlocoQuestoes).one();b.tempo_total_segundos=3600;b.tempo_questoes_informado=None;db.commit()
    assert c.post('/api/v1/estudos/concluir',json=p).json()['repetido'] is True
    assert one_block(c)['tempo_total_segundos']==3600
    assert c.post('/api/v1/estudos/concluir',json={**p,'segundos':1000}).status_code==409


@pytest.mark.parametrize('confirmed', [None, True])
def test_calibration_accepts_measured_mixed_sessions_but_excludes_legacy_question_labels(env,confirmed):
    from copy import deepcopy
    from test_goals import MONDAY
    c,e=env;(m,a),_=catalog(c)
    with Session(e) as db:
        for i in range(3):
            when=MONDAY-timedelta(days=i+1)
            s=models.SessaoEstudo(materia_id=UUID(m),assunto_id=UUID(a),tipo_sessao='TEORIA' if confirmed else 'QUESTOES',minutos_liquidos=60,data=when)
            db.add(s);db.flush()
            db.add(models.BlocoQuestoes(materia_id=UUID(m),assunto_id=UUID(a),sessao_id=s.id,data=when,total_questoes=10,total_acertos=8,dificuldade=None,tempo_total_segundos=600,tempo_questoes_informado=confirmed))
        db.commit()
        calibration=goals.calibration(db,goals.monday(MONDAY),deepcopy(goals.DEFAULT))
        assert calibration['blocos']==(3 if confirmed else 0)
        assert calibration['questoes']==(30 if confirmed else 0)
        assert calibration['minutos_por_questao']==(2 if confirmed else 6)
