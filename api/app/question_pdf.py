"""Printable PROVECTUS notebook. Data access remains in question_bank.py."""
from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (HRFlowable, Image, PageBreak, Paragraph,
                               SimpleDocTemplate, Spacer, Table, TableStyle)

INK = colors.HexColor('#202922')
OLIVE = colors.HexColor('#526638')
SAND = colors.HexColor('#C0AD83')
LIGHT = colors.HexColor('#F3F5EE')
RULE = colors.HexColor('#DCE2D5')
MUTED = colors.HexColor('#586254')
WIDTH = A4[0] - 92
SUBJECTS = dict(portugues='Português', matematica='Matemática', fisica='Física',
                quimica='Química', historia='História', ingles='Inglês',
                geografia='Geografia', biologia='Biologia')
DIFFICULTIES = dict(FACIL='Fácil', MEDIA='Média', DIFICIL='Difícil', MUITO_DIFICIL='Muito difícil')


class PDFContentError(ValueError):
    """An export must not silently omit a figure or substitute a formula."""


def fonts():
    folder = Path('/usr/share/fonts/truetype/dejavu')
    if not (folder / 'DejaVuSans.ttf').is_file():
        raise PDFContentError('Fonte DejaVu indisponível no servidor.')
    for name, file in [('PV', 'DejaVuSans.ttf'), ('PV-Bold', 'DejaVuSans-Bold.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(folder / file)))
    pdfmetrics.registerFontFamily('PV', normal='PV', bold='PV-Bold', italic='PV', boldItalic='PV-Bold')


def text_markup(value):
    # Source newlines (including verse) and indentation are deliberately retained.
    return escape(str(value or '')).replace('\t', '    ').replace('  ', '&#160; ').replace('\n', '<br/>')


class NotebookCanvas(Canvas):
    """Two passes for X/Y; page states retain their images and typography."""
    def __init__(self, *args, notebook_name='', **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages = []
        self.notebook_name = notebook_name

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self.decoration(total)
            super().showPage()
        super().save()

    def decoration(self, total):
        w, h = A4
        self.saveState()
        self.setFillColor(OLIVE)
        self.rect(46, h-42, 19, 3, fill=1, stroke=0)
        self.setFont('PV-Bold', 9)
        self.drawString(74, h-43, 'PROVECTUS')
        self.setFillColor(MUTED)
        self.setFont('PV', 7)
        self.drawRightString(w-46, h-43, 'BANCO DE QUESTÕES')
        self.setStrokeColor(RULE)
        self.line(46, h-54, w-46, h-54)
        self.line(46, 43, w-46, 43)
        # Paragraph wraps long names within the footer instead of overlapping X/Y.
        label = Paragraph(escape(self.notebook_name), ParagraphStyle(
            'Footer', fontName='PV', fontSize=6.5, leading=8, textColor=MUTED))
        _, height = label.wrap(WIDTH-110, 28)
        if height <= 28:
            label.drawOn(self, 46, 36-height)
        else:
            self.drawString(46, 27, 'PROVECTUS / Caderno de questões')
        self.drawRightString(w-46, 27, f'Página {self._pageNumber} de {total}')
        self.restoreState()


class ContentRenderer:
    def __init__(self, image_index, resolve, body):
        self.image_index, self.resolve, self.body = image_index, resolve, body
        self.paths = {}

    def image(self, digest):
        if digest not in self.image_index:
            raise PDFContentError(f'Imagem referenciada ausente: {digest}.')
        if digest not in self.paths:
            try:
                path = self.resolve(self.image_index[digest]['storage_path'])
                width, height = ImageReader(str(path)).getSize()
                self.paths[digest] = (str(path), width, height)
            except Exception as exc:
                raise PDFContentError(f'Imagem indisponível ou inválida: {digest}.') from exc
        return self.paths[digest]

    def block(self, digest, width):
        path, iw, ih = self.image(digest)
        scale = min(1, width/iw, 350/ih)
        image = Image(path, width=iw*scale, height=ih*scale)
        image.hAlign = 'CENTER'
        image.spaceBefore, image.spaceAfter = 5, 10
        return image

    def render(self, segments, fallback, assets, letter=None):
        style = self.body
        if letter:
            style = ParagraphStyle('Alternative', parent=style, leftIndent=25, firstLineIndent=-25, spaceAfter=9)
        width = WIDTH - (25 if letter else 0)
        result, parts, consumed = [], [], set()
        first = True

        def flush():
            nonlocal first, parts
            if not parts and not (first and letter):
                return
            prefix = f'<b>{escape(letter)})</b>   ' if first and letter else ''
            current_style = style if first else ParagraphStyle('Continuation', parent=style, firstLineIndent=0)
            paragraph = Paragraph(prefix + ''.join(parts), current_style)
            if not parts and letter:
                paragraph.keepWithNext = True
            result.append(paragraph)
            first, parts = False, []

        if not segments:
            if '[VISUAL]' in (fallback or ''):
                raise PDFContentError('Fórmula sem posição estruturada; revise o rich-content desta questão.')
            parts.append(text_markup(fallback))
        else:
            last_line = None
            for segment in segments:
                if segment.get('line_id') and last_line and segment['line_id'] != last_line and parts:
                    parts.append('<br/>')
                if segment.get('line_id'):
                    last_line = segment['line_id']
                if segment.get('kind') == 'visual':
                    digest = segment.get('asset_hash')
                    if not digest:
                        raise PDFContentError('Conteúdo visual sem referência de imagem.')
                    consumed.add(digest)
                    if segment.get('display') == 'inline':
                        path, iw, ih = self.image(digest)
                        bbox, size = segment.get('bbox'), segment.get('font_size')
                        ratio = min(4, max(.85, (bbox[3]-bbox[1])/size)) if bbox and size and size>0 else 1.35
                        height = style.fontSize * ratio
                        scale = min(height/ih, width/iw)
                        parts.append(f'<img src="{escape(path, quote=True)}" width="{iw*scale:.3f}" height="{ih*scale:.3f}" valign="middle"/>')
                    else:
                        flush()
                        result.append(self.block(digest, width))
                    continue
                content = text_markup(segment.get('text', ''))
                if segment.get('script') in ('sup', 'sub'):
                    tag = segment['script']; content = f'<{tag}>{content}</{tag}>'
                if segment.get('bold'):
                    content = f'<b>{content}</b>'
                parts.append(content)
        flush()
        for asset in assets:
            digest = asset['hash']
            if asset.get('type') != 'ORIGINAL_CROP' and digest not in consumed:
                result.append(self.block(digest, width))
                consumed.add(digest)
        return result


def build_notebook(name, questions, image_index, resolve, answer_placement='end'):
    if answer_placement not in ('end', 'after_each'):
        raise ValueError('Posição de gabarito inválida.')
    fonts()
    body = ParagraphStyle('Body', fontName='PV', fontSize=10.5, leading=16,
                          autoLeading='max', textColor=INK, spaceAfter=11,
                          allowWidows=0, allowOrphans=0)
    small = ParagraphStyle('Small', parent=body, fontSize=8, leading=12, textColor=MUTED)
    title = ParagraphStyle('Title', parent=body, fontName='PV-Bold', fontSize=21, leading=27, spaceAfter=12, keepWithNext=True)
    label = ParagraphStyle('Label', parent=small, fontName='PV-Bold', textColor=OLIVE, keepWithNext=True)
    renderer = ContentRenderer(image_index, resolve, body)
    story = [Paragraph('CADERNO DE QUESTÕES', label), Paragraph(text_markup(name), title)]
    subjects = list(dict.fromkeys(SUBJECTS.get((q.get('materia') or '').lower(), q.get('materia') or '') for q in questions))
    story.append(Paragraph(text_markup(f'{len(questions)} questões  •  '+ ' / '.join(s for s in subjects if s)), small))
    story.append(Paragraph('Gabarito após cada questão' if answer_placement=='after_each' else 'Gabarito somente ao final', small))
    story.extend([HRFlowable(width='100%', thickness=1, color=SAND), Spacer(1, 20)])
    answers = []
    for number, q in enumerate(questions, 1):
        # One shared ordinal for the question and its answer, even if DB ordinals have gaps.
        difficulty = q.get('dificuldade_normalizada') or 'Dificuldade não informada'
        meta = [q.get('banca_normalizada') or 'Banca não informada', DIFFICULTIES.get(difficulty, difficulty)]
        subject = SUBJECTS.get((q.get('materia') or '').lower(), q.get('materia') or '')
        path = q.get('content_path') or []
        hierarchy = ' › '.join(([subject] if subject else []) + path)
        heading = Table([[Paragraph(f'{number:02d}', ParagraphStyle('Number', parent=body, fontName='PV-Bold', fontSize=14, textColor=colors.white, alignment=TA_CENTER)),
                          Paragraph('<b>'+text_markup(' • '.join(meta))+'</b><br/>'+text_markup(hierarchy), small)]], colWidths=[39, WIDTH-39])
        heading.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),OLIVE),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                                    ('LINEBELOW',(1,0),(1,0),.6,RULE),('LEFTPADDING',(1,0),(1,0),12),
                                    ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        heading.keepWithNext = True
        heading.spaceAfter = 12
        story.append(heading)
        statement = renderer.render(q.get('statement_segments'), q.get('enunciado'), q.get('assets', []))
        # Keep the heading with a few lines, never with a whole multipage text.
        if statement and isinstance(statement[0], Paragraph):
            first = statement[0]
            _, height = first.wrap(WIDTH, 10000)
            if height > 96:
                fragments = first.split(WIDTH, 64)
                if len(fragments) > 1:
                    fragments[0].spaceAfter = 0
                    statement = fragments + statement[1:]
        story.extend(statement)
        for alt in q.get('alternatives', []):
            story.extend(renderer.render(alt.get('segments'), alt.get('text'), alt.get('assets', []), alt['letter']))
        answer = (q.get('gabarito') or '').strip() or 'Sem gabarito'
        answers.append((number, answer))
        if answer_placement == 'after_each':
            box = Table([[Paragraph('<b>GABARITO</b>', label), Paragraph(text_markup(answer), small)]], colWidths=[83, WIDTH-83])
            box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('LINEBEFORE',(0,0),(0,0),2,OLIVE),
                                    ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.append(box)
        if number < len(questions):
            story.extend([Spacer(1, 12), HRFlowable(width='100%', thickness=.4, color=RULE), Spacer(1, 20)])
    if answer_placement == 'end' and answers:
        story.extend([PageBreak(), Paragraph('CONFERÊNCIA / PROVECTUS', label), Paragraph('Gabarito', title), Paragraph(text_markup(name), small), Spacer(1, 8)])
        rows = []
        for offset in range(0, len(answers), 4):
            cells = [Paragraph(f'<b>{n:02d}</b>  —  {text_markup(answer)}', small) for n, answer in answers[offset:offset+4]]
            rows.append(cells+['']*(4-len(cells)))
        grid = Table(rows, colWidths=[WIDTH/4]*4)
        grid.setStyle(TableStyle([('ROWBACKGROUNDS',(0,0),(-1,-1),[LIGHT,colors.white]),('VALIGN',(0,0),(-1,-1),'TOP'),
                                 ('LINEBELOW',(0,0),(-1,-1),.4,RULE),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(grid)
    output = BytesIO()
    SimpleDocTemplate(output, pagesize=A4, leftMargin=46, rightMargin=46, topMargin=72, bottomMargin=61,
                      title=name, author='PROVECTUS', pageCompression=1).build(
        story, canvasmaker=lambda *args, **kwargs: NotebookCanvas(*args, notebook_name=name, **kwargs))
    output.seek(0)
    return output
