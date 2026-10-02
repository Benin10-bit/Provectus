import re
from collections import Counter
from .warnings import warn

def validate(q,previous,cfg):
    letters=[a['letra'] for a in q['alternativas']]
    if not q['enunciado'].strip():warn(q,'MISSING_STATEMENT','statement',severity='ERROR' if not q['imagens'] else 'REVIEW')
    elif len(q['enunciado'].strip())<cfg.min_statement_chars and not q['imagens']:warn(q,'VERY_SHORT_STATEMENT','statement')
    if not letters:warn(q,'MISSING_ALTERNATIVES','alternatives',severity='ERROR')
    if not cfg.min_alternatives<=len(letters)<=cfg.max_alternatives:warn(q,'UNEXPECTED_ALTERNATIVE_COUNT','alternatives',detail={'count':len(letters)})
    if any(n>1 for n in Counter(letters).values()):warn(q,'DUPLICATED_ALTERNATIVE','alternatives',severity='ERROR')
    if letters and letters!=[chr(65+i) for i in range(len(letters))]:warn(q,'BROKEN_SEQUENCE','alternatives',detail={'letters':letters})
    if q['gabarito'] is None:warn(q,'SOURCE_MISSING_ANSWER' if q['metadata'].get('answer_absence_verified') else 'PARSER_MISSING_ANSWER','answer',detail=q['metadata'].get('answer_absence_verified',{'reason':'absence not yet checked against visual source'}))
    elif not re.fullmatch('[A-Z]',q['gabarito']):warn(q,'UNKNOWN_ANSWER','answer')
    elif q['gabarito'] not in letters:warn(q,'ANSWER_NOT_IN_ALTERNATIVES','answer')
    if not q.get('dificuldade_original'):warn(q,'MISSING_DIFFICULTY','header')
    if not q.get('banca_original'):warn(q,'MISSING_BANK','header')
    if previous is not None and q.get('numero_original')!=previous+1:warn(q,'BROKEN_SEQUENCE','header',detail={'previous':previous})
    for a in q['alternativas']:
        if not (a['texto'] or '').strip() and not a['imagens']:warn(q,'EMPTY_GRAPHICAL_ALTERNATIVE','alternatives',detail={'alternative':a['letra']})
    for component,text in [('statement',q['enunciado'])]+[('alternatives',a.get('plain_text',a['texto']) or '') for a in q['alternativas']]:
        if re.search(cfg.formula_gap_pattern,text,re.I):warn(q,'POSSIBLE_MISSING_FORMULA',component,detail={'reason':'syntactically empty mathematical slot'})
    pnums=[r['page'] for r in q['source_regions']]
    if sorted(set(pnums)|set(q['metadata'].get('verified_blank_pages',[])))!=list(range(q['pagina_inicio'],q['pagina_fim']+1)):warn(q,'MULTIPAGE_INCONSISTENCY','layout')
    if not q['gabarito'] and not letters:warn(q,'QUESTION_INTERRUPTED','layout')
    for l in q['source_spans']:
        if any(re.search(pattern,l['text'],re.I) for pattern in [r'\bCPF\s*:',r'DOCUMENTO CONFIDENCIAL']):warn(q,'FOOTER_CONTAMINATION','layout',severity='ERROR')
    q['status']='ERROR' if any(w['severity']=='ERROR' for w in q['warnings']) else 'REVIEW' if any(w['severity']=='REVIEW' for w in q['warnings']) else 'OK'
