"""Import automatic OK questions into the existing Provectus PostgreSQL server.

The SQLite staging and source assets are never modified. Each PDF is committed
as a unit; a failed job retains earlier committed PDFs and can be rolled back.
"""
from collections import Counter
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import sqlite3
import uuid

from ..pdf.extraction import sha256_file


def _open_staging(root):
    path = Path(root).resolve() / 'staging.db'
    if not path.is_file():
        raise FileNotFoundError(path)
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db


def _documents(db, document=None):
    where = "processing_status='DONE'"
    params = []
    if document:
        where += ' AND sha256=?'
        params.append(document)
    return db.execute(f'''SELECT sha256,source_file,relative_path,materia,
                                content_path,pages,metadata_json
                         FROM documents WHERE {where} ORDER BY sha256''', params)


def _limit_check(limit):
    if limit is not None and limit < 1:
        raise ValueError('--limit deve ser positivo')


def plan(root, document=None, limit=None):
    """Count the exact selection without loading question payloads into RAM."""
    db = _open_staging(root)
    try:
        _limit_check(limit)
        by_document = {}
        remaining = limit
        for doc in _documents(db, document):
            count = db.execute("SELECT count(*) FROM questions WHERE document_sha256=? AND status='OK'",
                               (doc['sha256'],)).fetchone()[0]
            selected = min(count, remaining) if remaining is not None else count
            if selected:
                by_document[doc['sha256']] = selected
                if remaining is not None:
                    remaining -= selected
                    if not remaining:
                        break
        return {'questions_ok_selected': sum(by_document.values()),
                'documents_selected': len(by_document),
                'questions_by_document': dict(by_document),
                'excluded_statuses': ['REVIEW', 'ERROR'],
                'database_modified': False}
    finally:
        db.close()


def _selected_rows(db, document=None, limit=None, overridden=None):
    _limit_check(limit)
    if overridden is None:
        overridden = {row[0] for row in db.execute('SELECT DISTINCT question_id FROM manual_overrides')}
    remaining = limit
    for doc in _documents(db, document):
        sql = "SELECT id,payload_json FROM questions WHERE document_sha256=? AND status='OK' ORDER BY id"
        params = [doc['sha256']]
        if remaining is not None:
            sql += ' LIMIT ?'
            params.append(remaining)
        for source in db.execute(sql, params):
            row = {**dict(doc), **dict(source)}
            q = json.loads(row['payload_json'])
            if q['status'] != 'OK' or q['document_sha256'] != row['sha256']:
                raise ValueError('STAGING_QUESTION_IDENTITY_INCONSISTENCY')
            if q['extraction_id'] != row['id']:
                raise ValueError('STAGING_QUESTION_ID_MISMATCH')
            if row['id'] in overridden:
                from ..review.overrides import effective
                revision = effective(db, row['id'])
                if revision['stale_overrides']:
                    raise ValueError('STALE_MANUAL_OVERRIDE')
                q = revision['effective']
            q.update(relative_path=row['relative_path'], materia=row['materia'],
                     content_path=json.loads(row['content_path'] or '[]'))
            yield row, q
            if remaining is not None:
                remaining -= 1
                if not remaining:
                    return


def _validate_question(q):
    options = q['alternativas']
    letters = [a['letra'] for a in options]
    if not q['enunciado'] or not options or len(letters) != len(set(letters)):
        raise ValueError('INVALID_OK_QUESTION_STRUCTURE')
    if q.get('gabarito') not in letters:
        raise ValueError('INVALID_OK_ANSWER')
    if q['pagina_inicio'] > q['pagina_fim']:
        raise ValueError('INVALID_OK_PAGE_RANGE')


def _assets(q):
    for a in q['imagens'] + q['originals']:
        yield None, a
    for option in q['alternativas']:
        for a in option['imagens']:
            yield option['letra'], a


