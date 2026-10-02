import unittest,tempfile,json,sqlite3,shutil
from pathlib import Path
from unittest.mock import patch
from test_pipeline import Integration
from question_ingestor.config import Config
from question_ingestor.batch.discovery import hierarchy,discover
from question_ingestor.batch.runner import run_batch
from question_ingestor.batch.database import open_global
from question_ingestor.review.overrides import effective,change,approve,revert
from question_ingestor.review.server import listing

C=Config()
class Hierarchy(unittest.TestCase):
 def test_root_subject(self):self.assertEqual(hierarchy('Física/Cinemática.pdf',C)['content_path'],['Cinemática'])
 def test_variable_depth(self):self.assertEqual(hierarchy('Física/Óptica/Geométrica/Espelhos.pdf',C)['content_path'],['Óptica','Geométrica','Espelhos'])
 def test_generic(self):
  self.assertEqual(hierarchy('Física/Capacitores/lista-questoes-123.pdf',C)['content_path'],['Capacitores'])
  self.assertEqual(hierarchy('Física/lista-questoes-123.pdf',C)['hierarchy_status'],'REVIEW')
 def test_adjacent_only(self):
  self.assertEqual(hierarchy('Física/A/B/A/a.pdf',C)['content_path'],['A','B','A'])
 def test_missing_materia(self):self.assertIn('MISSING_MATERIA',hierarchy('a.pdf',C)['hierarchy_warnings'])
 def test_discovery(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);(r/'Física').mkdir();(r/'.hidden').mkdir();(r/'out').mkdir()
   for p in ['Física/z.PDF','Física/a.pdf','Física/a.txt','.hidden/x.pdf','out/x.pdf']:(r/p).write_bytes(b'x')
   (r/'link.pdf').symlink_to(r/'Física/a.pdf')
   self.assertEqual([h['relative_path'] for h in discover(r,r/'out',C)],['Física/a.pdf','Física/z.PDF'])

class Batch(unittest.TestCase):
 def setup_tree(self,t):
  r=Path(t)/'PDFs';(r/'Física').mkdir(parents=True);Integration().create_pdf(r/'Física/A.pdf');return r,Path(t)/'out'
 def test_dry_run_limit_resume_force_duplicate_move(self):
  with tempfile.TemporaryDirectory() as t:
   r,out=self.setup_tree(t);shutil.copyfile(r/'Física/A.pdf',r/'Física/B.PDF')
   dry=run_batch(r,out,dry_run=True);self.assertEqual(dry['documents_found'],2);self.assertFalse((out/'staging.db').exists())
   first=run_batch(r,out);self.assertEqual(first['documents_done'],1);self.assertEqual(first['documents_skipped'],1)
   second=run_batch(r,out);self.assertEqual(second['documents_skipped'],2)
   forced=run_batch(r,out,force=True,limit=1);self.assertEqual(forced['run_states'].get('DONE'),1)
   db=open_global(out/'staging.db');self.assertEqual(db.execute('select count(*) from questions').fetchone()[0],3);db.close()
   (r/'Física/A.pdf').rename(r/'Física/C.pdf');(r/'Física/B.PDF').unlink();moved=run_batch(r,out);self.assertEqual(moved['documents_skipped'],1)
   db=open_global(out/'staging.db');self.assertEqual(db.execute('select relative_path from documents').fetchone()[0],'Física/C.pdf');db.close()
 def test_failed_continues_retry_and_document_changed(self):
  with tempfile.TemporaryDirectory() as t:
   r,out=self.setup_tree(t);(r/'Física/0bad.pdf').write_bytes(b'bad pdf')
   first=run_batch(r,out);self.assertEqual(first['documents_failed'],1);self.assertEqual(first['documents_done'],1)
   second=run_batch(r,out);self.assertEqual(second['run_states']['FAILED_NOT_RETRIED'],1)
   retry=run_batch(r,out,retry_failed=True);self.assertEqual(retry['run_states']['FAILED'],1)
   with (r/'Física/A.pdf').open('ab') as f:f.write(b'\n%new version')
   changed=run_batch(r,out);db=open_global(out/'staging.db');self.assertEqual(db.execute('select count(*) from documents').fetchone()[0],3);db.close()
 def test_limit_two(self):
  with tempfile.TemporaryDirectory() as t:
   r,out=self.setup_tree(t)
   for n in ['B','C']:(r/f'Física/{n}.pdf').write_bytes((r/'Física/A.pdf').read_bytes()+n.encode())
   result=run_batch(r,out,limit=2);self.assertEqual(sum(result['run_states'].values()),2)
 def test_interrupt_resume(self):
  with tempfile.TemporaryDirectory() as t:
   r,out=self.setup_tree(t)
   with patch('question_ingestor.batch.runner.ingest',side_effect=KeyboardInterrupt):result=run_batch(r,out)
   self.assertTrue(result['interrupted']);self.assertEqual(run_batch(r,out)['documents_done'],1)
 def test_atomic_failure(self):
  with tempfile.TemporaryDirectory() as t:
   r,out=self.setup_tree(t)
   import question_ingestor.batch.database as bd
   original=bd.persist
   def bad(db,*args,**kwargs):original(db,*args,**kwargs);raise RuntimeError('simulated failure before commit')
   with patch('question_ingestor.batch.database.persist',side_effect=bad):run_batch(r,out)
   db=open_global(out/'staging.db');self.assertEqual(db.execute('select count(*) from questions').fetchone()[0],0);db.close()
   self.assertEqual(run_batch(r,out,retry_failed=True)['documents_done'],1)
 def test_overrides_approval_revert_and_stale(self):
  with tempfile.TemporaryDirectory() as t:
   r,out=self.setup_tree(t);run_batch(r,out);db=open_global(out/'staging.db');qid=db.execute('select id from questions limit 1').fetchone()[0]
   original=effective(db,qid)['automatic'];data=change(db,qid,{'gabarito':'A'},'test');self.assertEqual(data['automatic']['gabarito'],'B');self.assertEqual(data['effective']['gabarito'],'A');self.assertEqual(data['human_status'],'CORRECTED')
   self.assertEqual(approve(db,qid)['human_status'],'APPROVED');self.assertEqual(revert(db,qid,'gabarito')['effective']['gabarito'],'B')
   self.assertEqual(db.execute('select count(*) from review_actions').fetchone()[0],3)
   change(db,qid,{'gabarito':'A'});original['gabarito']='A'
   with db:db.execute('update questions set payload_json=? where id=?',(json.dumps(original),qid))
   self.assertIn('gabarito',effective(db,qid)['stale_overrides']);self.assertEqual(listing(db,{'filter':'ALL','limit':'1'})['limit'],1);db.close()

