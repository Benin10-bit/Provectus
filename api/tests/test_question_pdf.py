from io import BytesIO

import pytest
from PIL import Image as PILImage
from pypdf import PdfReader
from reportlab.platypus import Paragraph
from app.question_pdf import build_notebook, PDFContentError, ContentRenderer, fonts, WIDTH
from reportlab.lib.styles import ParagraphStyle


def question(**changes):
    return dict(enunciado='Enunciado preservado.', materia='Física', content_path=['Mecânica'],
                banca_normalizada='EsPCEx', dificuldade_normalizada='MEDIA', gabarito='B',
                alternatives=[dict(letter='A',text='Primeira',assets=[]), dict(letter='B',text='Segunda',assets=[])],
                assets=[], **changes)


def read(mode, questions):
    return PdfReader(build_notebook('Lista de revisão',questions,{},lambda p:p,mode))


def test_answer_placement_numbering_missing_answer_and_page_totals():
    questions=[question(),question()]
    questions[0]['ordinal']=6
    questions[1]['gabarito']=None
    final=read('end',questions)
    assert len(final.pages)==2
    assert 'GABARITO' not in final.pages[0].extract_text()
    assert '01 — B' in final.pages[-1].extract_text()
    assert '02 — Sem gabarito' in final.pages[-1].extract_text()
    after=read('after_each',questions)
    assert len(after.pages)==1
    assert after.pages[0].extract_text().count('GABARITO')==2
    for reader in (final,after):
        for n,page in enumerate(reader.pages,1):
            assert f'Página {n} de {len(reader.pages)}' in page.extract_text()
            assert float(page.mediabox.width)==pytest.approx(595.2756,abs=.01)
            assert float(page.mediabox.height)==pytest.approx(841.8898,abs=.01)


def test_long_question_and_alternative_are_not_truncated():
    q=question()
    q['enunciado']='INÍCIO '+('Texto longo íntegro. '*2500)+' FIM_DO_ENUNCIADO'
    q['alternatives'][0]['text']='Alternativa extensa. '*1800+' FIM_DA_ALTERNATIVA'
    reader=read('end',[q,question()])
    text='\n'.join(p.extract_text() for p in reader.pages)
    assert text.count('íntegro.')==2500
    assert text.count('extensa.')==1800
    assert 'FIM_DO_ENUNCIADO' in text and 'FIM_DA_ALTERNATIVA' in text
    assert '02 — B' in text
    assert 'INÍCIO' in reader.pages[0].extract_text()
    assert len(reader.pages)>5


def test_inline_formula_is_in_paragraph_and_not_repeated(tmp_path):
    fonts()
    path=tmp_path/'formula.webp'
    PILImage.new('RGB',(60,20),'black').save(path)
    renderer=ContentRenderer({'formula':{'storage_path':str(path)}},lambda p:p,
                             ParagraphStyle('test',fontName='PV',fontSize=10,leading=16,autoLeading='max'))
    segments=[dict(kind='text',text='Antes ',line_id='1',bold=True),
              dict(kind='visual',asset_hash='formula',display='inline',line_id='1'),
              dict(kind='text',text=' depois.',line_id='1'),
              dict(kind='text',text='Segundo verso.',line_id='2')]
    flow=renderer.render(segments,'[VISUAL]',[dict(hash='formula'),dict(hash='audit',type='ORIGINAL_CROP')])
    assert len(flow)==1 and isinstance(flow[0],Paragraph)
    assert flow[0].text.index('Antes')<flow[0].text.index('<img')<flow[0].text.index('depois')
    assert '<b>Antes </b>' in flow[0].text and '<br/>Segundo verso.' in flow[0].text
    q=question();q['statement_segments']=segments
    pdf=build_notebook('Fórmulas',[q],{'formula':{'storage_path':str(path)}},lambda p:p)
    assert len(PdfReader(pdf).pages[0].images)==1


@pytest.mark.parametrize('mode',['end','after_each'])
def test_graphical_alternatives_and_multipage_figures(tmp_path,mode):
    path=tmp_path/'diagram.png';PILImage.new('RGB',(1500,2000),'white').save(path)
    index={'diagram':{'storage_path':str(path)}}
    q=question()
    q['alternatives']=[dict(letter=letter,text=None,assets=[dict(hash='diagram')]) for letter in 'ABCDE']
    reader=PdfReader(build_notebook('Figuras',[q],index,lambda p:p,mode))
    content='\n'.join(p.extract_text() for p in reader.pages)
    assert all(f'{letter})' in content for letter in 'ABCDE')
    assert len(reader.pages)>1
    assert all('indisponível' not in p.extract_text() for p in reader.pages)


def test_missing_image_and_legacy_formula_are_explicit_errors():
    q=question();q['statement_segments']=[dict(kind='visual',display='inline',asset_hash='missing')]
    with pytest.raises(PDFContentError,match='ausente'):read('end',[q])
    q=question();q['enunciado']='Antes [VISUAL] depois'
    with pytest.raises(PDFContentError,match='Fórmula sem posição'):read('end',[q])
