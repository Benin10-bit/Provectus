"""Small fixtures reproduce observed layout; unittest runner needs no extra packages."""
import unittest,tempfile,json,hashlib,sqlite3
from pathlib import Path
from io import BytesIO
from PIL import Image
import pymupdf as fitz
from question_ingestor.config import Config
from question_ingestor.parsing.headers import parse_header
from question_ingestor.parsing.questions import parse_questions
from question_ingestor.validation.validators import validate
from question_ingestor.validation.confidence import confidence
from question_ingestor.dedup.normalization import normalize
from question_ingestor.dedup.matcher import candidates
from question_ingestor.pipeline import ingest
from question_ingestor.pdf.extraction import raw_extract

CFG=Config()
META={'document_sha256':'a'*64,'source_file':'fixture.pdf'}
TAX={'materia':'Física','assunto':'Eletrodinâmica','subassunto':'Capacitores'}

def line(text,y,x=22.5,size=9,font='DejaVuSans',id=None):
    return {'id':id or str(y),'text':text,'bbox':[x,y,550,y+size], 'dir':[1,0], 'spans':[{'text':text,'font':font,'size':size,'flags':0,'bbox':[x,y,550,y+size]}]}

def page(n,lines,objects=None):return {'page':n,'width':595,'height':842,'lines':lines,'objects':objects or [],'drawings':[],'text':'\n'.join(l['text'] for l in lines)}

def header(n,y=94,text=None):return line(text or f'Questão {n} - EEAr (Simulados) - Dificuldade: Fácil',y,size=12,font='DejaVuSans-Bold')

def fixture():
    return [page(1,[header(1),line('Considere os capacitores do circuito a seguir.',118),line('A) Primeira opção',250,x=30),line('B) Segunda opção',280,x=30),line('Gabarito: B',310)])]

def parsed(pages=None):return parse_questions(META,pages or fixture(),TAX,CFG)[0][0]

class Headers(unittest.TestCase):
    def test_origin(self):
        h=parse_header('Questão 18 - EsPCEx (Simulados) - Dificuldade: Média',CFG)
        self.assertEqual((h['numero_original'],h['banca_normalizada'],h['tipo_origem'],h['dificuldade_normalizada']),(18,'EsPCEx','Simulados','MEDIA'))
    def test_institution(self):
        h=parse_header('Questão 9 - Instituto Tecnológico de Aeronáutica - ITA - Dificuldade: Muito Difícil',CFG)
        self.assertEqual(h['banca_normalizada'],'ITA');self.assertEqual(h['instituicao'],'Instituto Tecnológico de Aeronáutica')
    def test_unknown_preserved(self):
        h=parse_header('Questão 1 - CFS - Demais especialidades - Dificuldade: Nova',CFG)
        self.assertEqual(h['banca_normalizada'],'CFS - Demais especialidades');self.assertEqual(h['dificuldade_normalizada'],'Nova')
    def test_wrapped(self):
        p=fixture();p[0]['lines'][0]=header(1,text='Questão 1 - Instituto Tecnológico de Aeronáutica - ITA - Dificuldade: Muito');p[0]['lines'].insert(1,line('Difícil',110,size=12,font='DejaVuSans-Bold'));p[0]['lines'][2]['bbox'][1]=140
        q=parsed(p);self.assertEqual(q['dificuldade_normalizada'],'MUITO_DIFICIL');self.assertNotIn('Difícil',q['enunciado'])

