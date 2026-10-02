import re

def alternative_marker(line,header_x,cfg):
    m=re.match(cfg.alternative_pattern,line['text'].strip())
    if not m:return None
    if abs(line['bbox'][0]-(header_x+cfg.alternative_indent))>cfg.alternative_x_tolerance:return None
    return m.groups()
