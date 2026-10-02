"""Question bank: importer data is read only; only 005 tables hold user state."""
import json
import os
import re
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from .database import get_db

router = APIRouter(prefix='/api/v1/question-bank', tags=['Banco de Questões'])

class Filters(BaseModel):
    paths: list[list[str]] = Field(default_factory=list, max_length=40)
    banks: list[str] = Field(default_factory=list, max_length=30)
    difficulties: list[str] = Field(default_factory=list, max_length=20)
    search: str = Field('', max_length=160)

class FolderIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: UUID | None = None

class FolderEdit(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    parent_id: UUID | None = None

class ListIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    folder_id: UUID | None = None
    count: int = Field(ge=1, le=1000)
    filters: Filters = Field(default_factory=Filters)

class ListEdit(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=160)
    folder_id: UUID | None = None

class Elimination(BaseModel):
    letters: list[str] = Field(max_length=20)

class Answer(BaseModel):
    letter: str = Field(min_length=1, max_length=12)


def exists(db, table, id):
    return db.execute(text(f'SELECT 1 FROM question_bank.{table} WHERE id=:id'), {'id':str(id)}).first() is not None


def require(db, table, id):
    if not exists(db,table,id):raise HTTPException(404,'Registro não encontrado.')


def filters_sql(f: Filters):
    clauses=["q.automatic_status='OK'"]
    args={}
    if f.paths:
        branches=[]
        for i,path in enumerate(f.paths):
            if not path or len(path)>12 or any(not part.strip() or len(part)>160 for part in path):
                raise HTTPException(422,'Caminho de conteúdo inválido.')
            args[f's{i}']=path[0]
            if len(path)==1:
                branches.append(f'(d.materia=:s{i})')
                continue
            for j,part in enumerate(path[1:]):args[f'v{i}_{j}']=part
            def prefix(offset):
                return ' AND '.join(f'd.content_path ->> {j+offset} = :v{i}_{j}' for j in range(len(path)-1))
            branches.append(f'(d.materia=:s{i} AND (({prefix(0)}) OR (d.content_path ->> 0 = :s{i} AND {prefix(1)})))')
        clauses.append('('+' OR '.join(branches)+')')
    if f.banks:clauses.append('q.banca_normalizada IN :banks');args['banks']=tuple(f.banks)
    if f.difficulties:clauses.append('q.dificuldade_normalizada IN :difficulties');args['difficulties']=tuple(f.difficulties)
    if f.search:clauses.append('q.enunciado ILIKE :search');args['search']='%'+f.search.replace('%','\\%').replace('_','\\_')+'%'
    return ' AND '.join(clauses),args


def run_filter(db, sql, params):
    statement=text(sql)
    for name in ('banks','difficulties'):
        if name in params:statement=statement.bindparams(bindparam(name,expanding=True))
    return db.execute(statement,params)


def base(f):
    where,args=filters_sql(f)
    return f' FROM question_bank.questions q JOIN question_bank.documents d ON d.sha256=q.document_sha256 WHERE {where}',args


def dictionary(row):return dict(row._mapping)

@router.get('/filters')
def filter_values(db: Session=Depends(get_db)):
    paths=db.execute(text("SELECT DISTINCT d.materia,d.content_path FROM question_bank.documents d JOIN question_bank.questions q ON q.document_sha256=d.sha256 WHERE q.automatic_status='OK' ORDER BY d.materia")).all()
    tree={}
    for subject,raw in paths:
        parts=raw if isinstance(raw,list) else json.loads(raw)
        if not subject:continue
        if parts and parts[0]==subject:parts=parts[1:]
        current=tree.setdefault(subject,{})
        for part in parts:
            if isinstance(part,str) and part:current=current.setdefault(part,{})
    def nodes(items,prefix=()):return [dict(name=name,path=[*prefix,name],children=nodes(children,(*prefix,name))) for name,children in sorted(items.items())]
    return {'tree':nodes(tree),'banks':db.execute(text("SELECT DISTINCT banca_normalizada FROM question_bank.questions WHERE banca_normalizada IS NOT NULL AND automatic_status='OK' ORDER BY 1")).scalars().all(),
            'difficulties':db.execute(text("SELECT DISTINCT dificuldade_normalizada FROM question_bank.questions WHERE dificuldade_normalizada IS NOT NULL AND automatic_status='OK' ORDER BY 1")).scalars().all()}

@router.post('/search')
def search(filters: Filters, page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    fragment,args=base(filters)
    total=run_filter(db,'SELECT count(*)'+fragment,args).scalar_one()
    rows=run_filter(db,'SELECT q.id,q.enunciado,q.banca_normalizada,q.dificuldade_normalizada,d.materia,d.content_path'+fragment+' ORDER BY q.id LIMIT :limit OFFSET :offset',{**args,'limit':size,'offset':(page-1)*size}).all()
    return {'total':total,'page':page,'size':size,'items':[dictionary(r) for r in rows]}


def media(db, ids):
    if not ids:return {},{}
    alt=db.execute(text("SELECT question_id,letter,ordinal,text,payload -> 'segments' AS segments FROM question_bank.alternatives WHERE question_id IN :ids ORDER BY question_id,ordinal").bindparams(bindparam('ids',expanding=True)),{'ids':ids}).all()
    assets=db.execute(text("SELECT qa.question_id,qa.ordinal,qa.type,qa.alternative_letter,a.hash,a.mime_type FROM question_bank.question_assets qa JOIN question_bank.assets a ON a.hash=qa.asset_hash WHERE qa.question_id IN :ids AND qa.type <> 'ORIGINAL_CROP' ORDER BY qa.question_id,qa.ordinal").bindparams(bindparam('ids',expanding=True)),{'ids':ids}).all()
    alts=defaultdict(list);images=defaultdict(list)
    for row in alt:alts[row.question_id].append(dict(letter=row.letter,ordinal=row.ordinal,text=row.text,segments=row.segments or [],assets=[]))
    for row in assets:
        entry=dict(hash=row.hash,url=f'/api/v1/question-bank/assets/{row.hash}',type=row.type,alt=f'{row.type} da questão',mime_type=row.mime_type)
        if row.alternative_letter:
            target=next((x for x in alts[row.question_id] if x['letter'].upper()==row.alternative_letter.upper()),None)
            if target:target['assets'].append(entry);continue
        images[row.question_id].append(entry)
    return alts,images

@router.get('/questions/{question_id}')
def question(question_id:str, db:Session=Depends(get_db)):
    row=db.execute(text("SELECT q.id,q.enunciado,q.banca_normalizada,q.dificuldade_normalizada,q.numero_original,(q.gabarito IS NOT NULL AND btrim(q.gabarito) <> '') AS has_answer,q.payload -> 'statement' -> 'segments' AS statement_segments,d.materia,d.content_path FROM question_bank.questions q JOIN question_bank.documents d ON d.sha256=q.document_sha256 WHERE q.id=:id AND q.automatic_status='OK'"),{'id':question_id}).first()
    if not row:raise HTTPException(404,'Questão não encontrada.')
    alts,images=media(db,[question_id]);return {**dictionary(row),'alternatives':alts[question_id],'assets':images[question_id]}

@router.post('/questions/{question_id}/check')
def check_individual(question_id:str,payload:Answer,db:Session=Depends(get_db)):
    """Correct an individual attempt without creating a list or persisting an answer."""
    row=db.execute(text("SELECT gabarito FROM question_bank.questions WHERE id=:id AND automatic_status='OK'"),{'id':question_id}).first()
    if not row:raise HTTPException(404,'Questão não encontrada.')
    if not row.gabarito or not row.gabarito.strip():raise HTTPException(422,'Esta questão não tem gabarito registrado.')
    valid=set(db.execute(text('SELECT letter FROM question_bank.alternatives WHERE question_id=:id'),{'id':question_id}).scalars().all())
    if payload.letter not in valid:raise HTTPException(422,'Alternativa inválida.')
    return {'selected':payload.letter,'correct':payload.letter.upper()==row.gabarito.strip().upper(),'answer':row.gabarito}

def asset_path(storage_path):
    root=Path(os.getenv('QUESTION_BANK_ASSETS_ROOT','/app/question-bank-assets')).resolve()
    candidate=(root/storage_path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():raise HTTPException(404,'Imagem indisponível.')
    return candidate

@router.get('/assets/{asset_hash}')
def asset(asset_hash:str,db:Session=Depends(get_db)):
    if not re.fullmatch(r'[0-9a-f]{64}',asset_hash):raise HTTPException(404,'Imagem não encontrada.')
    row=db.execute(text('SELECT storage_path,mime_type FROM question_bank.assets WHERE hash=:hash'),{'hash':asset_hash}).first()
    if not row or row.mime_type not in {'image/png','image/jpeg','image/webp','image/gif'}:raise HTTPException(404,'Imagem não encontrada.')
    candidate=asset_path(row.storage_path)
    return FileResponse(candidate,media_type=row.mime_type,headers={'Cache-Control':'public, max-age=3600'})

@router.get('/library')
def library(db:Session=Depends(get_db)):
    folders=[dictionary(x) for x in db.execute(text('SELECT id,parent_id,name FROM question_bank.folders ORDER BY lower(name)')).all()]
    lists=[dictionary(x) for x in db.execute(text('''SELECT l.id,l.folder_id,l.name,l.created_at,count(lq.question_id) AS total,
     count(a.answered_at) AS answered,count(*) FILTER (WHERE a.correct=true AND a.answered_at IS NOT NULL) AS correct,
     count(*) FILTER (WHERE a.correct=false AND a.answered_at IS NOT NULL) AS wrong
     FROM question_bank.lists l LEFT JOIN question_bank.list_questions lq ON lq.list_id=l.id
     LEFT JOIN question_bank.answers a ON a.list_id=lq.list_id AND a.question_id=lq.question_id
     GROUP BY l.id ORDER BY l.created_at DESC''')).all()]
    return {'folders':folders,'lists':lists}

@router.post('/folders',status_code=201)
def create_folder(payload:FolderIn,db:Session=Depends(get_db)):
    if payload.parent_id:require(db,'folders',payload.parent_id)
    id=str(uuid4());db.execute(text('INSERT INTO question_bank.folders(id,parent_id,name) VALUES (:id,:parent,:name)'),{'id':id,'parent':str(payload.parent_id) if payload.parent_id else None,'name':payload.name.strip()});db.commit();return {'id':id}

@router.patch('/folders/{folder_id}')
def edit_folder(folder_id:UUID,payload:FolderEdit,db:Session=Depends(get_db)):
    require(db,'folders',folder_id)
    if 'parent_id' in payload.model_fields_set and payload.parent_id:
        require(db,'folders',payload.parent_id)
        ancestors=db.execute(text('WITH RECURSIVE nested AS (SELECT id FROM question_bank.folders WHERE id=:id UNION ALL SELECT f.id FROM question_bank.folders f JOIN nested n ON f.parent_id=n.id) SELECT id FROM nested'),{'id':str(folder_id)}).scalars().all()
        if str(payload.parent_id) in {str(x) for x in ancestors}:raise HTTPException(409,'Uma pasta não pode ser movida para dentro de si mesma.')
    if payload.name is not None:db.execute(text('UPDATE question_bank.folders SET name=:name WHERE id=:id'),{'id':str(folder_id),'name':payload.name.strip()})
    if 'parent_id' in payload.model_fields_set:db.execute(text('UPDATE question_bank.folders SET parent_id=:parent WHERE id=:id'),{'id':str(folder_id),'parent':str(payload.parent_id) if payload.parent_id else None})
    db.commit();return {'id':str(folder_id)}

@router.delete('/folders/{folder_id}',status_code=204)
def delete_folder(folder_id:UUID,db:Session=Depends(get_db)):
    require(db,'folders',folder_id)
    if db.execute(text('SELECT 1 FROM question_bank.folders WHERE parent_id=:id UNION ALL SELECT 1 FROM question_bank.lists WHERE folder_id=:id LIMIT 1'),{'id':str(folder_id)}).first():raise HTTPException(409,'Esvazie ou mova as listas e subpastas antes de excluir.')
    db.execute(text('DELETE FROM question_bank.folders WHERE id=:id'),{'id':str(folder_id)});db.commit()

@router.post('/lists',status_code=201)
def create_list(payload:ListIn,db:Session=Depends(get_db)):
    if payload.folder_id:require(db,'folders',payload.folder_id)
    fragment,args=base(payload.filters)
    total=run_filter(db,'SELECT count(*)'+fragment,args).scalar_one()
    if payload.count>total:raise HTTPException(422,f'Existem apenas {total} questões disponíveis para esses filtros.')
    id=str(uuid4())
    with db.begin_nested():
        db.execute(text('INSERT INTO question_bank.lists(id,folder_id,name) VALUES (:id,:folder,:name)'),{'id':id,'folder':str(payload.folder_id) if payload.folder_id else None,'name':payload.name.strip()})
        statement='''INSERT INTO question_bank.list_questions(list_id,question_id,ordinal)
          SELECT :id,qid,row_number() OVER () FROM (SELECT q.id AS qid'''+fragment+' ORDER BY random() LIMIT :limit) chosen'
        run_filter(db,statement,{**args,'id':id,'limit':payload.count})
    db.commit();return {'id':id,'total':payload.count}

@router.patch('/lists/{list_id}')
def edit_list(list_id:UUID,payload:ListEdit,db:Session=Depends(get_db)):
    require(db,'lists',list_id)
    if payload.folder_id:require(db,'folders',payload.folder_id)
    if payload.name is not None:db.execute(text('UPDATE question_bank.lists SET name=:name WHERE id=:id'),{'id':str(list_id),'name':payload.name.strip()})
    if 'folder_id' in payload.model_fields_set:db.execute(text('UPDATE question_bank.lists SET folder_id=:folder WHERE id=:id'),{'id':str(list_id),'folder':str(payload.folder_id) if payload.folder_id else None})
    db.commit();return {'id':str(list_id)}

@router.delete('/lists/{list_id}',status_code=204)
def delete_list(list_id:UUID,db:Session=Depends(get_db)):
    require(db,'lists',list_id);db.execute(text('DELETE FROM question_bank.lists WHERE id=:id'),{'id':str(list_id)});db.commit()

@router.get('/lists/{list_id}')
def list_detail(list_id:UUID,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    require(db,'lists',list_id)
    name=db.execute(text('SELECT name FROM question_bank.lists WHERE id=:id'),{'id':str(list_id)}).scalar_one()
    total=db.execute(text('SELECT count(*) FROM question_bank.list_questions WHERE list_id=:id'),{'id':str(list_id)}).scalar_one()
    rows=db.execute(text('''SELECT lq.ordinal,q.id,q.enunciado,q.banca_normalizada,q.dificuldade_normalizada,q.numero_original,q.payload -> 'statement' -> 'segments' AS statement_segments,d.materia,d.content_path,(q.gabarito IS NOT NULL AND btrim(q.gabarito) <> '') AS has_answer,a.letter AS selected,a.correct,a.answered_at,a.eliminated, CASE WHEN a.answered_at IS NOT NULL THEN q.gabarito END AS answer
      FROM question_bank.list_questions lq JOIN question_bank.questions q ON q.id=lq.question_id JOIN question_bank.documents d ON d.sha256=q.document_sha256
      LEFT JOIN question_bank.answers a ON a.list_id=lq.list_id AND a.question_id=lq.question_id
      WHERE lq.list_id=:id ORDER BY lq.ordinal LIMIT :size OFFSET :offset'''),{'id':str(list_id),'size':size,'offset':(page-1)*size}).all()
    ids=[r.id for r in rows];alts,images=media(db,ids)
    result=[]
    for r in rows:
        data=dictionary(r)
        data['eliminated']=data['eliminated'] or []
        data['alternatives']=alts[r.id];data['assets']=images[r.id]
        result.append(data)
    return {'id':str(list_id),'name':name,'total':total,'page':page,'size':size,'items':result}

def membership(db,list_id,question_id):
    if not db.execute(text('SELECT 1 FROM question_bank.list_questions WHERE list_id=:list_id AND question_id=:qid'),{'list_id':str(list_id),'qid':question_id}).first():raise HTTPException(404,'Questão fora desta lista.')

@router.put('/lists/{list_id}/questions/{question_id}/eliminated')
def eliminated(list_id:UUID,question_id:str,payload:Elimination,db:Session=Depends(get_db)):
    membership(db,list_id,question_id)
    valid=set(db.execute(text('SELECT letter FROM question_bank.alternatives WHERE question_id=:qid'),{'qid':question_id}).scalars())
    if not set(payload.letters)<=valid:raise HTTPException(422,'Alternativa inválida.')
    db.execute(text('''INSERT INTO question_bank.answers(list_id,question_id,letter,eliminated) VALUES (:list_id,:qid,'',CAST(:eliminated AS jsonb))
      ON CONFLICT(list_id,question_id) DO UPDATE SET eliminated=EXCLUDED.eliminated WHERE answers.answered_at IS NULL'''),{'list_id':str(list_id),'qid':question_id,'eliminated':json.dumps(list(dict.fromkeys(payload.letters)))});db.commit()
    return {'eliminated':payload.letters}

@router.post('/lists/{list_id}/questions/{question_id}/answer')
def answer(list_id:UUID,question_id:str,payload:Answer,db:Session=Depends(get_db)):
    membership(db,list_id,question_id)
    data=db.execute(text('SELECT gabarito FROM question_bank.questions WHERE id=:qid'),{'qid':question_id}).first()
    if not data or not data.gabarito:raise HTTPException(422,'Esta questão não tem gabarito registrado.')
    exists_answer=db.execute(text('SELECT letter,correct,answered_at FROM question_bank.answers WHERE list_id=:lid AND question_id=:qid'),{'lid':str(list_id),'qid':question_id}).first()
    if exists_answer and exists_answer.answered_at:return {'selected':exists_answer.letter,'correct':exists_answer.correct,'answer':data.gabarito}
    valid=set(db.execute(text('SELECT letter FROM question_bank.alternatives WHERE question_id=:qid'),{'qid':question_id}).scalars())
    if payload.letter not in valid:raise HTTPException(422,'Alternativa inválida.')
    correct=payload.letter.upper()==data.gabarito.strip().upper()
    db.execute(text('''INSERT INTO question_bank.answers(list_id,question_id,letter,correct,answered_at) VALUES (:lid,:qid,:letter,:correct,now())
      ON CONFLICT(list_id,question_id) DO UPDATE SET letter=EXCLUDED.letter,correct=EXCLUDED.correct,answered_at=EXCLUDED.answered_at
      WHERE answers.answered_at IS NULL'''),{'lid':str(list_id),'qid':question_id,'letter':payload.letter,'correct':correct})
    db.commit();return {'selected':payload.letter,'correct':correct,'answer':data.gabarito}

@router.get('/lists/{list_id}/export.pdf')
def export_pdf(list_id:UUID,db:Session=Depends(get_db),answer_placement:Literal['end','after_each']='end'):
    """Keep the existing URL; the optional answer placement defaults to the final key."""
    from .question_pdf import build_notebook, PDFContentError
    require(db,'lists',list_id)
    name=db.execute(text('SELECT name FROM question_bank.lists WHERE id=:id'),{'id':str(list_id)}).scalar_one()
    rows=db.execute(text("""SELECT lq.ordinal,q.id,q.enunciado,q.gabarito,q.banca_normalizada,
        q.dificuldade_normalizada,q.payload -> 'statement' -> 'segments' AS statement_segments,
        d.materia,d.content_path FROM question_bank.list_questions lq
        JOIN question_bank.questions q ON q.id=lq.question_id
        JOIN question_bank.documents d ON d.sha256=q.document_sha256
        WHERE lq.list_id=:id ORDER BY lq.ordinal"""),{'id':str(list_id)}).all()
    questions=[dictionary(row) for row in rows]
    image_index={}
    for offset in range(0,len(questions),200):
        chunk=questions[offset:offset+200];ids=[q['id'] for q in chunk]
        alternatives,images=media(db,ids)
        for q in chunk:
            q['alternatives']=alternatives[q['id']];q['assets']=images[q['id']]
            for alt in q['alternatives']:
                if isinstance(alt['segments'],str):alt['segments']=json.loads(alt['segments'])
            for field in ('statement_segments','content_path'):
                if isinstance(q[field],str):q[field]=json.loads(q[field])
        statement=text("""SELECT DISTINCT a.hash,a.storage_path FROM question_bank.question_assets qa
          JOIN question_bank.assets a ON a.hash=qa.asset_hash WHERE qa.question_id IN :ids
          AND qa.type <> 'ORIGINAL_CROP'""").bindparams(bindparam('ids',expanding=True))
        for image in db.execute(statement,{'ids':ids}):image_index[image.hash]={'storage_path':image.storage_path}
    try:
        output=build_notebook(name,questions,image_index,asset_path,answer_placement)
    except PDFContentError as exc:
        raise HTTPException(422,f'PDF não gerado: {exc}') from exc
    return StreamingResponse(output,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="lista-{list_id}.pdf"'})