class Parsing(unittest.TestCase):
    def test_alternatives_and_answer(self):
        q=parsed();self.assertEqual([a['letra'] for a in q['alternativas']],['A','B']);self.assertEqual(q['gabarito'],'B')
    def test_multiline_alternative(self):
        p=fixture();p[0]['lines'].insert(3,line('continuação',265,x=30));self.assertIn('continuação',parsed(p)['alternativas'][0]['texto'])
    def test_multipage(self):
        p=fixture();p.append(page(2,p[0]['lines'][2:]));p[0]['lines']=p[0]['lines'][:2];q=parsed(p)
        self.assertEqual((q['pagina_inicio'],q['pagina_fim']),(1,2));self.assertEqual(len(q['alternativas']),2)
    def test_header_only_page(self):
        p=fixture();p.append(page(2,p[0]['lines'][1:]));p[0]['lines']=p[0]['lines'][:1];self.assertEqual(parsed(p)['pagina_fim'],2)
    def test_graphical_option_assignment(self):
        p=fixture();p[0]['lines'][2]['text']='A)';p[0]['objects']=[{'id':'im1','kind':'raster','bbox':[30,262,100,277],'width':100,'height':20}]
        q=parsed(p);self.assertEqual(q['_visuals'][0]['target'],'A');self.assertIsNone(q['alternativas'][0]['texto'])
    def test_question_boundary(self):
        p=fixture();p[0]['lines'] += [header(2,340),line('Outro enunciado com capacitores.',370),line('A) Um',420,x=30),line('B) Dois',450,x=30),line('Gabarito: A',480)]
        qs,_=parse_questions(META,p,TAX,CFG);self.assertEqual(len(qs),2);self.assertEqual(qs[0]['gabarito'],'B');self.assertNotIn('Outro',qs[0]['enunciado'])
    def test_bad_header_retained(self):
        p=fixture();p[0]['lines'][0]['text']='Questão 1 - incompleto';q=parsed(p);self.assertIn('HEADER_PARSE_FAILURE',[w['code'] for w in q['warnings']])
    def test_image_crossing_boundary(self):
        p=fixture();p[0]['lines'].append(header(2,340));p[0]['objects']=[{'id':'im1','kind':'raster','bbox':[30,330,100,360]}]
        qs,_=parse_questions(META,p,TAX,CFG)
        self.assertIn('SOURCE_LAYOUT_OVERLAP',[w['code'] for w in qs[1]['warnings']])

class Validation(unittest.TestCase):
    def test_valid(self):
        q=parsed();validate(q,None,CFG);confidence(q);self.assertEqual(q['status'],'OK');self.assertEqual(q['confidence']['answer'],1)
    def test_missing_answer(self):
        q=parsed();q['gabarito']=None;validate(q,None,CFG);self.assertEqual(q['status'],'REVIEW')
    def test_unknown_answer(self):
        q=parsed();q['gabarito']='?';validate(q,None,CFG);self.assertIn('UNKNOWN_ANSWER',[w['code'] for w in q['warnings']])
    def test_answer_membership(self):
        q=parsed();q['gabarito']='E';validate(q,None,CFG);self.assertIn('ANSWER_NOT_IN_ALTERNATIVES',[w['code'] for w in q['warnings']])
    def test_duplicate_option(self):
        q=parsed();q['alternativas'].append(q['alternativas'][0]);validate(q,None,CFG);self.assertEqual(q['status'],'ERROR')
    def test_empty_option(self):
        q=parsed();q['alternativas'][0]['texto']=None;validate(q,None,CFG);self.assertIn('EMPTY_GRAPHICAL_ALTERNATIVE',[w['code'] for w in q['warnings']])
    def test_empty_statement_with_image_review(self):
        q=parsed();q['enunciado']='';q['imagens']=[{'hash':'x'}];validate(q,None,CFG);self.assertEqual(q['status'],'REVIEW')
    def test_missing_formula(self):
        q=parsed();q['enunciado']='Um capacitor tem capacitância de .';validate(q,None,CFG);self.assertIn('POSSIBLE_MISSING_FORMULA',[w['code'] for w in q['warnings']])
    def test_sequence(self):
        q=parsed();validate(q,4,CFG);self.assertIn('BROKEN_SEQUENCE',[w['code'] for w in q['warnings']])
    def test_dynamic_count(self):
        for n in [4,5,6]:
            q=parsed();q['alternativas']=[{'letra':chr(65+i),'texto':'ok','imagens':[]} for i in range(n)];validate(q,None,CFG);self.assertNotIn('UNEXPECTED_ALTERNATIVE_COUNT',[w['code'] for w in q['warnings']])

