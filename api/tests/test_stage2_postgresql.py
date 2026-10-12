"""Opt-in integration: rejects any populated or unnamed database before writes.
PROVECTUS_STAGE2_TEST_DATABASE_URL must point to an EMPTY provectus_etapa2_test.
No user database, automatic deletion or teardown SQL is used.
"""
import os
from pathlib import Path
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app import migrate, models, goals, planner
from app.clock import utcnow, iso_utc
from app.database import get_db
from app.main import app
from app.planning_models import ConfigMetas

@pytest.fixture(scope='module')
def pg_env(tmp_path_factory):
    url=os.environ.get('PROVECTUS_STAGE2_TEST_DATABASE_URL')
    if not url:pytest.skip('PostgreSQL descartável não configurado.')
    assert make_url(url).database=='provectus_etapa2_test', 'Recusado: banco deve chamar provectus_etapa2_test.'
    engine=create_engine(url)
    with engine.connect() as conn:
        assert not inspect(conn).get_table_names(), 'Recusado: banco deve estar vazio antes de qualquer escrita.'
        assert 'question_bank' not in inspect(conn).get_schema_names(), 'Recusado: esquema BQ preexistente.'
    earlier=tmp_path_factory.mktemp('stage1_migrations')
    directory=migrate.MIGRATIONS
    for file in directory.glob('*.sql'):
        if file.name<'009_':(earlier/file.name).write_bytes(file.read_bytes())
    migrate.MIGRATIONS=earlier
    try:migrate.migrate(engine)
    finally:migrate.MIGRATIONS=directory
    mid,aid,sid,bid=(uuid4() for _ in range(4));date=utcnow()-timedelta(hours=1)
    with engine.begin() as conn:
        conn.execute(text('INSERT INTO tb_materia(id,nome,peso_prova,ativa) VALUES (:id,\'Legado\',1,true)'),{'id':mid})
        conn.execute(text('INSERT INTO tb_assunto(id,materia_id,nome,semana_do_ciclo,ativo) VALUES (:id,:mid,\'Assunto\',1,true)'),{'id':aid,'mid':mid})
        conn.execute(text('INSERT INTO tb_sessao_estudo(id,materia_id,assunto_id,data,tipo_sessao,minutos_liquidos) VALUES (:id,:mid,:aid,:date,\'TEORIA\',60)'),{'id':sid,'mid':mid,'aid':aid,'date':date})
        conn.execute(text('INSERT INTO tb_bloco_questoes(id,materia_id,assunto_id,data,sessao_id,dificuldade,total_questoes,total_acertos,tempo_total_segundos,criado_em) VALUES (:id,:mid,:aid,:date,:sid,3,10,8,3600,:date)'),{'id':bid,'mid':mid,'aid':aid,'date':date,'sid':sid})
        before=conn.execute(text('SELECT * FROM tb_bloco_questoes')).mappings().one()
        before=dict(before)
    migrate.migrate(engine)
    migrate.migrate(engine)  # Checksums + idempotent migration.
    with engine.connect() as conn:
        after=dict(conn.execute(text('SELECT * FROM tb_bloco_questoes')).mappings().one())
        assert all(after[k]==v for k,v in before.items())
        assert after['dificuldade_informada'] is None and after['tempo_questoes_informado'] is None
    def db_override():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_db]=db_override
    yield TestClient(app),engine,str(mid),str(aid),str(bid)
    app.dependency_overrides.clear();engine.dispose()


def test_migration_preserves_legacy_and_nullable_contract(pg_env):
    c,e,m,a,old=pg_env
    with e.connect() as conn:
        version=int(conn.execute(text('SHOW server_version_num')).scalar())
        assert version>=150000
        columns={x['name']:x for x in inspect(conn).get_columns('tb_bloco_questoes')}
        assert columns['dificuldade']['nullable'] and columns['tempo_total_segundos']['nullable']
        assert conn.execute(text('SELECT count(*) FROM provectus_migrations')).scalar()==9
    rows=c.get('/api/v1/performance/blocos').json()
    legacy=next(b for b in rows if b['id']==old)
    assert legacy['dificuldade']==3 and legacy['tempo_total_segundos']==3600 and legacy['tempo_medio_por_questao'] is None


