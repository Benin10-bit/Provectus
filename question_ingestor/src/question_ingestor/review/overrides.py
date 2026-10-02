"""One effective-value implementation for the API, display and future export."""
import json,hashlib,copy
from ..pipeline import utc
from ..parsing.rich import plain_text

FIELDS={'banca_original','banca_normalizada','dificuldade_original','dificuldade_normalizada','gabarito','note'}

def base_hash(q):
    value={k:q.get(k) for k in ['header_original','statement','alternativas','gabarito']}
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def automatic(db,qid):
    row=db.execute('SELECT payload_json FROM questions WHERE id=?',(qid,)).fetchone()
    if row is None:raise KeyError('Question not found')
    return json.loads(row[0])

def value_of(q,field):
    if field.startswith('segment:'):
        sid=field.split(':',1)[1]
        for s in q.get('statement',{}).get('segments',[])+[s for a in q['alternativas'] for s in a.get('segments',[])]:
            if s['id']==sid:return s.get('text')
        raise ValueError('Unknown segment')
    return q.get(field)

def effective(db,qid):
    original=automatic(db,qid);q=copy.deepcopy(original);h=base_hash(original);stale=[];applied=[]
    for field,data,base in db.execute('SELECT field,value_json,base_hash FROM manual_overrides WHERE question_id=?',(qid,)):
        if base!=h:stale.append(field);continue
        value=json.loads(data)
        if field.startswith('segment:'):
            sid=field.split(':',1)[1]
            for s in q.get('statement',{}).get('segments',[])+[s for a in q['alternativas'] for s in a.get('segments',[])]:
                if s['id']==sid:
                    s.update(kind='text',text=value,manual_override=True)
                    for k in ['asset_hash','asset_id','asset_path','recovery_candidate']:s.pop(k,None)
        else:q[field]=value
        applied.append(field)
    if q.get('statement'):
        q['statement']['plain_text']=plain_text(q['statement']['segments']);q['enunciado']=q['statement']['plain_text']
        for a in q['alternativas']:
            a['plain_text']=plain_text(a.get('segments',[]));a['texto']=''.join(s['text'] for s in a.get('segments',[]) if s['kind']=='text').strip() or None
    q['content']=[{**seg,'alternative':owner} for owner,segs in [(None,q.get('statement',{}).get('segments',[]))]+[(a['letra'],a.get('segments',[])) for a in q['alternativas']] for seg in segs]
    review=db.execute('SELECT human_status,base_hash,note FROM review_state WHERE question_id=?',(qid,)).fetchone()
    status=review[0] if review and review[1]==h and not stale else 'UNREVIEWED'
    # Current filesystem hierarchy is authoritative even after a move (without rerunning extraction).
    doc=db.execute('SELECT relative_path,materia,content_path FROM documents WHERE sha256=?',(q['document_sha256'],)).fetchone()
    if doc:q.update(relative_path=doc[0],materia=doc[1],content_path=json.loads(doc[2] or '[]'))
    return {'automatic':original,'effective':q,'automatic_status':original['status'],'human_status':status,'stale_overrides':stale,'applied_fields':applied,'base_hash':h,'note':review[2] if review else None}

def validate_edit(q,field,value):
    if field.startswith('segment:'):
        sid=field.split(':',1)[1];segments=q.get('statement',{}).get('segments',[])+[s for a in q['alternativas'] for s in a.get('segments',[])]
        seg=next((s for s in segments if s['id']==sid),None)
        if not seg or (seg['kind']!='text' and seg.get('role')!='unresolved_symbol'):raise ValueError('Only text and unresolved glyph segments are editable')
        if not isinstance(value,str):raise ValueError('Segment value must be text')
    elif field not in FIELDS:raise ValueError('Unsupported field')
    elif field=='gabarito':
        if value is not None and value not in [a['letra'] for a in q['alternativas']]:raise ValueError('Answer must match an existing alternative or null')
    elif not isinstance(value,str):raise ValueError('Field must be text')

def change(db,qid,edits,note='',expected=None):
    q=automatic(db,qid);h=base_hash(q)
    if expected and expected!=h:raise ValueError('Automatic extraction changed; reload before editing')
    edits=dict(edits)
    if not edits:edits['note']=note
    for field,value in edits.items():validate_edit(q,field,value)
    with db:
        for field,value in edits.items():
            before=value_of(effective(db,qid)['effective'],field)
            db.execute('INSERT INTO manual_overrides VALUES(?,?,?,?,?,?) ON CONFLICT(question_id,field) DO UPDATE SET value_json=excluded.value_json,base_hash=excluded.base_hash,updated_at=excluded.updated_at,note=excluded.note',(qid,field,json.dumps(value,ensure_ascii=False),h,utc(),note))
            db.execute('INSERT INTO review_actions(question_id,field,previous_value,new_value,created_at,note) VALUES(?,?,?,?,?,?)',(qid,field,json.dumps(before,ensure_ascii=False),json.dumps(value,ensure_ascii=False),utc(),note))
        db.execute('INSERT OR REPLACE INTO review_state VALUES(?,?,?,?,?)',(qid,'CORRECTED',h,utc(),note))
    return effective(db,qid)

def approve(db,qid,note='',expected=None):
    data=effective(db,qid)
    if data['stale_overrides']:raise ValueError('Revalidate stale overrides before approval')
    if expected and expected!=data['base_hash']:raise ValueError('Automatic extraction changed; reload')
    with db:
        db.execute('INSERT OR REPLACE INTO review_state VALUES(?,?,?,?,?)',(qid,'APPROVED',data['base_hash'],utc(),note))
        db.execute('INSERT INTO review_actions(question_id,field,previous_value,new_value,created_at,note) VALUES(?,?,?,?,?,?)',(qid,'human_status',json.dumps(data['human_status']),json.dumps('APPROVED'),utc(),note))
    return effective(db,qid)

def revert(db,qid,field,note=''):
    original=automatic(db,qid);data=effective(db,qid)
    if field not in data['applied_fields']+data['stale_overrides']:raise ValueError('No override for field')
    with db:
        before=value_of(data['effective'],field);after=value_of(original,field)
        db.execute('DELETE FROM manual_overrides WHERE question_id=? AND field=?',(qid,field))
        db.execute('DELETE FROM review_state WHERE question_id=?',(qid,))
        db.execute('INSERT INTO review_actions(question_id,field,previous_value,new_value,created_at,note) VALUES(?,?,?,?,?,?)',(qid,field,json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),utc(),'REVERT_TO_AUTOMATIC '+note))
        if db.execute('SELECT 1 FROM manual_overrides WHERE question_id=?',(qid,)).fetchone():db.execute('INSERT INTO review_state VALUES(?,?,?,?,?)',(qid,'CORRECTED',base_hash(original),utc(),note))
    return effective(db,qid)
