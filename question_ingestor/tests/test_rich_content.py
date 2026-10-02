import unittest,json,tempfile
from pathlib import Path
from question_ingestor.config import Config
try:
 from question_ingestor.parsing.rich import order_elements, build_content, overlap_evidence
except ModuleNotFoundError:
 from question_ingestor.parsing.questions import pos
 def order_elements(events,cfg):return sorted(events,key=pos)
 def build_content(q,cfg):return q
 def overlap_evidence(a,b,cfg):return {'blocking':a[1]<b[3]}
from question_ingestor.pdf.layout import graphical_regions
try:
 from question_ingestor.review.html import render_segments
except ImportError:
 def render_segments(segments):return 'legacy renderer has no segment API' 
from question_ingestor.validation.warnings import warn
from question_ingestor.validation.validators import validate
from test_pipeline import parsed,fixture,page,line,header,META,TAX

C=Config()
def text(t,b,id='l'):
 return {'kind':'text','text':t,'bbox':b,'page':1,'id':id,'spans':[{'text':t,'bbox':b,'font':'DejaVuSans','size':9,'origin':[b[0],b[3]-2],'flags':0}]}
def visual(b):return {'kind':'visual','page':1,'bbox':b,'objects':['im'],'graphic_kind':'raster'}

class RichRegression(unittest.TestCase):
 def test_inline_order_q13_geometry(self):
  events=[text('capacitância de ',[22,200,202,211],'left'),text('. Se o potencial',[260,200,550,211],'right'),visual([202,192,260,209])]
  result=order_elements(events,C);self.assertEqual([e['kind'] for e in result],['text','visual','text']);self.assertEqual(result[1]['display'],'inline')
 def test_small_graphic_is_block(self):
  r=order_elements([text('A)',[30,100,41,110]),visual([30,120,100,145])],C)
  self.assertEqual(r[1]['display'],'block')
 def test_table_zero_height_lines_grouped(self):
  p=page(1,[line('Coluna 1',90,x=55),line('Coluna 2',90,x=145),line('10',120,x=55),line('20',120,x=145)])
  # Fixtures use tight bounds as in the PDF, not the generic wide text helper.
  for l in p['lines']:l['bbox'][2]=l['bbox'][0]+55
  p['drawings']=[{'id':f'd{i}','kind':'drawing','bbox':b} for i,b in enumerate([[50,110,130,110],[130,110,230,110],[50,140,130,140],[130,140,230,140]])]
  r=graphical_regions(p,C);self.assertEqual(len(r),1);self.assertEqual(r[0]['role'],'table');self.assertEqual(len(r[0]['objects']),4)
 def test_false_overlap_q27(self):
  self.assertFalse(overlap_evidence([377,217.26,466,248],[22,203.63,520,217.6],C)['blocking'])
 def test_true_overlap(self):
  self.assertTrue(overlap_evidence([22,197,511,360],[22,209,548,223],C)['blocking'])
 def test_roman_sequence_is_statement(self):
  p=fixture();p[0]['lines'][2:2]=[line('I) primeira afirmativa',170),line('II) segunda afirmativa',190),line('III) terceira',210)]
  q=parsed(p);self.assertNotIn('UNEXPECTED_ALTERNATIVE_LAYOUT',[w['code'] for w in q['warnings']]);self.assertIn('I)',q['enunciado'])
 def test_native_superscript_not_missing_formula(self):
  p=fixture();p[0]['lines'][1]['text']='Capacitância de 10⁻⁶ F.';p[0]['lines'][1]['spans'][0]['flags']=1
  q=parsed(p);self.assertNotIn('POSSIBLE_MISSING_FORMULA',[w['code'] for w in q['warnings']])
 def test_graphical_option_and_info(self):
  q=parsed();q['alternativas'][0]['texto']=None;q['alternativas'][0]['imagens']=[{'hash':'x'}]
  warn(q,'GRAPHICAL_ALTERNATIVE','alternatives',severity='INFO');validate(q,None,C);self.assertEqual(q['status'],'OK')
 def test_html_inline(self):
  out=render_segments([{'kind':'text','text':'Antes ','line_id':'l'},{'kind':'visual','display':'inline','asset_path':'a.webp','bbox':[0,0,20,10],'line_id':'l','font_size':9},{'kind':'text','text':' depois','line_id':'l'}])
  self.assertLess(out.index('Antes'),out.index('a.webp'));self.assertLess(out.index('a.webp'),out.index('depois'));self.assertIn('inline-visual',out)
 def test_rich_content_exists(self):
  q=parsed();build_content(q,C);self.assertTrue(q['statement']['segments']);self.assertEqual(q['statement']['plain_text'],q['enunciado'])

if __name__=='__main__':unittest.main()