@pytest.mark.parametrize('seconds',[None,600])
def test_integrated_writes_and_replay_on_postgresql(pg_env,seconds):
    c,e,m,a,old=pg_env
    p=dict(chave_registro=str(uuid4()),materia_id=m,assunto_id=a,data=iso_utc(utcnow()-timedelta(seconds=1)),segundos=3600,atividade='TEORIA',bloco={'total_questoes':10,'total_acertos':8,'tempo_total_segundos':seconds})
    r=c.post('/api/v1/estudos/concluir',json=p);assert r.status_code==201,r.text
    assert c.post('/api/v1/estudos/concluir',json=p).json()['repetido'] is True
    with Session(e) as db:
        from uuid import UUID
        s=db.get(models.SessaoEstudo,UUID(r.json()['sessao_id']))
        b=db.query(models.BlocoQuestoes).filter_by(sessao_id=s.id).one()
        assert s.segundos_exatos==3600 and b.tempo_total_segundos==seconds and b.dificuldade is None
        assert b.tempo_medio_por_questao==(60 if seconds else None)


def test_database_rejects_negative_measures_without_touching_legacy(pg_env):
    c,e,m,a,old=pg_env
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        with e.begin() as conn:
            conn.execute(text('INSERT INTO tb_bloco_questoes(id,materia_id,assunto_id,data,total_questoes,total_acertos,tempo_total_segundos,dificuldade) VALUES (:id,:mid,:aid,:date,10,8,-1,NULL)'),{'id':uuid4(),'mid':m,'aid':a,'date':utcnow()})
    with e.connect() as conn:
        assert conn.execute(text('SELECT tempo_total_segundos FROM tb_bloco_questoes WHERE id=:id'),{'id':old}).scalar()==3600


def test_reference_persists_across_connections(pg_env):
    c,e,m,a,old=pg_env
    w=c.get('/api/v1/metas/semana');assert w.status_code==200,w.text
    target=w.json()['projecoes']['mes']
    c.patch('/api/v1/metas/semana/ajuste',json={'percentual':0})
    with Session(e) as db:
        assert db.get(ConfigMetas,1).dados['_referencias_projecao']
        assert goals.period_projection(db,'mes')==target
    d=c.get('/api/v1/performance/dashboard?periodo=mes').json()
    assert d['meta_horas']==target['minutos']/60 and d['meta_questoes']==target['questoes']


def test_editing_linked_measures_does_not_replace_session_duration(pg_env):
    c,e,m,a,old=pg_env
    p=dict(chave_registro=str(uuid4()),materia_id=m,assunto_id=a,data=iso_utc(utcnow()-timedelta(seconds=1)),segundos=3600,atividade='TEORIA',bloco={'total_questoes':10,'total_acertos':8,'dificuldade':3,'tempo_total_segundos':600})
    r=c.post('/api/v1/estudos/concluir',json=p);assert r.status_code==201,r.text
    sid=r.json()['sessao_id']
    b=next(b for b in c.get('/api/v1/performance/blocos').json() if b['sessao_id']==sid)
    session=dict(materia_id=m,assunto_id=a,tipo_sessao='TEORIA',minutos_liquidos=45,data=p['data'])
    assert c.put('/api/v1/estudos/sessoes/'+sid,json=session).status_code==200
    assert c.put('/api/v1/estudos/sessoes/'+sid,json={**session,'minutos_liquidos':5}).status_code==422
    changed=c.put('/api/v1/estudos/blocos/'+b['id'],json={**b,'tempo_total_segundos':300})
    assert changed.status_code==200,changed.text
    assert changed.json()['tempo_medio_por_questao']==30
    from uuid import UUID
    with Session(e) as db:
        s=db.get(models.SessaoEstudo,UUID(sid));assert s.segundos_exatos==2700
        assert db.query(models.BlocoQuestoes).filter_by(sessao_id=s.id).count()==1
