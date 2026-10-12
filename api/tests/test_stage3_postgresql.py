"""Opt-in migration 009 -> 010, only a fresh provectus_etapa3_test database."""
import os
from datetime import timedelta
from uuid import uuid4, UUID
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app import migrate, models
from app.main import app
from app.database import get_db
from app.clock import utcnow, iso_utc


@pytest.fixture(scope='module')
def pg3(tmp_path_factory):
    url=os.getenv('PROVECTUS_STAGE3_TEST_DATABASE_URL')
    if not url:pytest.skip('PostgreSQL descartável não configurado.')
    assert make_url(url).database=='provectus_etapa3_test'
    engine=create_engine(url)
    with engine.connect() as conn:
        assert not inspect(conn).get_table_names(), 'Recusado: banco não está vazio.'
        assert 'question_bank' not in inspect(conn).get_schema_names(), 'Recusado: BQ preexistente.'
    directory=migrate.MIGRATIONS;old=tmp_path_factory.mktemp('migrations_001_009')
    for file in directory.glob('*.sql'):
        if file.name<'010_':(old/file.name).write_bytes(file.read_bytes())
    migrate.MIGRATIONS=old
    try:migrate.migrate(engine)
    finally:migrate.MIGRATIONS=directory
    mid,aid,sid,bid=(uuid4() for _ in range(4));when=utcnow()-timedelta(days=2)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO tb_materia(id,nome,peso_prova,ativa) VALUES (:m,'Teste etapa 3',1,true)"),{'m':mid})
        conn.execute(text("INSERT INTO tb_assunto(id,materia_id,nome,semana_do_ciclo,ativo) VALUES (:a,:m,'Assunto real',1,true)"),{'a':aid,'m':mid})
        conn.execute(text("INSERT INTO tb_sessao_estudo(id,materia_id,assunto_id,data,tipo_sessao,minutos_liquidos) VALUES (:s,:m,:a,:d,'REVISAO',40)"),{'s':sid,'m':mid,'a':aid,'d':when})
        conn.execute(text("INSERT INTO tb_bloco_questoes(id,materia_id,assunto_id,data,total_questoes,total_acertos,dificuldade,tempo_total_segundos) VALUES (:b,:m,:a,:d,10,4,NULL,NULL)"),{'b':bid,'m':mid,'a':aid,'d':when})
        before={table:[dict(x) for x in conn.execute(text('SELECT * FROM '+table)).mappings()] for table in ('tb_assunto','tb_sessao_estudo','tb_bloco_questoes')}
    migrate.migrate(engine);migrate.migrate(engine)
    with engine.connect() as conn:
        for table,records in before.items():
            after={str(x['id']):x for x in conn.execute(text('SELECT * FROM '+table)).mappings()}
            for row in records:assert all(after[str(row['id'])][k]==v for k,v in row.items())
    def override():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_db]=override
    yield TestClient(app),engine,mid,aid,sid
    app.dependency_overrides.clear();engine.dispose()


def test_migration_010_preserves_old_fields_and_unknowns(pg3):
    c,e,m,a,s=pg3
    with Session(e) as db:
        assert db.get(models.SessaoEstudo,s).finalidade is None
        assert db.get(models.Assunto,a).familiaridade_declarada is None
        assert db.query(models.BlocoQuestoes).one().dificuldade is None
    with e.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM provectus_migrations')).scalar()==10
        assert conn.execute(text('SHOW server_version_num')).scalar() >= '150000'


def test_postgresql_declaration_and_recommendation_are_not_study_events(pg3):
    c,e,m,a,s=pg3
    with Session(e) as db:before=db.query(models.SessaoEstudo).count()
    assert c.patch(f'/api/v1/estudos/assuntos/{a}/familiaridade',json={'declaracao':'ESTUDADO'}).status_code==200
    for _ in range(3):assert c.get('/api/v1/estudos/agora?minutos=15').status_code==200
    with Session(e) as db:assert db.query(models.SessaoEstudo).count()==before


def test_postgresql_completion_metadata_and_replay(pg3):
    c,e,m,a,s=pg3
    payload=dict(chave_registro=str(uuid4()),materia_id=str(m),assunto_id=str(a),data=iso_utc(utcnow()-timedelta(seconds=1)),
                 atividade='QUESTOES',finalidade='REVISAO',objetivo_revisao='contato:'+str(s),classe_revisao='MANUTENCAO',segundos=900,
                 bloco={'total_questoes':10,'total_acertos':8})
    response=c.post('/api/v1/estudos/concluir',json=payload);assert response.status_code==201,response.text
    assert c.post('/api/v1/estudos/concluir',json=payload).json()['repetido']
    with Session(e) as db:
        session=db.get(models.SessaoEstudo,UUID(response.json()['sessao_id']));assert session.finalidade=='REVISAO'
        assert db.query(models.BlocoQuestoes).filter_by(sessao_id=session.id).count()==1


def test_postgresql_constraints(pg3):
    c,e,m,a,s=pg3
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        with e.begin() as conn:conn.execute(text("UPDATE tb_sessao_estudo SET finalidade='DOMINADO' WHERE id=:s"),{'s':s})
    with Session(e) as db:assert db.get(models.SessaoEstudo,s).finalidade is None
