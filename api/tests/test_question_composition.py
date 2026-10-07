import os
os.environ.setdefault('DATABASE_URL','sqlite://')
import json
import random
import pytest
from sqlalchemy import text, event
from fastapi import HTTPException
from app.question_composition import Composition, CompositionNode as N, allocate, catalog, resolve
from app.question_bank import Filters, ListIn, PreviewIn, availability, preview, create_list
from test_question_bank_filters import db


def hierarchy():
    return catalog([('Matemática',['Geometria','Plana'],12),('Matemática',['Álgebra','Funções'],20),('Português',['Sintaxe','Regência'],18),('Português',['Sintaxe','Crase'],5),('Física',['Óptica'],0)])

def manual_example():
    return Composition(distribution='manual',nodes=[
        N(path=['Matemática'],quantity=4,distribution='manual',children=[N(path=['Matemática','Geometria'],quantity=4,distribution='manual',children=[N(path=['Matemática','Geometria','Plana'],quantity=4)])]),
        N(path=['Português'],quantity=5,distribution='manual',children=[N(path=['Português','Sintaxe'],quantity=5,distribution='manual',children=[N(path=['Português','Sintaxe','Regência'],quantity=5)])])])


def test_exact_manual_example_and_locked_preview():
    result=resolve(hierarchy(),manual_example(),9)
    assert [(g['path'],g['quantity']) for g in result['groups']]==[(['Matemática','Geometria','Plana'],4),(['Português','Sintaxe','Regência'],5)]
    locked=Composition(**result['resolved'])
    assert resolve(hierarchy(),locked,9)['groups']==result['groups']


def test_random_multiple_seeds_invariants_and_variation():
    allocations=set()
    for seed in range(150):
        values=allocate(30,[(0,100),(0,3),(0,100),(0,100),(0,0)],random.Random(seed))
        assert sum(values)==30 and 1<=values[1]<=3 and values[-1]==0
        assert all(1<=n<=100 for n in [values[0],values[2],values[3]])
        allocations.add(tuple(values))
        result=resolve(hierarchy(),Composition(seed=str(seed)),20)
        assert sum(n['quantity'] for n in result['resolved']['nodes'])==20
        assert sum(g['quantity'] for g in result['groups'])==20
        assert all(g['quantity']>0 for g in result['groups'])
    assert len(allocations)>10
    assert sum(allocate(2,[(0,10)]*4,random.Random(1)))==2


def test_subjects_manual_contents_auto_and_mixed_branches():
    composition=Composition(distribution='manual',nodes=[N(path=['Matemática'],quantity=10),N(path=['Português'],quantity=5,distribution='manual',children=[N(path=['Português','Sintaxe'],quantity=5,distribution='manual',children=[N(path=['Português','Sintaxe','Regência'],quantity=5)])])])
    result=resolve(hierarchy(),composition,15)
    assert [n['quantity'] for n in result['resolved']['nodes']]==[10,5]
    assert sum(g['quantity'] for g in result['groups'] if g['path'][0]=='Matemática')==10
    assert next(g for g in result['groups'] if g['path'][0]=='Português')['path'][-1]=='Regência'


def test_auto_subjects_reserve_manually_defined_content_totals():
    c=Composition(nodes=[N(path=['Matemática'],distribution='manual',children=[N(path=['Matemática','Geometria'],quantity=4)]),N(path=['Português'])])
    result=resolve(hierarchy(),c,14)
    assert [n['quantity'] for n in result['resolved']['nodes']]==[4,10]
    assert any(g['path']==['Matemática','Geometria','Plana'] and g['quantity']==4 for g in result['groups'])


def test_partial_fixed_plus_auto_and_empty_children_are_not_all_contents():
    c=Composition(distribution='manual',nodes=[N(path=['Matemática'],quantity=10,distribution='manual',children=[N(path=['Matemática','Geometria'],quantity=4),N(path=['Matemática','Álgebra'])])])
    result=resolve(hierarchy(),c,10)
    assert sorted(g['quantity'] for g in result['groups'])==[4,6]
    with pytest.raises(HTTPException):resolve(hierarchy(),Composition(nodes=[N(path=['Matemática'],children=[])]),3)


@pytest.mark.parametrize('composition,total',[
    (manual_example(),10),(manual_example(),8),
    (Composition(nodes=[N(path=['Desconhecida'])]),1),
    (Composition(nodes=[N(path=['Matemática']),N(path=['Matemática'])]),1),
    (Composition(nodes=[N(path=['Matemática','Geometria'])]),1),
    (Composition(nodes=[N(path=['Matemática'],children=[N(path=['Português','Sintaxe'])])]),1),
    (Composition(distribution='manual',nodes=[N(path=['Física'],quantity=1)]),1),
    (Composition(),100),
])
def test_impossible_requests_are_structured_errors(composition,total):
    with pytest.raises(HTTPException) as exc:resolve(hierarchy(),composition,total)
    assert exc.value.status_code==422 and 'code' in exc.value.detail and 'path' in exc.value.detail