def _verify_asset(root, a, verified):
    relative = PurePosixPath(a['path'])
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] != 'storage':
        raise ValueError('ASSET_PATH_OUTSIDE_STAGING')
    absolute = (root / relative).resolve()
    if not absolute.is_relative_to(root / 'storage'):
        raise ValueError('ASSET_PATH_OUTSIDE_STAGING')
    digest = a['hash']
    key = (digest, a['path'])
    if key in verified:
        return
    if not absolute.is_file() or absolute.stat().st_size != a['size_bytes'] or sha256_file(absolute) != digest:
        raise ValueError('ASSET_INTEGRITY_FAILURE')
    verified.add(key)


def _connect():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError('Instale question-ingestor[postgresql] para importar') from exc
    required = ('DB_USER', 'DB_PASSWORD', 'DB_NAME')
    if any(not os.getenv(key) for key in required):
        raise RuntimeError('Configure DB_USER, DB_PASSWORD e DB_NAME')
    return psycopg.connect(host=os.getenv('DB_HOST', 'db'), port=int(os.getenv('DB_PORT', '5432')),
                           user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
                           dbname=os.environ['DB_NAME'], autocommit=True)


def _require_schema(conn):
    if conn.execute("SELECT to_regclass('question_bank.questions')").fetchone()[0] is None:
        raise RuntimeError('QUESTION_BANK_SCHEMA_MISSING: execute a migration 004 na API primeiro')


