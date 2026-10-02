import sqlite3,json
from contextlib import nullcontext
from pathlib import Path

SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS documents(sha256 TEXT PRIMARY KEY,source_file TEXT NOT NULL,pages INTEGER NOT NULL,metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS processing_jobs(id TEXT PRIMARY KEY,document_sha256 TEXT NOT NULL,config_hash TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('PENDING','PROCESSING','DONE','FAILED')),started_at TEXT,finished_at TEXT,error_code TEXT);
CREATE TABLE IF NOT EXISTS questions(id TEXT PRIMARY KEY,document_sha256 TEXT REFERENCES documents(sha256),job_id TEXT REFERENCES processing_jobs(id),numero_original INTEGER,status TEXT NOT NULL CHECK(status IN ('OK','REVIEW','ERROR')),pagina_inicio INTEGER,pagina_fim INTEGER,bank TEXT,difficulty TEXT,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alternatives(question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,ordinal INTEGER,letter TEXT,text TEXT,PRIMARY KEY(question_id,ordinal));
CREATE TABLE IF NOT EXISTS assets(hash TEXT PRIMARY KEY,path TEXT NOT NULL,mime_type TEXT,width INTEGER,height INTEGER,size_bytes INTEGER);
CREATE TABLE IF NOT EXISTS question_assets(question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,ordinal INTEGER,asset_hash TEXT REFERENCES assets(hash),alternative_letter TEXT,type TEXT,page INTEGER,bbox_json TEXT,metadata_json TEXT,PRIMARY KEY(question_id,ordinal));
CREATE TABLE IF NOT EXISTS warnings(question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,ordinal INTEGER,code TEXT,severity TEXT,component TEXT,page INTEGER,payload_json TEXT,PRIMARY KEY(question_id,ordinal));
CREATE TABLE IF NOT EXISTS validation_results(question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,component TEXT,rule TEXT,passed INTEGER,PRIMARY KEY(question_id,component,rule));
CREATE TABLE IF NOT EXISTS content_segments(question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,owner TEXT NOT NULL,ordinal INTEGER,kind TEXT,display TEXT,page INTEGER,bbox_json TEXT,text TEXT,asset_hash TEXT REFERENCES assets(hash),payload_json TEXT NOT NULL,PRIMARY KEY(question_id,owner,ordinal));
CREATE TABLE IF NOT EXISTS duplicate_candidates(question_a TEXT REFERENCES questions(id),question_b TEXT REFERENCES questions(id),status TEXT,score REAL,evidence_json TEXT,PRIMARY KEY(question_a,question_b));
CREATE TABLE IF NOT EXISTS review_decisions(question_id TEXT REFERENCES questions(id),decision TEXT,reviewer TEXT,decided_at TEXT,notes TEXT);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);
CREATE INDEX IF NOT EXISTS idx_questions_doc ON questions(document_sha256);
CREATE INDEX IF NOT EXISTS idx_warnings_code ON warnings(code);
'''

def connect(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path);db.executescript(SCHEMA);return db

def persist(db,meta,questions,job_id,transaction=True):
    with db if transaction else nullcontext():
        db.execute('INSERT INTO documents(sha256,source_file,pages,metadata_json) VALUES(?,?,?,?) ON CONFLICT(sha256) DO UPDATE SET source_file=excluded.source_file,pages=excluded.pages,metadata_json=excluded.metadata_json',(meta['document_sha256'],meta['source_file'],meta['pages'],json.dumps(meta,ensure_ascii=False)))
        for q in questions:
            # Explicit update preserves review references; children are regenerated atomically.
            vals=(q['extraction_id'],q['document_sha256'],job_id,q.get('numero_original'),q['status'],q['pagina_inicio'],q['pagina_fim'],q.get('banca_normalizada'),q.get('dificuldade_normalizada'),json.dumps(q,ensure_ascii=False))
            db.execute('INSERT INTO questions VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET job_id=excluded.job_id,numero_original=excluded.numero_original,status=excluded.status,pagina_inicio=excluded.pagina_inicio,pagina_fim=excluded.pagina_fim,bank=excluded.bank,difficulty=excluded.difficulty,payload_json=excluded.payload_json',vals)
            for table in ['alternatives','question_assets','warnings','validation_results','content_segments']:db.execute(f'DELETE FROM {table} WHERE question_id=?',(q['extraction_id'],))
            for i,a in enumerate(q['alternativas']):db.execute('INSERT INTO alternatives VALUES(?,?,?,?)',(q['extraction_id'],i,a['letra'],a['texto']))
            assets=[(None,a) for a in q['imagens']+q['originals']]+[(opt['letra'],a) for opt in q['alternativas'] for a in opt['imagens']]
            for i,(letter,a) in enumerate(assets):
                db.execute('INSERT OR IGNORE INTO assets VALUES(?,?,?,?,?,?)',(a['hash'],a['path'],a['mime_type'],a['width'],a['height'],a['size_bytes']))
                db.execute('INSERT INTO question_assets VALUES(?,?,?,?,?,?,?,?)',(q['extraction_id'],i,a['hash'],letter,a['type'],a['page'],json.dumps(a['bbox']),json.dumps(a)))
            groups=[('',q.get('statement',{}).get('segments',[]))]+[(a['letra'],a.get('segments',[])) for a in q['alternativas']]
            for owner,segments in groups:
                for i,segment in enumerate(segments):
                    db.execute('INSERT INTO content_segments VALUES(?,?,?,?,?,?,?,?,?,?)',(q['extraction_id'],owner,i,segment['kind'],segment.get('display'),segment['page'],json.dumps(segment['bbox']),segment.get('text'),segment.get('asset_hash'),json.dumps(segment,ensure_ascii=False)))
            for i,w in enumerate(q['warnings']):db.execute('INSERT INTO warnings VALUES(?,?,?,?,?,?,?)',(q['extraction_id'],i,w['code'],w['severity'],w['component'],w['page'],json.dumps(w)))
            for comp,rules in q['confidence_evidence'].items():
                for rule,passed in rules.items():db.execute('INSERT INTO validation_results VALUES(?,?,?,?)',(q['extraction_id'],comp,rule,int(passed)))

def load_segments(db,question_id,owner=''):
    return [json.loads(row[0]) for row in db.execute('SELECT payload_json FROM content_segments WHERE question_id=? AND owner=? ORDER BY ordinal',(question_id,owner))]