class Dedup(unittest.TestCase):
    def test_math_preserved(self):
        self.assertNotEqual(normalize('10⁻⁶'),normalize('10⁶'));self.assertNotEqual(normalize('-10 μF'),normalize('10 μF'));self.assertNotEqual(normalize('x²'),normalize('x2'))
    def test_whitespace(self):self.assertEqual(normalize('A\n B'),normalize('A B'))
    def test_candidates_never_confirm(self):
        a=parsed();b=parsed();b['extraction_id']='b';c=candidates([a,b]);self.assertEqual(c[0]['status'],'POSSIBLE_DUPLICATE')

class Integration(unittest.TestCase):
    def create_pdf(self,path):
        doc=fitz.open();im=Image.new('RGB',(80,60),'red');buf=BytesIO();im.save(buf,format='PNG');image_bytes=buf.getvalue()
        for n in range(3):
            p=doc.new_page(width=595,height=842)
            p.insert_text((72,25),'PRIVATE-OWNER-TEST',fontsize=8)
            p.insert_text((22.5,106),f'Questão {n+1} - EEAr - Dificuldade: Fácil',fontsize=12,fontname='hebo')
            p.insert_text((22.5,130),'Capacitores em serie conforme o circuito.',fontsize=9)
            p.insert_image(fitz.Rect(200,300,280,360),stream=image_bytes)
            p.insert_text((30,160),'A) Um',fontsize=9);p.insert_text((30,185),'B) Dois',fontsize=9);p.insert_text((22.5,210),'Gabarito: B',fontsize=9)
        doc.save(path);doc.close()
    def test_sanitization_and_idempotency(self):
        with tempfile.TemporaryDirectory() as t:
            t=Path(t);path=t/'sample.pdf';self.create_pdf(path);before=path.read_bytes();root=t/'out'
            _,_,clean=raw_extract(path,root,CFG)
            pixel=clean[0].get_pixmap(clip=fitz.Rect(210,310,220,320))
            self.assertTrue(all(v==255 for v in pixel.samples));clean.close()
            first=ingest(path,root,TAX);second=ingest(path,root,TAX)
            self.assertEqual(first['questions_found'],3);self.assertTrue(second['resumed_without_reprocessing']);self.assertEqual(path.read_bytes(),before)
            for p in (root/'data/raw').rglob('*.json'):self.assertNotIn('PRIVATE-OWNER-TEST',p.read_text())
            db=sqlite3.connect(root/'data/staging/staging.db');self.assertEqual(db.execute('select count(*) from questions').fetchone()[0],3);self.assertEqual(db.execute('pragma integrity_check').fetchone()[0],'ok');db.close()
            # Corrupted asset forces regeneration instead of falsely reporting a complete checkpoint.
            asset=next((root/'storage').rglob('*.webp'));asset.write_bytes(b'broken')
            third=ingest(path,root,TAX);self.assertNotIn('resumed_without_reprocessing',third)
            self.assertNotEqual(asset.read_bytes(),b'broken')
    def test_failed_job_trace_and_raw(self):
        with tempfile.TemporaryDirectory() as t:
            t=Path(t);p=t/'scan.pdf';doc=fitz.open();doc.new_page();doc.save(p);doc.close()
            with self.assertRaises(ValueError):ingest(p,t/'out',TAX)
            db=sqlite3.connect(t/'out/data/staging/staging.db');self.assertEqual(db.execute('select state from processing_jobs').fetchone()[0],'FAILED');db.close()
            self.assertTrue((t/'out/technical.log').exists());self.assertTrue(list((t/'out/data/raw').rglob('document.json')))

if __name__=='__main__':unittest.main()