def _insert_one(conn, row, q, job, root, verified):
    from psycopg.types.json import Jsonb
    _validate_question(q)
    payload_hash = hashlib.sha256(json.dumps(q, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':')).encode()).hexdigest()
    existing = conn.execute('SELECT source_payload_sha256 FROM question_bank.questions WHERE id=%s',
                            (q['extraction_id'],)).fetchone()
    if existing:
        if existing[0] != payload_hash:
            raise ValueError('EXISTING_QUESTION_CONTENT_CONFLICT')
        return False
    # Validate every unique referenced file before writing the question.
    assets = list(_assets(q))
    for _, asset in assets:
        _verify_asset(root, asset, verified)
    conn.execute('''INSERT INTO question_bank.documents
        (sha256,source_file,relative_path,materia,content_path,pages,metadata,first_import_job_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (sha256) DO NOTHING''',
        (row['sha256'], row['source_file'], row['relative_path'], row['materia'],
         Jsonb(json.loads(row['content_path'] or '[]')), row['pages'],
         Jsonb(json.loads(row['metadata_json'])), job))
    conn.execute('''INSERT INTO question_bank.questions
        (id,document_sha256,import_job_id,source_payload_sha256,automatic_status,
         numero_original,banca_original,banca_normalizada,tipo_origem,
         dificuldade_original,dificuldade_normalizada,enunciado,gabarito,
         pagina_inicio,pagina_fim,payload)
        VALUES (%s,%s,%s,%s,'OK',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (q['extraction_id'], row['sha256'], job, payload_hash, q['numero_original'],
         q.get('banca_original'), q.get('banca_normalizada'), q.get('tipo_origem'),
         q.get('dificuldade_original'), q.get('dificuldade_normalizada'),
         q['enunciado'], q['gabarito'], q['pagina_inicio'], q['pagina_fim'], Jsonb(q)))
    for i, alternative in enumerate(q['alternativas']):
        conn.execute('''INSERT INTO question_bank.alternatives
            (question_id,ordinal,letter,text,payload) VALUES (%s,%s,%s,%s,%s)''',
            (q['extraction_id'], i, alternative['letra'], alternative['texto'], Jsonb(alternative)))
    for i, (letter, a) in enumerate(assets):
        conn.execute('''INSERT INTO question_bank.assets
            (hash,storage_path,mime_type,width,height,size_bytes,first_import_job_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (hash) DO NOTHING''',
            (a['hash'], a['path'], a['mime_type'], a['width'], a['height'], a['size_bytes'], job))
        conn.execute('''INSERT INTO question_bank.question_assets
            (question_id,ordinal,asset_hash,type,alternative_letter,page,bbox,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
            (q['extraction_id'], i, a['hash'], a['type'], letter, a['page'],
             Jsonb(a['bbox']), Jsonb(a)))
    return True


def import_ok(root, document=None, limit=None):
    """Explicit write; commits per document and returns a rollbackable job ID."""
    root = Path(root).resolve()
    db = _open_staging(root)
    conn = None
    job = uuid.uuid4()
    job_created = False
    counts = Counter()
    verified = set()
    try:
        conn = _connect()
        _require_schema(conn)
        from psycopg.types.json import Jsonb
        with conn.transaction():
            conn.execute('INSERT INTO question_bank.import_jobs (id,status,scope) VALUES (%s,%s,%s)',
                         (job, 'PROCESSING', Jsonb({'document': document, 'limit': limit,
                                                   'selection': 'automatic OK from DONE documents'})))
        job_created = True
        print(f'import_job_id={job}', flush=True)
        remaining = limit
        overridden = {row[0] for row in db.execute('SELECT DISTINCT question_id FROM manual_overrides')}
        for doc in _documents(db, document):
            local = Counter()
            with conn.transaction():
                for row, q in _selected_rows(db, doc['sha256'], remaining, overridden):
                    local['imported' if _insert_one(conn, row, q, job, root, verified) else 'skipped'] += 1
                if local:
                    conn.execute('''UPDATE question_bank.import_jobs
                        SET imported_count=imported_count+%s, skipped_count=skipped_count+%s WHERE id=%s''',
                        (local['imported'], local['skipped'], job))
            if local:
                counts.update(local)
                print(f"document={doc['sha256'][:12]} imported={local['imported']} skipped={local['skipped']}",
                      flush=True)
                if remaining is not None:
                    remaining -= local.total()
                    if not remaining:
                        break
        with conn.transaction():
            conn.execute("UPDATE question_bank.import_jobs SET status='DONE',finished_at=now() WHERE id=%s", (job,))
        return {'job_id': str(job), 'status': 'DONE', **dict(counts)}
    except BaseException:
        if conn is not None and job_created:
            with conn.transaction():
                conn.execute('''UPDATE question_bank.import_jobs SET status='FAILED',finished_at=now(),
                    error_code=%s WHERE id=%s''', (type(exc).__name__, job))
        raise
    finally:
        db.close()
        if conn is not None:
            conn.close()


def rollback(job_id, apply=False):
    job = uuid.UUID(job_id)
    conn = _connect()
    try:
        _require_schema(conn)
        count = conn.execute('SELECT count(*) FROM question_bank.questions WHERE import_job_id=%s', (job,)).fetchone()[0]
        if not apply:
            return {'job_id': str(job), 'questions_to_delete': count, 'database_modified': False}
        with conn.transaction():
            status = conn.execute('SELECT status FROM question_bank.import_jobs WHERE id=%s FOR UPDATE', (job,)).fetchone()
            if not status or status[0] not in ('DONE', 'FAILED'):
                raise ValueError('IMPORT_JOB_NOT_ROLLBACKABLE')
            conn.execute('DELETE FROM question_bank.questions WHERE import_job_id=%s', (job,))
            conn.execute('''DELETE FROM question_bank.assets a WHERE a.first_import_job_id=%s
                AND NOT EXISTS (SELECT 1 FROM question_bank.question_assets qa WHERE qa.asset_hash=a.hash)''', (job,))
            conn.execute('''DELETE FROM question_bank.documents d WHERE d.first_import_job_id=%s
                AND NOT EXISTS (SELECT 1 FROM question_bank.questions q WHERE q.document_sha256=d.sha256)''', (job,))
            conn.execute("UPDATE question_bank.import_jobs SET status='ROLLED_BACK',finished_at=now() WHERE id=%s", (job,))
        return {'job_id': str(job), 'questions_deleted': count, 'status': 'ROLLED_BACK'}
    finally:
        conn.close()
