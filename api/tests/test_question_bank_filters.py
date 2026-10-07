"""Run the real filter queries against isolated data; no production DB access."""
import os
os.environ.setdefault('DATABASE_URL','sqlite://')
from uuid import UUID
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.question_bank import Filters, ListIn, Answer, search, create_list, check_individual, mark_solved, delete_list, answer

@pytest.fixture
def db():
    engine=create_engine('sqlite://')
    with engine.begin() as c:
        c.exec_driver_sql("ATTACH DATABASE ':memory:' AS question_bank")
        c.connection.driver_connection.create_function('now',0,lambda:'2026-10-06 20:00:00')
        c.exec_driver_sql('CREATE TABLE question_bank.documents(sha256 TEXT PRIMARY KEY,materia TEXT,content_path TEXT)')
        c.exec_driver_sql('CREATE TABLE question_bank.questions(id TEXT PRIMARY KEY,document_sha256 TEXT,enunciado TEXT,banca_normalizada TEXT,dificuldade_normalizada TEXT,automatic_status TEXT,gabarito TEXT)')
        c.exec_driver_sql('CREATE TABLE question_bank.alternatives(question_id TEXT,letter TEXT)')
        c.exec_driver_sql('CREATE TABLE question_bank.solved_questions(question_id TEXT PRIMARY KEY,answered_at TEXT DEFAULT CURRENT_TIMESTAMP,correct BOOLEAN,last_answered_at TEXT)')
        c.exec_driver_sql('CREATE TABLE question_bank.answers(list_id TEXT,question_id TEXT,answered_at TEXT,letter TEXT,correct BOOLEAN,PRIMARY KEY(list_id,question_id))')
        c.exec_driver_sql('CREATE TABLE question_bank.lists(id TEXT PRIMARY KEY,folder_id TEXT,name TEXT,generation TEXT)')
        c.exec_driver_sql('CREATE TABLE question_bank.list_questions(list_id TEXT,question_id TEXT,ordinal INT)')
        c.exec_driver_sql("INSERT INTO question_bank.documents VALUES ('d','Física','[]')")
        for qid,bank,level,status,key in [('q1','EsPCEx','FACIL','OK','B'),('q2','ENEM','DIFICIL','OK','B'),('q3','ITA','MEDIA','OK','B'),('q4','EsPCEx','DIFICIL','OK','B'),('review','ENEM','FACIL','REVIEW','B'),('no-key','EsPCEx','MEDIA','OK',None)]:
            c.execute(text("INSERT INTO question_bank.questions VALUES (:q,'d','Enunciado',:b,:l,:s,:k)"),dict(q=qid,b=bank,l=level,s=status,k=key))
            for letter in ['A','B']:c.execute(text('INSERT INTO question_bank.alternatives VALUES (:q,:l)'),dict(q=qid,l=letter))
    with Session(engine) as session:yield session
    engine.dispose()

def ids(result):return {q['id'] for q in result['items']}

def test_multiple_filters_combine_with_or_within_and_between_groups(db):
    f=Filters(banks=['EsPCEx','ENEM'],difficulties=['FACIL','DIFICIL'])
    assert ids(search(f,1,20,db))=={'q1','q2','q4'}
    mark_solved(db,'q1');db.commit()
    f.exclude_answered=True
    r=search(f,1,1,db)
    assert r['total']==2 and len(r['items'])==1
    assert ids(search(f,1,20,db))=={'q2','q4'}
    assert search(Filters(exclude_answered=True),1,20,db)['total']==4
    assert search(Filters(),1,20,db)['total']==5

def test_new_list_uses_same_exclusion_and_rejects_excess_count(db):
    mark_solved(db,'q1');db.commit()
    f=Filters(banks=['EsPCEx','ENEM'],difficulties=['FACIL','DIFICIL'],exclude_answered=True)
    with pytest.raises(HTTPException) as exc:create_list(ListIn(name='Nova',count=3,filters=f),db)
    assert exc.value.status_code==422
    assert db.execute(text('SELECT count(*) FROM question_bank.lists')).scalar_one()==0
    result=create_list(ListIn(name='Nova',count=2,filters=f),db)
    assert set(db.execute(text('SELECT question_id FROM question_bank.list_questions WHERE list_id=:l'),{'l':result['id']}).scalars())=={'q2','q4'}

