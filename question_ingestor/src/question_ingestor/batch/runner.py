from pathlib import Path
import os,json,time,uuid,shutil,gc,hashlib,logging
from dataclasses import asdict
from .discovery import discover
from .database import open_global,register,synchronize
from .locking import output_lock
from .report import global_report
from ..config import Config
from ..pipeline import ingest,utc,safe_trace,ENGINE_REVISION
from ..pdf.extraction import sha256_file,dump
from ..validation.warnings import warn


def parser_fingerprint():
    # v0.2.3 only widens a guarded repair for PDFs that previously FAILED.
    # DONE documents cannot have used that branch successfully, so their
    # output remains compatible and should not be regenerated on a full run.
    # Bump this semantic fingerprint for any change to successful extraction.
    return 'fenix-batch-2-bold-spans:75f74dde2d63c9f4947bd2905c68ac98e82c57ee36da31865dbbdf8306236832'

def intact(docroot):
    try:
        manifest=json.loads((docroot/'manifest.json').read_text())
        return all((docroot/p).is_file() and sha256_file(docroot/p)==sha for p,sha in manifest['files'].items())
    except (OSError,ValueError,KeyError):return False

def share_assets(docroot,out,qs):
    assets={a['path']:a['hash'] for q in qs for a in q['imagens']+q['originals']+[i for opt in q['alternativas'] for i in opt['imagens']]}
    for rel,digest in assets.items():
        src=docroot/rel;dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists() or sha256_file(dst)!=digest:
            tmp=dst.with_suffix('.tmp');shutil.copyfile(src,tmp);tmp.replace(dst)
        if not os.path.samefile(src,dst):
            tmp=src.with_suffix('.linktmp')
            try:os.link(dst,tmp);tmp.replace(src)
            except OSError:
                if tmp.exists():tmp.unlink()  # on non-hardlink filesystems local audit keeps its own copy

def refresh_hierarchy(db,docroot,h,digest):
    """Rebind current paths without reading/interpreting the PDF again."""
    from ..staging.database import connect,persist
    from ..reporting.report import report
    from ..review.html import generate
    rows=db.execute('SELECT payload_json FROM questions WHERE document_sha256=? ORDER BY numero_original,id',(digest,)).fetchall()
    if not rows:return
    first=json.loads(rows[0][0])
    if all(first.get(k)==h.get(k) for k in ['relative_path','materia','content_path']):return
    cfg=Config();qs=[]
    for row in rows:
        q=json.loads(row[0]);q.update({k:h[k] for k in ['relative_path','materia','content_path','hierarchy_warnings']});q['source_file']=h['filename']
        q['assunto']=h['content_path'][0] if h['content_path'] else None;q['subassunto']=h['content_path'][1] if len(h['content_path'])>1 else None
        q['warnings']=[w for w in q['warnings'] if w['component']!='hierarchy']
        for code in h['hierarchy_warnings']:warn(q,code,'hierarchy')
        q['status']='ERROR' if any(w['severity']=='ERROR' for w in q['warnings']) else 'REVIEW' if any(w['severity']=='REVIEW' for w in q['warnings']) else 'OK'
        qs.append(q)
    manifest=json.loads((docroot/'manifest.json').read_text());meta=json.loads((docroot/'inspection.json').read_text());meta.update({k:h[k] for k in ['relative_path','materia','content_path']});meta['source_file']=h['filename']
    local=connect(docroot/'data/staging/staging.db')
    try:persist(local,meta,qs,manifest['job_id'])
    finally:local.close()
    path=docroot/'data/staging/questions.jsonl';tmp=path.with_suffix('.tmp');tmp.write_text(''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in qs));tmp.replace(path)
    old=json.loads((docroot/'report.json').read_text());sample=generate(qs,docroot,cfg);result=report(meta,qs,old['processing_time_seconds'],docroot,sample,[])
    with db:
        persist(db,meta,qs,manifest['job_id'],transaction=False)
        db.execute('UPDATE documents SET report_json=? WHERE sha256=?',(json.dumps(result,ensure_ascii=False),digest))
    for rel in manifest['files']:manifest['files'][rel]=sha256_file(docroot/rel)
    dump(docroot/'metadata.json',meta);dump(docroot/'manifest.json',manifest)