class RichIntegrity(unittest.TestCase):
 def test_native_bold_survives_pdf_to_render(self):
  import pymupdf as fitz
  from question_ingestor.pdf.extraction import raw_extract
  from question_ingestor.parsing.questions import parse_questions
  with tempfile.TemporaryDirectory() as t:
   pdf=Path(t)/'bold.pdf';doc=fitz.open();p=doc.new_page()
   p.insert_text((30,90),'Questão 1 - EEAr (Simulados) - Dificuldade: Fácil',fontsize=12,fontname='hebo')
   p.insert_text((30,120),'Assinale a palavra ',fontsize=10,fontname='helv')
   p.insert_text((123,120),'NÃO',fontsize=10,fontname='hebo')
   p.insert_text((148,120),' correta.',fontsize=10,fontname='helv')
   p.insert_text((37.5,160),'A) opção ',fontsize=10,fontname='helv')
   p.insert_text((80.5,160),'errada',fontsize=10,fontname='hebo')
   p.insert_text((37.5,180),'B) outra',fontsize=10,fontname='helv')
   p.insert_text((30,200),'Gabarito: B',fontsize=10,fontname='helv')
   doc.save(pdf);doc.close()
   meta,pages,source=raw_extract(pdf,Path(t)/'raw',C);source.close()
   self.assertTrue(any(s['flags']&16 and s['text']=='NÃO' for l in pages[0]['lines'] for s in l['spans']))
   q=parse_questions(meta,pages,TAX,C)[0][0];build_content(q,C)
   segments=q['statement']['segments'];bold=[s for s in segments if s['kind']=='text' and s['bold']]
   self.assertEqual([s['text'] for s in bold],['NÃO'])
   self.assertIn('NÃO',q['enunciado']);self.assertNotIn('<strong>',q['enunciado'])
   self.assertIn('<strong>NÃO</strong>',render_segments(segments))
   self.assertIn('<strong>errada</strong>',render_segments(q['alternativas'][0]['segments']))
   self.assertFalse(any(s.get('bold') for s in segments if s['kind']=='text' and s['text'].startswith('Assinale')))
   from question_ingestor.pipeline import ingest
   from question_ingestor.staging.database import connect,load_segments
   out=Path(t)/'out';ingest(pdf,out,TAX)
   saved=json.loads((out/'data/staging/questions.jsonl').read_text().splitlines()[0])
   self.assertEqual(saved['status'],'OK')
   self.assertIn('<strong>NÃO</strong>',(out/'audit.html').read_text())
   with connect(out/'data/staging/staging.db') as db:
    stored=load_segments(db,saved['extraction_id'])
   self.assertEqual([s['text'] for s in stored if s['kind']=='text' and s.get('bold')],['NÃO'])

 def test_unresolved_glyph_stays_review(self):
  q=parsed();l=q['source_spans'][1];sp=l['spans'][0];sp['text']='X�F';sp['id']='span';sp['chars']=[{'c':c,'id':str(i),'bbox':[i*5,118,i*5+5,127],'glyph_visible':False,'glyph_id':0} for i,c in enumerate(sp['text'])]
  build_content(q,C);validate(q,None,C)
  self.assertEqual(q['status'],'REVIEW');self.assertTrue(any(s.get('role')=='unresolved_symbol' for s in q['statement']['segments']))
 def test_ordered_visual_plain_has_placeholder(self):
  from question_ingestor.parsing.rich import plain_text
  segs=[{'kind':'text','text':'de ','line_id':'l'},{'kind':'visual','display':'inline','line_id':'l'},{'kind':'text','text':'. Se','line_id':'l'}]
  self.assertEqual(plain_text(segs),'de [VISUAL]. Se')
 def test_source_missing_requires_evidence(self):
  q=parsed();q['gabarito']=None;validate(q,None,C)
  self.assertIn('PARSER_MISSING_ANSWER',[w['code'] for w in q['warnings']])
  q=parsed();q['gabarito']=None;q['metadata']['answer_absence_verified']={'evidence':'boundary.png'};validate(q,None,C)
  self.assertIn('SOURCE_MISSING_ANSWER',[w['code'] for w in q['warnings']]);self.assertEqual(q['status'],'REVIEW')
 def test_sqlite_canonical_roundtrip_and_raw_cache(self):
  from test_pipeline import Integration,TAX
  from question_ingestor.pipeline import ingest
  from question_ingestor.pdf.extraction import raw_extract
  from question_ingestor.staging.database import connect,load_segments
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pdf=root/'fixture.pdf';Integration().create_pdf(pdf);out=root/'out';ingest(pdf,out,TAX)
   q=json.loads((out/'data/staging/questions.jsonl').read_text().splitlines()[0]);db=connect(out/'data/staging/staging.db')
   self.assertEqual(load_segments(db,q['extraction_id']),q['statement']['segments'])
   for a in q['alternativas']:self.assertEqual(load_segments(db,q['extraction_id'],a['letra']),a['segments'])
   db.close();cfg=Config(horizontal_gap_em=3)
   meta,_,doc=raw_extract(pdf,out,cfg);self.assertTrue(meta['raw_cache_reused']);doc.close()
   meta,_,doc=raw_extract(pdf,out,Config(position_tolerance=3));self.assertFalse(meta['raw_cache_reused']);doc.close()
 def test_trailing_option_whitespace_does_not_drop_text(self):
  p=fixture();l=p[0]['lines'][2];l['text']='A) Texto  ';l['spans'][0]['text']=l['text'];q=parsed(p);build_content(q,C)
  self.assertEqual(q['alternativas'][0]['texto'],'Texto')

class RasterLineIsolation(unittest.TestCase):
 def test_adjacent_rasters_in_distinct_lines_do_not_merge(self):
  p=page(1,[]);p['objects']=[{'id':'top','kind':'raster','bbox':[291,432,450,459]},{'id':'bottom','kind':'raster','bbox':[298,460,321,487]}]
  r=graphical_regions(p,C);self.assertEqual(len(r),2)
