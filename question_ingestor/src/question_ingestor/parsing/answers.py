import re

def answer_marker(text,cfg):
    m=re.match(cfg.answer_pattern,text.strip())
    return m[1] if m else None
