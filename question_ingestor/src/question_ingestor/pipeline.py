from pathlib import Path
import json,hashlib,time,traceback,datetime,os
from .config import Config
from .pdf.extraction import raw_extract,sha256_file,dump
from .pdf.inspection import inspect_pages
from .parsing.questions import parse_questions
from .parsing.rich import build_content
from .pdf.assets import extract_assets
from .validation.validators import validate
from .validation.confidence import confidence
from .validation.warnings import warn
from .staging.database import connect,persist,load_segments
from .review.html import generate
from .reporting.report import report

ENGINE_REVISION='fenix-batch-2-bold-spans'

class UnsupportedLayout(ValueError):pass

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def safe_trace(root,exc,document,page=None,question=None):
    # Exception messages/locals may contain private source text: record type + stack frames only.
    with (root/'technical.log').open('a') as f:
        f.write(json.dumps({'document':document,'page':page,'question':question,'exception_type':type(exc).__name__})+'\n')
        f.writelines(traceback.format_tb(exc.__traceback__))

def ingest(path,root,taxonomy,cfg=None,force=False):
    cfg=cfg or Config();path=Path(path);root=Path(root);root.mkdir(parents=True,exist_ok=True)
    if not path.is_file():raise ValueError('Pilot command requires exactly one PDF file')
    digest=sha256_file(path)
    existing=root/'report.json'
    if existing.exists() and json.loads(existing.read_text())['sha256']!=digest:raise ValueError('Use a distinct output directory for each pilot document')
    observations_path=root/'source_observations.json'
    observation_hash=sha256_file(observations_path) if observations_path.exists() else ''
    observations=json.loads(observations_path.read_text()) if observations_path.exists() else {}
    baseline_path=root/'baseline/questions.jsonl'
    baseline={}
    if baseline_path.exists():
        with baseline_path.open(encoding='utf8') as rows:
            baseline={q['extraction_id']:q for q in (json.loads(line) for line in rows)}
    config_hash=hashlib.sha256((cfg.fingerprint()+json.dumps(taxonomy,sort_keys=True)+ENGINE_REVISION+observation_hash).encode()).hexdigest()
    job_id=hashlib.sha256((digest+config_hash).encode()).hexdigest()
    db=connect(root/'data/staging/staging.db')
    manifest=root/'manifest.json'
    prior=db.execute('SELECT state FROM processing_jobs WHERE id=?',(job_id,)).fetchone()
    if not force and prior and prior[0]=='DONE' and manifest.exists():
        m=json.loads(manifest.read_text())
        expected_rows={}
        saved_jsonl=root/'data/staging/questions.jsonl'
        if saved_jsonl.exists():
            with saved_jsonl.open(encoding='utf8') as rows:
                expected_rows={q['extraction_id']:q for q in (json.loads(line) for line in rows)}
        db_rows={id:json.loads(payload) for id,payload in db.execute('SELECT id,payload_json FROM questions WHERE document_sha256=?',(digest,))}
        db_ok=db_rows==expected_rows and bool(db_rows) and db.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
        if db_ok:
            db_ok=all(load_segments(db,q['extraction_id'])==q.get('statement',{}).get('segments',[]) and all(load_segments(db,q['extraction_id'],a['letra'])==a.get('segments',[]) for a in q['alternativas']) for q in expected_rows.values())
        if db_ok and m['job_id']==job_id and all((root/rel).exists() and sha256_file(root/rel)==h for rel,h in m['files'].items()):
            db.close();return {**json.loads(existing.read_text()),'resumed_without_reprocessing':True}
    with db:
        db.execute('INSERT INTO processing_jobs(id,document_sha256,config_hash,state) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state',(job_id,digest,config_hash,'PENDING'))
        db.execute("UPDATE processing_jobs SET state='PROCESSING',started_at=?,finished_at=NULL,error_code=NULL WHERE id=?",(utc(),job_id))
    start=time.perf_counter();doc=None
    try:
        meta,pages,doc=raw_extract(path,root,cfg);inspect_pages(meta,pages,root)
        # Reuse only verified immutable regional assets from the same document/configuration.
        if prior and prior[0]=='DONE' and manifest.exists():
            cached_manifest=json.loads(manifest.read_text())
            cached_json=root/'data/staging/questions.jsonl'
            if cached_manifest.get('job_id')==job_id and cached_json.exists() and sha256_file(cached_json)==cached_manifest.get('files',{}).get('data/staging/questions.jsonl'):
                cache={}
                with cached_json.open(encoding='utf8') as stream:
                    for line in stream:
                        old=json.loads(line)
                        for a in old['imagens']+old['originals']+[a for opt in old['alternativas'] for a in opt['imagens']]:
                            ap=root/a['path']
                            if 'dpi' in a and a['document_sha256']==digest and ap.exists() and sha256_file(ap)==a['hash']:
                                cache[(a['type'],a['page'],tuple(a['bbox']),a['dpi'])]=a
                doc._verified_render_cache=cache
        # Attribute engine diagnostics to the actual source page, without logging source strings.
        page_diagnostics={}
        if 'OTHER_SOURCE_ENGINE_WARNING' in meta.get('source_engine_warnings',[]):
            import pymupdf as fitz
            for i,p in enumerate(doc):
                fitz.TOOLS.mupdf_warnings(reset=True);p.get_text();p.get_drawings()
                messages=[v for v in fitz.TOOLS.mupdf_warnings(reset=True).splitlines() if v and v!='invalid character in hex string' and not v.startswith('... repeated ')]
                if messages:page_diagnostics[i+1]=['SOURCE_EMPTY_CLOSEPATH' if v=='closepath with no current point' else 'OTHER_SOURCE_ENGINE_WARNING' for v in messages]
            if not page_diagnostics:page_diagnostics={pn:['UNLOCALIZED_SOURCE_DIAGNOSTIC'] for pn in range(1,len(pages)+1)}
        qs,orphans=parse_questions(meta,pages,taxonomy,cfg)
        if not qs:raise UnsupportedLayout('No question header detected; raw retained')
        if not any(q['alternativas'] for q in qs):raise UnsupportedLayout('No alternatives detected; raw retained')
        dump(root/meta['raw_directory']/'unassigned.json',orphans)
        previous=None
        for q in qs:
            try:
                build_content(q,cfg)
                extract_assets(q,doc,root,cfg,pages)
            except Exception as exc:
                safe_trace(root,exc,digest,q['pagina_inicio'],q.get('numero_original'))
                q.pop('_visuals',None);warn(q,'ASSET_EXTRACTION_FAILED','images',severity='ERROR')
            q['metadata']['verified_blank_pages']=[]
            for pn in range(q['pagina_inicio'],q['pagina_fim']+1):
                pd=pages[pn-1]
                if not pd['text'].strip():
                    if not pd['objects'] and not pd['drawings']:
                        q['metadata']['verified_blank_pages'].append(pn);warn(q,'BLANK_SOURCE_PAGE','layout',page=pn,severity='INFO')
                    else:
                        complete=bool(q['enunciado'] and q['alternativas'] and q['gabarito'] and q['imagens'])
                        warn(q,'VISUAL_CONTINUATION_PAGE' if complete else 'OCR_REQUIRED','layout',page=pn,severity='INFO' if complete else 'REVIEW')
                if pn in page_diagnostics:warn(q,'PDF_ENGINE_WARNING','layout',page=pn,detail={'source_diagnostics':page_diagnostics[pn]})
            if orphans:warn(q,'UNASSIGNED_DOCUMENT_CONTENT','layout',detail={'count':len(orphans)})
            if observations.get('document_sha256')==digest:
                evidence=observations.get('questions',{}).get(q['extraction_id'])
                if evidence and evidence.get('code')=='SOURCE_MISSING_ANSWER' and q['gabarito'] is None:q['metadata']['answer_absence_verified']=evidence
            for code in q.get('hierarchy_warnings',[]):warn(q,code,'hierarchy')
            validate(q,previous,cfg);confidence(q);
            old=baseline.get(q['extraction_id'])
            if old:q['metadata']['previous_status']=old['status'];q['metadata']['status_changed']=old['status']!=q['status']
            q['duplicate_status']=None;q['dedup_checked']=False
            previous=q.get('numero_original')
        out=root/'data/staging/questions.jsonl';tmp=out.with_suffix('.jsonl.tmp')
        with tmp.open('w',encoding='utf8') as stream:
            for q in qs:stream.write(json.dumps(q,ensure_ascii=False)+'\n')
            stream.flush();os.fsync(stream.fileno())
        with tmp.open(encoding='utf8') as stream:written=[json.loads(line)['extraction_id'] for line in stream]
        if written!=[q['extraction_id'] for q in qs]:raise RuntimeError('JSONL_WRITE_INTEGRITY_FAILURE')
        persist(db,meta,qs,job_id);tmp.replace(out)
        sample_size=generate(qs,root,cfg)
        result=report(meta,qs,time.perf_counter()-start,root,sample_size,orphans)
        files=[out,root/'report.json',root/'report.md',root/'audit.html',root/'review_sample.json',root/'inspection.json']+list((root/'storage').rglob('*.webp'))+list((root/'data/raw'/digest).rglob('*.json'))
        dump(manifest,{'job_id':job_id,'files':{str(f.relative_to(root)):sha256_file(f) for f in files}})
        with db:db.execute("UPDATE processing_jobs SET state='DONE',finished_at=? WHERE id=?",(utc(),job_id))
        return result
    except KeyboardInterrupt:
        with db:db.execute("UPDATE processing_jobs SET state='FAILED',finished_at=?,error_code='KeyboardInterrupt' WHERE id=?",(utc(),job_id))
        raise
    except Exception as exc:
        safe_trace(root,exc,digest)
        with db:db.execute("UPDATE processing_jobs SET state='FAILED',finished_at=?,error_code=? WHERE id=?",(utc(),type(exc).__name__,job_id))
        raise
    finally:
        if doc:doc.close()
        db.close()