def run_batch(root,out,cfg=None,dry_run=False,force=False,retry_failed=False,limit=None,materia=None,path_prefix=None):
    cfg=cfg or Config();root=Path(root).resolve();out=Path(out).resolve()
    if limit is not None and limit<1:raise ValueError('--limit must be positive')
    found=discover(root,out,cfg,materia,path_prefix);selected=found[:limit] if limit else found
    out.mkdir(parents=True,exist_ok=True)
    with output_lock(out):
        dump(out/'hierarchy_report.json',{'root':str(root),'documents_found':len(found),'documents_selected':len(selected),'files':selected})
        if dry_run:
            for i,h in enumerate(selected,1):print(f"[{i}/{len(selected)}] {h['relative_path']} | {h['materia']} | {' > '.join(h['content_path'])} | {h['hierarchy_status']}")
            return {'dry_run':True,'documents_found':len(found),'documents_selected':len(selected)}
        db=open_global(out/'staging.db');job=uuid.uuid4().hex;start=time.perf_counter();parser=parser_fingerprint();cfg_hash=cfg.fingerprint();seen=set();interrupted=False
        (out/'logs').mkdir(exist_ok=True)
        with db:
            db.execute("UPDATE batch_jobs SET status='INTERRUPTED',finished_at=? WHERE status='PROCESSING'",(utc(),))
            db.execute('INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?)',(job,str(root),str(out),json.dumps(asdict(cfg),ensure_ascii=False),parser,utc(),None,'PROCESSING',None))
        current=None
        try:
            for index,h in enumerate(selected,1):
                tick=time.perf_counter();path=root/h['relative_path'];digest=None;current=h['relative_path']
                print(f"[{index}/{len(selected)}] {current}",flush=True)
                try:
                    digest=sha256_file(path);docroot=out/'documents'/digest
                    prior=db.execute('SELECT processing_status,parser_version,config_hash FROM documents WHERE sha256=?',(digest,)).fetchone()
                    # First deterministic path in this invocation is canonical; aliases always retained.
                    canonical=db.execute('SELECT relative_path,source_file,file_stem,materia,content_path FROM documents WHERE sha256=?',(digest,)).fetchone() if digest in seen else None
                    register(db,digest,h,path.stat().st_size,root,job,parser,cfg_hash,cfg.raw_schema_version,str(docroot.relative_to(out)))
                    if canonical:
                        with db:db.execute('UPDATE documents SET relative_path=?,source_file=?,file_stem=?,materia=?,content_path=? WHERE sha256=?',(*canonical,digest))
                    skip_duplicate=digest in seen;seen.add(digest)
                    with db:db.execute('INSERT INTO batch_items VALUES(?,?,?,?,?,?)',(job,current,digest,'PENDING',None,0))
                    if skip_duplicate or (not force and prior and prior[0]=='DONE' and prior[1:]==(parser,cfg_hash) and intact(docroot)):
                        if not skip_duplicate:refresh_hierarchy(db,docroot,h,digest)
                        with db:db.execute("UPDATE batch_items SET state='SKIPPED',duration=? WHERE job_id=? AND relative_path=?",(time.perf_counter()-tick,job,current))
                        print('SKIPPED',flush=True);continue
                    if prior and prior[0]=='FAILED' and not (retry_failed or force):
                        with db:db.execute("UPDATE batch_items SET state='FAILED_NOT_RETRIED' WHERE job_id=? AND relative_path=?",(job,current))
                        print('FAILED_NOT_RETRIED (use --retry-failed)',flush=True);continue
                    with db:
                        db.execute("UPDATE documents SET processing_status='PROCESSING',started_at=?,error_code=NULL WHERE sha256=?",(utc(),digest))
                        db.execute("UPDATE batch_items SET state='PROCESSING' WHERE job_id=? AND relative_path=?",(job,current))
                    taxonomy={k:h[k] for k in ['materia','content_path']};taxonomy.update(assunto=h['content_path'][0] if h['content_path'] else None,subassunto=h['content_path'][1] if len(h['content_path'])>1 else None,relative_path=current,hierarchy_warnings=h['hierarchy_warnings'])
                    # Same single-document pipeline; global state forces regeneration when parser/config changes.
                    result=ingest(path,docroot,taxonomy,cfg,force=force or bool(prior and prior[1:]!=(parser,cfg_hash)))
                    with (docroot/'data/staging/questions.jsonl').open(encoding='utf8') as rows:
                        qs=[json.loads(line) for line in rows]
                    meta=json.loads((docroot/'inspection.json').read_text());meta.update(taxonomy,document_id=digest,parser_version=parser)
                    share_assets(docroot,out,qs)
                    synchronize(db,docroot,meta,qs,result,job,parser,cfg_hash,cfg)
                    dump(docroot/'metadata.json',{**meta,'size_bytes':path.stat().st_size,'processing_status':'DONE','config_hash':cfg_hash})
                    with db:db.execute("UPDATE batch_items SET state='DONE',duration=? WHERE job_id=? AND relative_path=?",(time.perf_counter()-tick,job,current))
                    print(f"pages={result['pages']} questions={result['questions_found']} ok={result['questions_ok']} review={result['questions_review']} error={result['questions_error']} duration={time.perf_counter()-tick:.2f}s DONE",flush=True)
                    del qs,meta;gc.collect()
                except KeyboardInterrupt:raise
                except Exception as exc:
                    safe_trace(out/'logs',exc,digest or current)
                    with db:
                        if digest:db.execute("UPDATE documents SET processing_status='FAILED',finished_at=?,error_code=? WHERE sha256=?",(utc(),type(exc).__name__,digest))
                        db.execute('INSERT INTO batch_items VALUES(?,?,?,?,?,?) ON CONFLICT(job_id,relative_path) DO UPDATE SET state=excluded.state,error_code=excluded.error_code,duration=excluded.duration',(job,current,digest,'FAILED',type(exc).__name__,time.perf_counter()-tick))
                    print(f'FAILED {type(exc).__name__}',flush=True)
                finally:
                    with (out/'logs/batch.log').open('a',encoding='utf8') as log:log.write(json.dumps({'job':job,'path':current,'sha256':digest,'duration':round(time.perf_counter()-tick,3)},ensure_ascii=False)+'\n')
        except KeyboardInterrupt:
            interrupted=True
            with db:
                db.execute("UPDATE documents SET processing_status='INTERRUPTED' WHERE processing_status='PROCESSING'")
                db.execute("UPDATE batch_items SET state='INTERRUPTED' WHERE job_id=? AND state='PROCESSING'",(job,))
            print('INTERRUPTED: execute o mesmo comando para continuar.',flush=True)
        finally:
            result=global_report(db,out,job,len(found),time.perf_counter()-start);result['interrupted']=interrupted
            with db:db.execute('UPDATE batch_jobs SET status=?,finished_at=?,summary_json=? WHERE id=?',('INTERRUPTED' if interrupted else 'DONE',utc(),json.dumps(result,ensure_ascii=False),job))
            dump(out/'batch_manifest.json',{'last_job':job,'parser_version':parser,'config_hash':cfg_hash,'summary':result})
            integrity=db.execute('PRAGMA quick_check').fetchone()[0]
            db.close()
            if integrity!='ok':raise RuntimeError('STAGING_INTEGRITY_FAILURE')
            verify=open_global(out/'staging.db')
            try:
                if verify.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                    raise RuntimeError('STAGING_REOPEN_INTEGRITY_FAILURE')
            finally:verify.close()
        print(f"BATCH {'INTERRUPTED' if interrupted else 'COMPLETE'} | DONE={result['documents_done']} FAILED={result['documents_failed']} SKIPPED={result['documents_skipped']} | questões={result.get('questions_found',0)} | {out/'reports/global.md'}",flush=True)
        return result
