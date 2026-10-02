"""Small loopback-only-by-default HTTP review server, no external services."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse,parse_qs,unquote
import json,secrets,webbrowser,mimetypes
from ..batch.database import open_global
from ..batch.locking import output_lock
from .overrides import effective,change,approve,revert
from .html import render_segments

FILTERS={'REVIEW':"q.status='REVIEW'",'ERROR':"q.status='ERROR'",'MISSING_ANSWER':"json_extract(q.payload_json,'$.gabarito') IS NULL",'GLYPH':"EXISTS(SELECT 1 FROM warnings w WHERE w.question_id=q.id AND w.code LIKE '%GLYPH%')",'OVERLAP':"EXISTS(SELECT 1 FROM warnings w WHERE w.question_id=q.id AND w.code LIKE '%OVERLAP%')",'FORMULA':"EXISTS(SELECT 1 FROM warnings w WHERE w.question_id=q.id AND w.code='POSSIBLE_MISSING_FORMULA')",'CORRECTED':"r.human_status='CORRECTED'",'APPROVED':"r.human_status='APPROVED'"}

def listing(db,params):
    limit=max(1,min(50,int(params.get('limit','20'))));offset=max(0,int(params.get('offset','0')));where=["d.processing_status='DONE'"];values=[]
    selected=params.get('filter','REVIEW')
    if selected in FILTERS:where.append(FILTERS[selected])
    for param,column in [('materia','d.materia'),('document','d.sha256'),('content_path','d.content_path')]:
        if params.get(param):where.append(column+'=?');values.append(params[param])
    if params.get('number'):where.append('q.numero_original=?');values.append(int(params['number']))
    sql=' FROM questions q JOIN documents d ON d.sha256=q.document_sha256 LEFT JOIN review_state r ON r.question_id=q.id WHERE '+' AND '.join(where)
    total=db.execute('SELECT count(*)'+sql,values).fetchone()[0]
    rows=db.execute('SELECT q.id,q.numero_original,q.status,d.materia,d.content_path,d.relative_path,COALESCE(r.human_status,\'UNREVIEWED\')'+sql+' ORDER BY d.relative_path,q.numero_original,q.id LIMIT ? OFFSET ?',values+[limit,offset]).fetchall()
    return {'total':total,'offset':offset,'limit':limit,'items':[dict(zip(['id','number','automatic_status','materia','content_path','document','human_status'],r)) for r in rows]}

def make_server(out,host='127.0.0.1',port=8765):
    out=Path(out).resolve();token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,value,status=200):
            data=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            parsed=urlparse(self.path);p=parsed.path;params={k:v[0] for k,v in parse_qs(parsed.query).items()}
            try:
                if p=='/':
                    data=(Path(__file__).with_name('review.html')).read_text().replace('__TOKEN__',token).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(data);return
                if p.startswith('/storage/'):
                    target=(out/unquote(p).lstrip('/')).resolve()
                    if not target.is_relative_to(out/'storage') or not target.is_file() or target.suffix.lower() not in ['.webp','.png','.jpg']:self.send({'error':'Not found'},404);return
                    self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(target.name)[0] or 'application/octet-stream');self.end_headers()
                    with target.open('rb') as f:
                        while chunk:=f.read(65536):self.wfile.write(chunk)
                    return
                db=open_global(out/'staging.db')
                try:
                    if p=='/api/questions':data=listing(db,params)
                    elif p=='/api/options':
                        data={'documents':[{'id':r[0],'path':r[1],'materia':r[2],'content_path':r[3]} for r in db.execute("SELECT sha256,relative_path,materia,content_path FROM documents WHERE processing_status='DONE' ORDER BY relative_path")]}
                    elif p=='/api/question':
                        data=effective(db,params['id']);q=data['effective'];data['rendered_statement']=render_segments(q.get('statement',{}).get('segments',[]));data['rendered_alternatives']=[{'letter':a['letra'],'html':render_segments(a.get('segments',[]))} for a in q['alternativas']];data['history']=[dict(zip(['id','field','previous_value','new_value','created_at','note'],row)) for row in db.execute('SELECT id,field,previous_value,new_value,created_at,note FROM review_actions WHERE question_id=? ORDER BY id DESC LIMIT 100',(params['id'],))]
                    else:self.send({'error':'Not found'},404);return
                    self.send(data)
                finally:db.close()
            except (ValueError,KeyError) as exc:self.send({'error':str(exc)},400)
            except Exception:self.send({'error':'Internal error; inspect staging integrity'},500)
        def do_POST(self):
            if self.headers.get('X-Review-Token')!=token:self.send({'error':'Invalid local token'},403);return
            origin=self.headers.get('Origin')
            if origin and urlparse(origin).netloc!=self.headers.get('Host'):self.send({'error':'Cross-origin request rejected'},403);return
            db=None
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length>16*1024*1024:raise ValueError('Request too large; edit individual segments')
                data=json.loads(self.rfile.read(length));db=open_global(out/'staging.db');qid=data['id'];note=data.get('note','')
                if self.path=='/api/edit':result=change(db,qid,data['edits'],note,data.get('base_hash'))
                elif self.path=='/api/approve':result=approve(db,qid,note,data.get('base_hash'))
                elif self.path=='/api/revert':result=revert(db,qid,data['field'],note)
                else:self.send({'error':'Not found'},404);return
                self.send(result)
            except (ValueError,KeyError) as exc:self.send({'error':str(exc)},400)
            except Exception:self.send({'error':'Update failed; transaction rolled back'},500)
            finally:
                if db is not None:db.close()
    return ThreadingHTTPServer((host,port),Handler)

def serve(out,host='127.0.0.1',port=8765,open_browser=False):
    out=Path(out)
    if not (out/'staging.db').exists():raise ValueError('Batch staging.db not found')
    with output_lock(out):
        server=make_server(out,host,port);url=f'http://{host}:{server.server_port}'
        print(f'Review: {url} — Ctrl+C para encerrar. Não execute batch simultaneamente.',flush=True)
        if open_browser:webbrowser.open(url)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
