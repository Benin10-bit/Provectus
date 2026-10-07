"""Check boundaries without pretending SQLite implements PostgreSQL JSONB."""
from pathlib import Path
import pytest
from fastapi import HTTPException
from test_flows import env
from app.question_bank import Filters, Answer, filters_sql, asset_path, media, question, check_individual, router


def test_rich_segments_and_audit_crops_are_separated():
    from types import SimpleNamespace

    inline = {'kind': 'visual', 'display': 'inline', 'asset_hash': 'a' * 64}
    class Rows:
        def __init__(self, values): self.values = values
        def all(self): return self.values
        def first(self): return self.values[0] if self.values else None

    class FakeDb:
        def execute(self, statement, _params):
            sql = str(statement)
            if 'SELECT q.id,q.enunciado' in sql:
                assert "q.payload -> 'statement' -> 'segments'" in sql
                return Rows([SimpleNamespace(_mapping={'id': 'q1', 'statement_segments': [inline]})])
            if 'FROM question_bank.alternatives' in sql:
                return Rows([SimpleNamespace(question_id='q1', letter='A', ordinal=0,
                                             text=None, segments=[inline])])
            assert "qa.type <> 'ORIGINAL_CROP'" in sql
            return Rows([SimpleNamespace(question_id='q1', ordinal=0, type='STATEMENT_IMAGE',
                                         alternative_letter=None, hash='a' * 64, mime_type='image/webp')])

    data = question('q1', FakeDb())
    assert data['statement_segments'] == [inline]
    assert data['alternatives'][0]['segments'] == [inline]
    assert data['assets'][0]['hash'] == 'a' * 64
    assert 'answer' not in data


def test_individual_answer_records_only_bank_history_after_validation():
    from types import SimpleNamespace
    class Rows:
        def __init__(self,values):self.values=values
        def first(self):return self.values[0] if self.values else None
        def scalars(self):return self
        def all(self):return self.values
    class FakeDb:
        def __init__(self):self.solved=[];self.commits=0
        def execute(self,stmt,args):
            sql=str(stmt)
            if 'SELECT gabarito' in sql:return Rows([SimpleNamespace(gabarito='B')])
            if 'SELECT letter' in sql:return Rows(['A','B'])
            assert 'INSERT INTO question_bank.solved_questions' in sql
            self.solved.append(args['qid']);return Rows([])
        def commit(self):self.commits+=1
    db=FakeDb()
    assert check_individual('q1',Answer(letter='B'),db)=={'selected':'B','correct':True,'answer':'B'}
    assert check_individual('q1',Answer(letter='A'),db)['correct'] is False
    assert db.solved==['q1','q1'] and db.commits==2
    with pytest.raises(HTTPException) as error:check_individual('q1',Answer(letter='C'),db)
    assert error.value.status_code==422
    assert len(db.solved)==2 and db.commits==2


def test_content_hierarchy_is_a_prefix():
    where,args=filters_sql(Filters(paths=[['Matemática','Básica','Operações'],['Física']]))
    assert 'OR' in where and '->> 2' in where
    assert args['v0_0']=='Básica' and args['v0_1']=='Operações'
    with pytest.raises(HTTPException):filters_sql(Filters(paths=[['']]))


def test_asset_root_blocks_traversal(tmp_path,monkeypatch):
    monkeypatch.setenv('QUESTION_BANK_ASSETS_ROOT',str(tmp_path))
    (tmp_path/'figure.png').write_bytes(b'image')
    assert asset_path('figure.png')==tmp_path/'figure.png'
    with pytest.raises(HTTPException):asset_path('../elsewhere.png')
    with pytest.raises(HTTPException):asset_path('missing.png')