class LongText(unittest.TestCase):
 def test_large_question_is_preserved_without_length_review(self):
  from test_pipeline import fixture,parsed
  from question_ingestor.parsing.rich import build_content
  from question_ingestor.validation.validators import validate
  p=fixture();text=('Um texto longo com números 10⁻⁶ e palavras preservadas.\n'*2500)
  p[0]['lines'][1]['text']=text;p[0]['lines'][1]['spans'][0]['text']=text
  q=parsed(p);build_content(q,C);validate(q,None,C)
  self.assertEqual(q['enunciado'],text.strip());self.assertEqual(q['status'],'OK');self.assertGreater(len(q['enunciado']),100000)

class ReviewHTTP(unittest.TestCase):
 def test_api_pagination_edit_and_revert(self):
  import threading,urllib.request,re
  from question_ingestor.review.server import make_server
  with tempfile.TemporaryDirectory() as t:
   r,out=Batch().setup_tree(t);run_batch(r,out);server=make_server(out,port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
   try:
    # The local review server must be reached directly even if the user's
    # machine has an HTTP proxy configured for urllib.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    html=opener.open(base).read().decode();match=re.search("const token='([^']+)'",html)
    self.assertIsNotNone(match,'The local review page did not contain its edit token')
    token=match.group(1)
    def get(path):return json.load(opener.open(base+path))
    first=get('/api/questions?filter=ALL&limit=1');self.assertEqual(len(first['items']),1);self.assertEqual(first['total'],3);qid=first['items'][0]['id']
    detail=get('/api/question?id='+qid);self.assertIn('rendered_statement',detail);self.assertTrue(detail['effective']['originals'])
    for route,payload in [('edit',{'edits':{'gabarito':'A'}}),('revert',{'field':'gabarito'})]:
     req=urllib.request.Request(base+'/api/'+route,data=json.dumps({'id':qid,**payload}).encode(),headers={'Content-Type':'application/json','X-Review-Token':token});data=json.load(opener.open(req))
    self.assertEqual(data['effective']['gabarito'],'B');self.assertEqual(get('/api/question?id='+qid)['automatic']['gabarito'],'B')
   finally:server.shutdown();server.server_close();thread.join()

class SourceRegression(unittest.TestCase):
 def test_global_staging_large_document_survives_close_and_reopen(self):
  from question_ingestor.batch.database import open_global
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'staging.db';db=open_global(path)
   self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0],'delete')
   with db:
    db.execute('INSERT INTO documents(sha256,source_file,pages,metadata_json) VALUES(?,?,?,?)',('a'*64,'fixture.pdf',1,'x'*6_000_000))
   db.close()
   reopened=open_global(path)
   try:
    self.assertEqual(reopened.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    self.assertEqual(reopened.execute('SELECT length(metadata_json) FROM documents').fetchone()[0],6_000_000)
   finally:reopened.close()
 def test_bibliography_is_not_missing_formula(self):
  from test_pipeline import parsed
  from question_ingestor.validation.validators import validate
  q=parsed();q['enunciado']='Fonte: VARNHAGEN, Francisco Adolfo de. História da Independência do Brasil.';validate(q,None,C)
  self.assertNotIn('POSSIBLE_MISSING_FORMULA',[w['code'] for w in q['warnings']])
 def test_visual_statement_not_short(self):
  from test_pipeline import parsed
  from question_ingestor.validation.validators import validate
  q=parsed();q['enunciado']='[VISUAL]';q['imagens']=[{'hash':'fixture'}];validate(q,None,C);self.assertEqual(q['status'],'OK')
 def test_font_auxiliary_repair_preserves_text(self):
  import pymupdf as f
  from question_ingestor.pdf.extraction import repair_font_system_info
  d=f.open();p=d.new_page();p.insert_text((30,50),'Academic content');self.assertEqual(repair_font_system_info(d),[]);d.close()
 def test_font_repair_allows_other_intact_source_variants(self):
  from question_ingestor.pdf.extraction import repair_font_system_info
  class Page:
   def get_text(self):return 'original question'
  class Document:
   def __init__(self,unsafe=False):
    self.objects={1:'<< /Subtype /CIDFontType2 /CIDSystemInfo 2 0 R >>',
                  2:None,
                  3:'<< /Subtype /CIDFontType2 /CIDSystemInfo 4 0 R >>',
                  4:'<< /Registry (Adobe) /Ordering (UCS) /Supplement 0 >>',
                  5:'<< /Subtype /CIDFontType2 /CIDSystemInfo 6 0 R >>',
                  6:'<< /Registry (Adobe) /Ordering (RCS) /Supplement 0 >>'}
    if unsafe:self.objects[7]='<< /Other 2 0 R >>'
   def xref_length(self):return max(self.objects)+1
   def xref_object(self,x):
    if self.objects[x] is None:raise RuntimeError('unreadable dictionary')
    return self.objects[x]
   def xref_get_key(self,x,key):
    import re
    obj=self.xref_object(x);value=re.search(r'/'+key+r'\s+(\d+\s+0\s+R|\([^)]*\)|/\w+|\d+)',obj)
    if not value:return ('null','null')
    val=value[1]
    return ('xref',val) if val.endswith('R') else ('string',val[1:-1]) if val.startswith('(') else ('name',val) if val.startswith('/') else ('int',val)
   def update_object(self,x,value):self.objects[x]=value
   def __iter__(self):return iter([Page()])
  d=Document();repairs=repair_font_system_info(d)
  self.assertEqual([r['xref'] for r in repairs],[2]);self.assertIn('Ordering (RCS)',d.objects[6])
  with self.assertRaisesRegex(RuntimeError,'UNSAFE_FONT_REPAIR_REFERENCE'):repair_font_system_info(Document(unsafe=True))

class FinalRegressions(unittest.TestCase):
 def test_blank_page_requires_evidence(self):
  from test_pipeline import parsed
  from question_ingestor.validation.validators import validate
  q=parsed();q['pagina_inicio']=1;q['pagina_fim']=3;q['source_regions']=[{'page':1},{'page':3}];q['metadata']['verified_blank_pages']=[2];validate(q,None,C)
  self.assertNotIn('MULTIPAGE_INCONSISTENCY',[w['code'] for w in q['warnings']])
  q['metadata']['verified_blank_pages']=[];validate(q,None,C);self.assertIn('MULTIPAGE_INCONSISTENCY',[w['code'] for w in q['warnings']])
 def test_unicode_line_separator_preserved_in_jsonl(self):
  value={'text':'antes\u2028depois\u2029fim'}
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'x.jsonl';p.write_text(json.dumps(value,ensure_ascii=False)+'\n',encoding='utf8')
   with p.open(encoding='utf8') as f:self.assertEqual([json.loads(line) for line in f],[value])
 def test_force_reuses_verified_regional_images(self):
  from question_ingestor.pipeline import ingest
  with tempfile.TemporaryDirectory() as t:
   pdf=Path(t)/'x.pdf';out=Path(t)/'out';Integration().create_pdf(pdf);meta={'materia':'F','assunto':'A','subassunto':'B'};first=ingest(pdf,out,meta)
   with patch('question_ingestor.pdf.rendering.Image.frombytes',side_effect=AssertionError('cache should avoid rerender')):second=ingest(pdf,out,meta,force=True)
   self.assertEqual(first['questions_error'],second['questions_error']);self.assertEqual(first['images_found'],second['images_found'])