def test_four_content_levels_and_direct_parent_buckets_do_not_overlap():
    tree=catalog([('M',['A','B','C','D'],12),('M',['A','B'],4),('M',['M','A','B','C','D'],3)])
    result=resolve(tree,Composition(),10)
    assert len(result['groups'])==2
    assert sum(g['quantity'] for g in result['groups'])==10
    assert {tuple(g['path']) for g in result['groups']}=={('M','A','B'),('M','A','B','C','D')}
    deep=next(g for g in result['groups'] if len(g['path'])==5)
    assert deep['quantity']<=15


def populate(db):
    db.execute(text('DELETE FROM question_bank.questions'))
    db.execute(text('DELETE FROM question_bank.documents'))
    for doc,subject,path,size in [('g','Matemática',['Geometria','Plana'],12),('f','Matemática',['Matemática','Álgebra','Funções'],15),('r','Português',['Sintaxe','Regência'],12)]:
        db.execute(text('INSERT INTO question_bank.documents VALUES (:d,:s,:p)'),dict(d=doc,s=subject,p=json.dumps(path)))
        for i in range(size):db.execute(text("INSERT INTO question_bank.questions VALUES (:q,:d,'Enunciado','EsPCEx',:level,'OK','B')"),dict(q=f'{doc}{i}',d=doc,level='FACIL' if i%2==0 else 'DIFICIL'))
    db.commit()


def test_actual_sql_selection_exact_distinct_reproducible_and_metadata(db):
    populate(db)
    tree=availability(Filters(),db)
    assert tree['total']==39
    p=preview(PreviewIn(count=9,composition=manual_example()),db)
    result=create_list(ListIn(name='Composta',count=9,composition=Composition(**p['resolved'])),db)
    rows=db.execute(text('SELECT question_id,ordinal FROM question_bank.list_questions WHERE list_id=:id ORDER BY ordinal'),{'id':result['id']}).all()
    assert len(rows)==9 and len({r.question_id for r in rows})==9
    assert sum(r.question_id.startswith('g') for r in rows)==4
    assert sum(r.question_id.startswith('r') for r in rows)==5
    assert [r.ordinal for r in rows]==list(range(1,10))
    assert db.execute(text('SELECT question_id,ordinal FROM question_bank.list_questions WHERE list_id=:id ORDER BY ordinal'),{'id':result['id']}).all()==rows
    metadata=json.loads(db.execute(text('SELECT generation FROM question_bank.lists WHERE id=:id'),{'id':result['id']}).scalar_one())
    assert metadata['actual']==p['resolved'] and metadata['order']=='shuffle'


def test_all_filters_affect_availability_and_sampling(db):
    populate(db)
    db.execute(text("INSERT INTO question_bank.solved_questions(question_id,correct,last_answered_at) VALUES ('g0',true,'2026-10-01'),('g2',false,'2026-10-01')"));db.commit()
    f=Filters(banks=['EsPCEx','ENEM'],difficulties=['FACIL'],exclude_answered=True,paths=[['Matemática','Geometria']])
    assert availability(f,db)['total']==4
    with pytest.raises(HTTPException):create_list(ListIn(name='Impossível',count=5,filters=f,composition=Composition()),db)
    result=create_list(ListIn(name='Novas',count=4,filters=f,composition=Composition()),db)
    chosen=set(db.execute(text('SELECT question_id FROM question_bank.list_questions WHERE list_id=:id'),{'id':result['id']}).scalars())
    assert chosen=={'g4','g6','g8','g10'}
    for result_filter,qid in [('correct','g0'),('incorrect','g2')]:
        filters=Filters(result=result_filter)
        assert availability(filters,db)['total']==1
        value=create_list(ListIn(name=result_filter,count=1,filters=filters,composition=Composition()),db)
        assert db.execute(text('SELECT question_id FROM question_bank.list_questions WHERE list_id=:id'),{'id':value['id']}).scalar_one()==qid
    assert availability(Filters(banks=['ITA']),db)['total']==0


def test_grouped_order_and_legacy_create_remain_valid(db):
    populate(db)
    result=create_list(ListIn(name='Agrupada',count=9,composition=manual_example(),order='grouped'),db)
    ids=db.execute(text('SELECT question_id FROM question_bank.list_questions WHERE list_id=:id ORDER BY ordinal'),{'id':result['id']}).scalars().all()
    assert all(q.startswith('g') for q in ids[:4]) and all(q.startswith('r') for q in ids[4:])
    old=create_list(ListIn(name='Antiga API',count=3),db)
    assert db.execute(text('SELECT count(*) FROM question_bank.list_questions WHERE list_id=:id'),{'id':old['id']}).scalar_one()==3


def test_atomic_creation_rolls_back_list_and_items_on_insert_failure(db):
    populate(db)
    db.execute(text("CREATE TRIGGER question_bank.stop_insert BEFORE INSERT ON list_questions BEGIN SELECT RAISE(ABORT,'simulated'); END"));db.commit()
    with pytest.raises(Exception):create_list(ListIn(name='Falha',count=9,composition=manual_example()),db)
    assert db.execute(text('SELECT count(*) FROM question_bank.lists')).scalar_one()==0
    assert db.execute(text('SELECT count(*) FROM question_bank.list_questions')).scalar_one()==0
