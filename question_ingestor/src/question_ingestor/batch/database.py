import json
from ..staging.database import connect,persist

SCHEMA='''
CREATE TABLE IF NOT EXISTS batch_jobs(id TEXT PRIMARY KEY,root TEXT,output TEXT,config_json TEXT,parser_version TEXT,started_at TEXT,finished_at TEXT,status TEXT,summary_json TEXT);
CREATE TABLE IF NOT EXISTS batch_items(job_id TEXT,relative_path TEXT,sha256 TEXT,state TEXT,error_code TEXT,duration REAL,PRIMARY KEY(job_id,relative_path));
CREATE TABLE IF NOT EXISTS document_paths(root TEXT,relative_path TEXT,sha256 TEXT REFERENCES documents(sha256),hierarchy_json TEXT,seen_job TEXT,PRIMARY KEY(root,relative_path,sha256));
CREATE TABLE IF NOT EXISTS manual_overrides(question_id TEXT REFERENCES questions(id),field TEXT,value_json TEXT,base_hash TEXT,updated_at TEXT,note TEXT,PRIMARY KEY(question_id,field));
CREATE TABLE IF NOT EXISTS review_state(question_id TEXT PRIMARY KEY REFERENCES questions(id),human_status TEXT,base_hash TEXT,updated_at TEXT,note TEXT);
CREATE TABLE IF NOT EXISTS review_actions(id INTEGER PRIMARY KEY AUTOINCREMENT,question_id TEXT REFERENCES questions(id),field TEXT,previous_value TEXT,new_value TEXT,created_at TEXT,note TEXT);
CREATE INDEX IF NOT EXISTS idx_questions_number ON questions(numero_original);
CREATE INDEX IF NOT EXISTS idx_documents_materia ON documents(materia);
'''
COLUMNS={'relative_path':'TEXT','file_stem':'TEXT','materia':'TEXT','content_path':'TEXT','size_bytes':'INTEGER','parser_version':'TEXT','raw_schema_version':'INTEGER','config_hash':'TEXT','processing_status':'TEXT','started_at':'TEXT','finished_at':'TEXT','processing_duration':'REAL','report_json':'TEXT','error_code':'TEXT','output_path':'TEXT'}

def open_global(path):
    # The batch and review editor are mutually exclusive. Rollback journaling
    # avoids a large WAL checkpoint at shutdown for long PDF documents.
    db=connect(path);db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA busy_timeout=5000')
    existing={r[1] for r in db.execute('PRAGMA table_info(documents)')}
    for column,typ in COLUMNS.items():
        if column not in existing:db.execute(f'ALTER TABLE documents ADD COLUMN {column} {typ}')
    db.executescript(SCHEMA);return db

def register(db,digest,h,size,root,job,parser,cfg_hash,raw_version,out):
    with db:
        db.execute('INSERT OR IGNORE INTO documents(sha256,source_file,pages,metadata_json,processing_status) VALUES(?,?,0,?,?)',(digest,h['filename'],'{}','PENDING'))
        db.execute('INSERT INTO document_paths VALUES(?,?,?,?,?) ON CONFLICT(root,relative_path,sha256) DO UPDATE SET hierarchy_json=excluded.hierarchy_json,seen_job=excluded.seen_job',(str(root),h['relative_path'],digest,json.dumps(h,ensure_ascii=False),job))
        db.execute('UPDATE documents SET relative_path=?,source_file=?,file_stem=?,materia=?,content_path=?,size_bytes=?,output_path=? WHERE sha256=?',(h['relative_path'],h['filename'],h['file_stem'],h['materia'],json.dumps(h['content_path'],ensure_ascii=False),size,out,digest))

def synchronize(db,docroot,meta,qs,result,job,parser,config_hash,cfg):
    from ..pipeline import utc
    from ..pdf.extraction import sha256_file
    digest=meta['document_sha256'];local_manifest=json.loads((docroot/'manifest.json').read_text());processing_id=local_manifest['job_id']
    with db:
        db.execute('INSERT OR REPLACE INTO processing_jobs(id,document_sha256,config_hash,state,started_at,finished_at) VALUES(?,?,?,?,?,?)',(processing_id,digest,config_hash,'DONE',utc(),utc()))
        persist(db,meta,qs,processing_id,transaction=False)
        # Remove obsolete automatic rows only if they have no manual history; preserve reviewed rows explicitly.
        ids={q['extraction_id'] for q in qs}
        for (qid,) in db.execute('SELECT id FROM questions WHERE document_sha256=?',(digest,)).fetchall():
            if qid not in ids:
                protected=db.execute('SELECT 1 FROM review_actions WHERE question_id=? LIMIT 1',(qid,)).fetchone()
                if protected:raise ValueError('REPROCESS_WOULD_ORPHAN_MANUAL_REVIEW')
                db.execute('DELETE FROM questions WHERE id=?',(qid,))
        db.execute("UPDATE documents SET processing_status='DONE',parser_version=?,raw_schema_version=?,config_hash=?,finished_at=?,processing_duration=?,report_json=?,error_code=NULL WHERE sha256=?",(parser,cfg.raw_schema_version,config_hash,utc(),result['processing_time_seconds'],json.dumps(result,ensure_ascii=False),digest))
