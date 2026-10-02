import argparse,json
from pathlib import Path
from .config import Config
from .pipeline import ingest
from .pdf.extraction import raw_extract
from .pdf.inspection import inspect_pages

def main():
    parser=argparse.ArgumentParser(description='Isolated pilot ingestion. One PDF; no production writes.')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ['inspect','ingest']:
        p=sub.add_parser(name);p.add_argument('pdf',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--config',type=Path)
        if name=='ingest':
            p.add_argument('--materia',required=True);p.add_argument('--assunto',required=True);p.add_argument('--subassunto',required=True);p.add_argument('--force',action='store_true')
    b=sub.add_parser('batch',help='Recursive sequential ingestion into global staging')
    b.add_argument('root',type=Path);b.add_argument('--out',type=Path,required=True);b.add_argument('--config',type=Path)
    for flag in ['dry-run','force','retry-failed']:b.add_argument('--'+flag,action='store_true')
    b.add_argument('--limit',type=int);b.add_argument('--materia');b.add_argument('--path-prefix')
    r=sub.add_parser('review',help='Local paginated staging review tool')
    r.add_argument('out',type=Path);r.add_argument('--host',default='127.0.0.1');r.add_argument('--port',type=int,default=8765);r.add_argument('--open-browser',action='store_true')
    imp=sub.add_parser('import-ok',help='Preview or explicitly import only automatic OK questions into PostgreSQL')
    imp.add_argument('out',type=Path);imp.add_argument('--document');imp.add_argument('--limit',type=int)
    imp.add_argument('--apply',action='store_true',help='Write to PostgreSQL; omitted means SQLite-only preview')
    undo=sub.add_parser('rollback-import',help='Preview or explicitly roll back one import job')
    undo.add_argument('job_id');undo.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if args.command in ('import-ok','rollback-import'):
        from .importing.postgres import plan,import_ok,rollback
        if args.command=='rollback-import':result=rollback(args.job_id,args.apply)
        elif args.apply:result=import_ok(args.out,args.document,args.limit)
        else:result=plan(args.out,args.document,args.limit)
        print(json.dumps(result,ensure_ascii=False));return
    if args.command=='review':
        from .review.server import serve
        serve(args.out,args.host,args.port,args.open_browser);return
    cfg=Config.load(args.config)
    if args.command=='batch':
        from .batch.runner import run_batch
        run_batch(args.root,args.out,cfg,args.dry_run,args.force,args.retry_failed,args.limit,args.materia,args.path_prefix);return
    if args.command=='inspect':
        meta,pages,doc=raw_extract(args.pdf,args.out,cfg)
        try:result=inspect_pages(meta,pages,args.out)
        finally:doc.close()
        print(json.dumps({k:result[k] for k in ['pages','native_question_markers','native_answer_markers','content_image_occurrences','drawings']},ensure_ascii=False))
    else:
        result=ingest(args.pdf,args.out,{k:getattr(args,k) for k in ['materia','assunto','subassunto']},cfg,args.force)
        print(json.dumps({k:result.get(k) for k in ['sha256','pages','questions_found','questions_ok','questions_review','questions_error','processing_time_seconds','resumed_without_reprocessing']},ensure_ascii=False))