def test_individual_correct_wrong_repeat_and_invalid_answers(db):
    assert check_individual('q1',Answer(letter='A'),db)['correct'] is False
    assert check_individual('q2',Answer(letter='B'),db)['correct'] is True
    check_individual('q1',Answer(letter='B'),db)
    assert set(db.execute(text('SELECT question_id FROM question_bank.solved_questions')).scalars())=={'q1','q2'}
    for qid,letter in [('q3','C'),('no-key','A')]:
        with pytest.raises(HTTPException):check_individual(qid,Answer(letter=letter),db)
    assert ids(search(Filters(exclude_answered=True),1,20,db))=={'q3','q4','no-key'}

def test_deleting_list_preserves_solved_history(db):
    result=create_list(ListIn(name='Antiga',count=1,filters=Filters(banks=['ITA'])),db)
    mark_solved(db,'q3');db.commit()
    delete_list(UUID(result['id']),db)
    assert 'q3' not in ids(search(Filters(exclude_answered=True),1,20,db))


def test_list_answer_marks_question_solved_and_repeated_answer_stays_idempotent(db):
    result=create_list(ListIn(name='Prática',count=1,filters=Filters(banks=['ITA'])),db)
    lid=UUID(result['id'])
    assert not answer(lid,'q3',Answer(letter='A'),db)['correct']
    assert answer(lid,'q3',Answer(letter='B'),db)['selected']=='A'
    assert db.execute(text('SELECT count(*) FROM question_bank.solved_questions')).scalar_one()==1
    assert 'q3' not in ids(search(Filters(exclude_answered=True),1,20,db))
    delete_list(lid,db)
    assert 'q3' not in ids(search(Filters(exclude_answered=True),1,20,db))


def test_migration_preserves_old_answers_and_excludes_only_completed_attempts(db):
    from pathlib import Path
    source=Path(__file__).resolve().parents[1].joinpath('migrations/006_question_bank_solved.sql').read_text()
    db.execute(text("INSERT INTO question_bank.answers(list_id,question_id,answered_at) VALUES ('l1','q1','2026-09-01'),('l2','q1','2026-10-01'),('l1','q2',NULL)"))
    backfill=source[source.index('INSERT INTO question_bank.solved_questions'):]
    db.execute(text(backfill));db.commit()
    assert db.execute(text('SELECT question_id,answered_at FROM question_bank.solved_questions')).all()==[('q1','2026-09-01')]
    assert 'q2' in ids(search(Filters(exclude_answered=True),1,20,db))


def test_result_filters_follow_latest_correction_and_apply_to_new_lists(db):
    check_individual('q1',Answer(letter='A'),db)
    check_individual('q2',Answer(letter='B'),db)
    assert ids(search(Filters(result='incorrect'),1,20,db))=={'q1'}
    assert ids(search(Filters(result='correct'),1,20,db))=={'q2'}
    assert search(Filters(result='correct',banks=['ITA']),1,20,db)['total']==0
    result=create_list(ListIn(name='Rever erros',count=1,filters=Filters(result='incorrect')),db)
    assert db.execute(text('SELECT question_id FROM question_bank.list_questions WHERE list_id=:l'),{'l':result['id']}).scalar_one()=='q1'
    check_individual('q1',Answer(letter='B'),db)
    assert search(Filters(result='incorrect'),1,20,db)['total']==0
    assert ids(search(Filters(result='correct'),1,20,db))=={'q1','q2'}
    delete_list(UUID(result['id']),db)
    assert ids(search(Filters(result='correct'),1,20,db))=={'q1','q2'}


def test_old_list_replay_does_not_overwrite_newer_individual_correction(db):
    result=create_list(ListIn(name='Prática',count=1,filters=Filters(banks=['ITA'])),db)
    lid=UUID(result['id'])
    answer(lid,'q3',Answer(letter='A'),db)
    db.execute(text("UPDATE question_bank.answers SET answered_at='2026-10-01' WHERE question_id='q3'"));db.commit()
    check_individual('q3',Answer(letter='B'),db)
    assert not answer(lid,'q3',Answer(letter='A'),db)['correct']
    assert ids(search(Filters(result='correct'),1,20,db))=={'q3'}


def test_unknown_legacy_correction_and_conflicting_filters(db):
    mark_solved(db,'q1');db.commit()
    assert search(Filters(result='correct'),1,20,db)['total']==0
    assert search(Filters(result='incorrect'),1,20,db)['total']==0
    assert 'q1' not in ids(search(Filters(exclude_answered=True),1,20,db))
    with pytest.raises(HTTPException) as exc:search(Filters(result='incorrect',exclude_answered=True),1,20,db)
    assert exc.value.status_code==422
