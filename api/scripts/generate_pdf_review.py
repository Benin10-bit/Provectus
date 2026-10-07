"""Generate the same Modernismo comparison and synthetic visual review cases.

Run from api/: python scripts/generate_pdf_review.py [--output DIRECTORY]
Uses the existing API dependencies; no production database is accessed.
"""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))
from app.question_pdf import build_notebook


def visual_cases(asset_dir):
    asset_dir.mkdir(parents=True, exist_ok=True)
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    index = {}

    def save(name, image):
        path = asset_dir / f'{name}.png'
        image.save(path)
        index[name] = {'storage_path': str(path)}

    formula = Image.new('RGB', (260, 65), 'white')
    ImageDraw.Draw(formula).text((5, 2), 'E = mc²', font=ImageFont.truetype(font, 46), fill='black')
    save('formula', formula)
    for name, points in {
        'grafico': [(0, 0), (1, 2), (2, 4), (3, 6)],
        'opcao_a': [(0, 0), (1, 2), (2, 4), (3, 6)],
        'opcao_b': [(0, 6), (1, 4), (2, 2), (3, 0)],
        'opcao_c': [(0, 3), (1, 3), (2, 3), (3, 3)],
        'opcao_d': [(0, 0), (1, 1), (2, 3), (3, 6)],
    }.items():
        image = Image.new('RGB', (700, 300), 'white')
        draw = ImageDraw.Draw(image)
        for n in range(4):
            x = 70+n*185
            draw.line((x, 35, x, 248), fill='#dddddd', width=1)
            draw.text((x-4, 255), str(n), font=ImageFont.truetype(font, 18), fill='black')
        for n in range(4):
            y = 248-n*65
            draw.line((70, y, 625, y), fill='#dddddd', width=1)
            draw.text((40, y-10), str(n*2), font=ImageFont.truetype(font, 18), fill='black')
        draw.line((70, 35, 70, 248, 625, 248), fill='black', width=2)
        draw.line([(70+x*185, 248-y*32.5) for x, y in points], fill='black', width=4)
        draw.text((640, 240), 't (s)', font=ImageFont.truetype(font, 18), fill='black')
        draw.text((12, 5), 's (m)', font=ImageFont.truetype(font, 18), fill='black')
        save(name, image)
    base = dict(materia='fisica', content_path=['fisica', 'mecanica', 'cinematica'],
                banca_normalizada='Exemplo de validação', dificuldade_normalizada='MEDIA', assets=[])
    questions = [
        dict(base, enunciado='Considere a relação E = mc² e o gráfico apresentado.',
             statement_segments=[
                 dict(kind='text', text='Considere a relação ', line_id='1'),
                 dict(kind='visual', display='inline', asset_hash='formula', line_id='1'),
                 dict(kind='text', text=' e o gráfico apresentado.', line_id='1'),
                 dict(kind='visual', display='block', asset_hash='grafico')],
             alternatives=[dict(letter='A', text='O deslocamento cresce linearmente com o tempo.', assets=[]),
                           dict(letter='B', text='O deslocamento permanece constante.', assets=[])], gabarito='A'),
        dict(base, enunciado='Selecione o gráfico de uma posição que cresce linearmente com o tempo.',
             alternatives=[dict(letter=letter, text=None, assets=[dict(hash=f'opcao_{letter.lower()}')])
                           for letter in 'ABCD'], gabarito='A'),
        dict(base, enunciado='Texto extenso para verificar continuação e integridade.\n'+
             '\n'.join(f'Linha {n:02d}: o conteúdo permanece completo durante a paginação.' for n in range(1, 81))+
             '\nFonte: material sintético de validação.\nhttps://exemplo.invalid/'+('referencia-muito-longa/'*12),
             alternatives=[dict(letter='A', text='FIM_DO_CONTEÚDO_PRESERVADO', assets=[]),
                           dict(letter='B', text='Outra alternativa de validação.', assets=[])], gabarito='A'),
    ]
    return questions, index


def generate(output):
    output.mkdir(parents=True, exist_ok=True)
    modernismo = json.loads((API/'tests/fixtures/pdf_modernismo.json').read_text())
    cases, index = visual_cases(output/'assets')
    outputs = [
        ('provectus-Modernismo-after.pdf', 'Modernismo', modernismo, {}, 'end'),
        ('provectus-Modernismo-after_each.pdf', 'Modernismo', modernismo, {}, 'after_each'),
        ('provectus-validacao-visual.pdf', 'Fórmulas, gráficos e textos longos', cases, index, 'after_each'),
    ]
    for filename, title, questions, images, mode in outputs:
        path = output/filename
        path.write_bytes(build_notebook(title, questions, images, lambda path: path, mode).getvalue())
        print(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=API.parent/'validacao_pdf/refatoracao')
    generate(parser.parse_args().output)
