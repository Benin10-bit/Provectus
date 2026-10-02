import re

def parse_header(text,cfg):
    m=re.match(cfg.header_pattern,text)
    if not m:return None
    number,original,difficulty=m.groups()
    origin=re.search(r'\(([^()]*)\)\s*$',original)
    source=original[:origin.start()].strip() if origin else original
    institution=None;normalized=cfg.aliases.get(source)
    if ' - ' in source:
        long_name,short=source.rsplit(' - ',1)
        if re.fullmatch(r'[A-Z][A-Za-zÀ-ÿ0-9]{1,12}',short):
            institution=long_name;normalized=cfg.aliases.get(long_name,short)
    if normalized is None:normalized=source  # Preserve unknown source; never invent an abbreviation.
    return {'numero_original':int(number),'header_original':text,'banca_original':original,
        'banca_normalizada':normalized,'instituicao':institution,'tipo_origem':origin[1] if origin else None,
        'dificuldade_original':difficulty or None,'dificuldade_normalizada':cfg.difficulties.get(difficulty,difficulty or None)}

def is_header(line,cfg):
    return bool(re.match(cfg.header_start_pattern,line['text']))

def header_typography(line,cfg):
    return any(s['size']>=cfg.header_min_size and 'Bold' in s['font'] for s in line['spans'])
