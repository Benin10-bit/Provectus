"""Geometric event parser for the inspected single-column profile."""
import hashlib,re
from .headers import parse_header,is_header,header_typography
from .alternatives import alternative_marker
from .answers import answer_marker
from ..pdf.layout import graphical_regions
from ..validation.warnings import warn
from .rich import order_elements,overlap_evidence

def pos(item):
    y=(item['bbox'][1]+item['bbox'][3])/2 if item.get('kind')=='visual' else item['bbox'][1]
    return (item['page'],y,item['bbox'][0])

def detect_headers(pages,cfg):
    lines=[{**l,'page':p['page']} for p in pages for l in p['lines'] if l['text'].strip()]
    headers=[];consumed=set()
    for i,line in enumerate(lines):
        if not is_header(line,cfg):continue
        parts=[line];j=i+1
        while j<len(lines):
            nxt=lines[j]
            if (nxt['page']!=line['page'] or is_header(nxt,cfg) or not header_typography(nxt,cfg)
                or nxt['bbox'][1]-parts[-1]['bbox'][3]>cfg.header_wrap_gap
                or abs(nxt['bbox'][0]-line['bbox'][0])>cfg.header_x_tolerance):break
            parts.append(nxt);j+=1
        text=' '.join(p['text'] for p in parts)
        headers.append({'page':line['page'],'bbox':line['bbox'],'parts':parts,'text':text,'parsed':parse_header(text,cfg),'typography_ok':header_typography(line,cfg)})
        consumed.update((p['page'],p['id']) for p in parts)
    return headers,lines,consumed

def parse_questions(meta,pages,taxonomy,cfg):
    headers,lines,consumed=detect_headers(pages,cfg)
    events=[{**l,'kind':'text'} for l in lines if (l['page'],l['id']) not in consumed]
    for page in pages:
        events += [{**r,'page':page['page'],'kind':'visual','graphic_kind':r['kind']} for r in graphical_regions(page,cfg)]
    events.sort(key=pos);questions=[];orphans=[]
    for n,h in enumerate(headers):
        start=pos(h);end=pos(headers[n+1]) if n+1<len(headers) else (len(pages)+1,0,0)
        owned=[e for e in events if start<=pos(e)<end]
        q={'extraction_id':hashlib.sha256(f"{meta['document_sha256']}:{n+1}".encode()).hexdigest(),
           'source_ordinal':n+1,'document_sha256':meta['document_sha256'],'source_file':meta['source_file'],
           **taxonomy,**(h['parsed'] or {'numero_original':None,'header_original':h['text']}),
           'enunciado':'','alternativas':[],'gabarito':None,'imagens':[],'originals':[],
           'pagina_inicio':h['page'],'pagina_fim':max([h['page']]+[e['page'] for e in owned]),
           'warnings':[],'content':[],'source_spans':h['parts'].copy(),'source_regions':[],
           'metadata':{'profile':cfg.profile,'header_typography_ok':h['typography_ok'],'raw_schema_version':cfg.schema_version},
           '_visuals':[]}
        if not h['parsed']:warn(q,'HEADER_PARSE_FAILURE','header',page=h['page'],severity='ERROR')
        if not h['typography_ok']:warn(q,'UNEXPECTED_HEADER_LAYOUT','layout',page=h['page'])
        current=None;answered=False;answer_count=0
        for event in order_elements(owned,cfg):
            page=event['page'];box=event['bbox']
            if event['kind']=='visual':
                e={**event,'target':current['letra'] if current else None}
                if page==h['page']:
                    for part in h['parts']:
                        evidence=overlap_evidence(box,part['bbox'],cfg)
                        if evidence['blocking']:warn(q,'SOURCE_LAYOUT_OVERLAP','layout',page=page,bbox=box,detail=evidence)
                if page==end[0] and box[3]>end[1]+cfg.geometry_epsilon:warn(q,'POSSIBLE_UNASSOCIATED_IMAGE','images',page=page,bbox=box)
                if answered:warn(q,'CONTENT_AFTER_ANSWER','layout',page=page,bbox=box)
                q['_visuals'].append(e)
                q['content'].append({'kind':'visual','page':page,'bbox':box,'alternative':e['target'],'visual_index':len(q['_visuals'])-1,'line_id':event['line_id']})
                continue
            t=event['text'].strip();q['source_spans'].append(event)
            answer=answer_marker(t,cfg)
            if answer is not None:
                answer_count+=1;q['gabarito']=answer;answered=True
                q['content'].append({'kind':'answer','text':t,'page':page,'bbox':box});continue
            marker=alternative_marker(event,h['bbox'][0],cfg)
            if marker:
                letter,body=marker
                current={'letra':letter,'texto':body or None,'imagens':[],'source':{'page':page,'bbox':box}}
                q['alternativas'].append(current)
                q['content'].append({'kind':'alternative_marker','source_line_id':event['id'],'line_id':event['line_id'],'prefix_length':re.match(r'^\s*[A-Z]\)\s*',event['text']).end(),'text':body,'alternative':letter,'page':page,'bbox':box})
                continue
            if answered and t:warn(q,'CONTENT_AFTER_ANSWER','layout',page=page,bbox=box)
            if re.match(cfg.alternative_pattern,t) and not marker and not (current is None and re.match(r'^[IVXLCDM]+\)',t)):warn(q,'UNEXPECTED_ALTERNATIVE_LAYOUT','alternatives',page=page,bbox=box)
            if current:current['texto']=((current['texto']+'\n') if current['texto'] else '')+t
            else:q['enunciado']+=('\n' if q['enunciado'] else '')+t
            q['content'].append({'kind':'text','source_line_id':event['id'],'line_id':event['line_id'],'text':t,'alternative':current['letra'] if current else None,'page':page,'bbox':box})
        if answer_count>1:warn(q,'MULTIPLE_ANSWERS','answer')
        # Tight, ordered page crops, including header and all source elements.
        all_boxes=h['parts']+owned
        for pn in sorted({e['page'] for e in all_boxes}):
            boxes=[e['bbox'] for e in all_boxes if e['page']==pn]
            q['source_regions'].append({'page':pn,'bbox':[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]})
        questions.append(q)
    if headers:orphans=[e for e in events if pos(e)<pos(headers[0])]
    elif events:orphans=events
    return questions,orphans