def test_asset_http_route_serves_file(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db

    monkeypatch.setenv('QUESTION_BANK_ASSETS_ROOT',str(tmp_path))
    (tmp_path/'figure.png').write_bytes(b'image')

    class FakeDb:
        def execute(self,*_args,**_kwargs):
            return SimpleNamespace(first=lambda: SimpleNamespace(storage_path='figure.png',mime_type='image/png'))

    app.dependency_overrides[get_db]=lambda:FakeDb()
    try:
        response=TestClient(app).get('/api/v1/question-bank/assets/'+'a'*64)
        assert response.status_code==200
        assert response.headers['content-type']=='image/png'
        assert response.content==b'image'
    finally:
        app.dependency_overrides.pop(get_db,None)


def test_question_bank_routes_and_additive_migration():
    paths={route.path for route in router.routes}
    assert {'/api/v1/question-bank/filters','/api/v1/question-bank/search',
            '/api/v1/question-bank/lists/{list_id}/export.pdf',
            '/api/v1/question-bank/lists/{list_id}/questions/{question_id}/answer'} <= paths
    sql=Path(__file__).resolve().parents[1].joinpath('migrations/005_question_bank_user_data.sql').read_text()
    assert 'CREATE TABLE question_bank.answers' in sql
    assert 'DROP TABLE' not in sql


@pytest.mark.parametrize('placement',['end','after_each'])
def test_pdf_contains_question_and_answer_key(tmp_path,monkeypatch,placement):
    from uuid import uuid4
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from app.question_bank import export_pdf
    engine=create_engine('sqlite://')
    lid=str(uuid4())
    with engine.begin() as conn:
        conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS question_bank")
        conn.exec_driver_sql('CREATE TABLE question_bank.lists(id TEXT,name TEXT)')
        conn.exec_driver_sql('CREATE TABLE question_bank.list_questions(list_id TEXT,question_id TEXT,ordinal INTEGER)')
        conn.exec_driver_sql("CREATE TABLE question_bank.questions(id TEXT,enunciado TEXT,gabarito TEXT,document_sha256 TEXT DEFAULT 'doc',banca_normalizada TEXT,dificuldade_normalizada TEXT,payload TEXT DEFAULT '{}')")
        conn.exec_driver_sql("CREATE TABLE question_bank.alternatives(question_id TEXT,letter TEXT,ordinal INTEGER,text TEXT,payload TEXT DEFAULT '{}')")
        conn.exec_driver_sql('CREATE TABLE question_bank.question_assets(question_id TEXT,ordinal INTEGER,asset_hash TEXT,alternative_letter TEXT,type TEXT)')
        conn.exec_driver_sql('CREATE TABLE question_bank.assets(hash TEXT,storage_path TEXT,mime_type TEXT)')
        conn.exec_driver_sql('CREATE TABLE question_bank.documents(sha256 TEXT,materia TEXT,content_path TEXT)')
        conn.exec_driver_sql("INSERT INTO question_bank.documents VALUES ('doc','Física','[]')")
        conn.execute(text('INSERT INTO question_bank.lists VALUES (:id,:name)'),dict(id=lid,name='Lista de Física'))
        conn.exec_driver_sql("INSERT INTO question_bank.questions(id,enunciado,gabarito) VALUES ('q1','Quanto é 2 + 2?','B')")
        conn.execute(text("INSERT INTO question_bank.list_questions VALUES (:id,'q1',1)"),dict(id=lid))
        conn.exec_driver_sql("INSERT INTO question_bank.alternatives(question_id,letter,ordinal,text) VALUES ('q1','A',1,'3'),('q1','B',2,'4')")
    with Session(engine) as db:
        response=export_pdf(__import__('uuid').UUID(lid),db,placement)
        assert response.media_type=='application/pdf'
        assert response.headers['content-disposition'].endswith('.pdf"')
        import asyncio
        from io import BytesIO
        from pypdf import PdfReader
        async def contents():
            return b''.join([part async for part in response.body_iterator])
        pdf=PdfReader(BytesIO(asyncio.run(contents())))
        content='\n'.join(page.extract_text() for page in pdf.pages)
        assert 'Quanto é 2 + 2?' in content
        assert ('01 — B' in content) if placement=='end' else ('GABARITO' in content)
    engine.dispose()
