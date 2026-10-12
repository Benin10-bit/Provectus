"""Name validation/movement against isolated HTTP and SQLite question-bank tables."""
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import ValidationError

from test_flows import env
from app.question_bank import FolderIn, FolderEdit, ListIn, ListEdit


@pytest.fixture
def names(env):
    client, engine = env
    folder, other, list_id = (str(uuid4()) for _ in range(3))
    with engine.begin() as db:
        db.exec_driver_sql("ATTACH DATABASE ':memory:' AS question_bank")
        db.exec_driver_sql('CREATE TABLE question_bank.folders(id TEXT PRIMARY KEY,parent_id TEXT,name TEXT)')
        db.exec_driver_sql('CREATE TABLE question_bank.lists(id TEXT PRIMARY KEY,folder_id TEXT,name TEXT)')
        db.exec_driver_sql('CREATE TABLE question_bank.documents(sha256 TEXT PRIMARY KEY,materia TEXT,content_path TEXT)')
        db.exec_driver_sql('CREATE TABLE question_bank.questions(id TEXT PRIMARY KEY,document_sha256 TEXT,enunciado TEXT,automatic_status TEXT)')
        db.exec_driver_sql('CREATE TABLE question_bank.list_questions(list_id TEXT,question_id TEXT,ordinal INT)')
        db.exec_driver_sql("INSERT INTO question_bank.documents VALUES ('d','Física','[]')")
        db.exec_driver_sql("INSERT INTO question_bank.questions VALUES ('q','d','Enunciado','OK')")
        db.execute(text("INSERT INTO question_bank.folders VALUES (:id,NULL,'Título original')"), {'id': folder})
        db.execute(text("INSERT INTO question_bank.folders VALUES (:id,NULL,'Destino')"), {'id': other})
        db.execute(text("INSERT INTO question_bank.lists VALUES (:id,NULL,'Lista original')"), {'id': list_id})
    return client, engine, folder, other, list_id


@pytest.mark.parametrize('name', ['', '   ', '\t\n', '\u00a0'])
@pytest.mark.parametrize('operation', ['folder-create', 'folder-edit', 'list-create', 'list-edit'])
def test_http_rejects_empty_names_with_readable_422(names, name, operation):
    client, _, folder, _, list_id = names
    endpoints = {
        'folder-create': ('POST', '/folders', {'name': name}),
        'folder-edit': ('PATCH', f'/folders/{folder}', {'name': name}),
        'list-create': ('POST', '/lists', {'name': name, 'count': 1}),
        'list-edit': ('PATCH', f'/lists/{list_id}', {'name': name}),
    }
    method, path, body = endpoints[operation]
    response = client.request(method, '/api/v1/question-bank' + path, json=body)
    assert response.status_code == 422
    assert 'Informe um nome' in response.json()['detail'][0]['msg']


@pytest.mark.parametrize('name,expected', [('Título', 'Título'), ('  Física  ', 'Física'), ('  Duas  palavras  ', 'Duas  palavras')])
def test_valid_names_are_normalized_in_creation_and_editing(names, name, expected):
    client, engine, folder, _, list_id = names
    root = '/api/v1/question-bank'
    created_folder = client.post(root + '/folders', json={'name': name})
    assert created_folder.status_code == 201
    created_list = client.post(root + '/lists', json={'name': name, 'count': 1})
    assert created_list.status_code == 201, created_list.text
    assert client.patch(root + f'/folders/{folder}', json={'name': name}).status_code == 200
    assert client.patch(root + f'/lists/{list_id}', json={'name': name}).status_code == 200
    with Session(engine) as db:
        for table, ids in [('folders', [folder, created_folder.json()['id']]), ('lists', [list_id, created_list.json()['id']])]:
            for id in ids:
                assert db.execute(text(f'SELECT name FROM question_bank.{table} WHERE id=:id'), {'id': id}).scalar_one() == expected


def test_move_or_empty_edit_does_not_rename(names):
    client, engine, folder, other, list_id = names
    root = '/api/v1/question-bank'
    for path, body in [(f'/folders/{folder}', {}), (f'/lists/{list_id}', {}),
                       (f'/folders/{folder}', {'parent_id': other}), (f'/lists/{list_id}', {'folder_id': other})]:
        response = client.patch(root + path, json=body)
        assert response.status_code == 200, response.text
    with Session(engine) as db:
        f = db.execute(text('SELECT name,parent_id FROM question_bank.folders WHERE id=:id'), {'id': folder}).one()
        l = db.execute(text('SELECT name,folder_id FROM question_bank.lists WHERE id=:id'), {'id': list_id}).one()
        assert tuple(f) == ('Título original', other)
        assert tuple(l) == ('Lista original', other)
    assert client.patch(root + f'/folders/{folder}', json={'parent_id': None}).status_code == 200
    assert client.patch(root + f'/lists/{list_id}', json={'folder_id': None}).status_code == 200


@pytest.mark.parametrize('schema,extra,limit', [(FolderIn, {}, 120), (FolderEdit, {}, 120), (ListIn, {'count': 1}, 160), (ListEdit, {}, 160)])
def test_length_limits_apply_after_normalization(schema, extra, limit):
    assert schema(name='  ' + 'x' * limit + '  ', **extra).name == 'x' * limit
    with pytest.raises(ValidationError):
        schema(name='x' * (limit + 1), **extra)
