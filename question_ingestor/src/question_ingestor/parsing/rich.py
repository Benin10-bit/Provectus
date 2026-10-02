"""Canonical scientific content, geometric line bands and traceable segments."""
from statistics import median
import hashlib
from ..validation.warnings import warn
from ..pdf.recovery import unicode_candidate


def bbox_union(boxes):
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]

def overlap_evidence(a,b,cfg):
    w=max(0,min(a[2],b[2])-max(a[0],b[0]));h=max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=w*h;denom=max((b[2]-b[0])*(b[3]-b[1]),1e-9)
    return {'intersection_width':w,'intersection_height':h,'intersection_area':area,'header_area_ratio':area/denom,'ratio_threshold':cfg.overlap_ratio_threshold,'edge_tolerance_pt':cfg.geometry_epsilon,'blocking':w>cfg.geometry_epsilon and h>cfg.geometry_epsilon and area/denom>=cfg.overlap_ratio_threshold}

def baseline(e):
    return median(s.get('origin',[0,e['bbox'][3]-2])[1] for s in e.get('spans',[])) if e.get('spans') else e['bbox'][3]-2

def vertical_overlap(a,b):
    return max(0,min(a[3],b[3])-max(a[1],b[1]))/max(min(a[3]-a[1],b[3]-b[1]),1e-9)

def order_elements(elements,cfg):
    result=[]
    for pn in sorted({e['page'] for e in elements}):
        es=[dict(e) for e in elements if e['page']==pn];bands=[]
        for e in sorted((e for e in es if e['kind']=='text'),key=lambda e:(baseline(e),e['bbox'][0])):
            match=next((b for b in bands if abs(b['baseline']-baseline(e))<=cfg.baseline_tolerance and vertical_overlap(e['bbox'],b['bbox'])>=cfg.inline_vertical_overlap),None)
            if match is None:
                match={'baseline':baseline(e),'bbox':e['bbox'].copy(),'items':[]};bands.append(match)
            match['items'].append(e);match['bbox']=bbox_union([match['bbox'],e['bbox']])
        blocks=[]
        for v in (e for e in es if e['kind']=='visual'):
            candidates=[];a=v['bbox']
            if v.get('role')!='table':
                for b in bands:
                    aligned=[t for t in b['items'] if vertical_overlap(a,t['bbox'])>=cfg.inline_vertical_overlap]
                    font=median(s.get('size',9) for t in b['items'] for s in t.get('spans',[])) if any(t.get('spans') for t in b['items']) else 9
                    gaplimit=font*cfg.horizontal_gap_em
                    left=[a[0]-t['bbox'][2] for t in aligned if -cfg.geometry_epsilon<=a[0]-t['bbox'][2]<=gaplimit]
                    right=[t['bbox'][0]-a[2] for t in aligned if -cfg.geometry_epsilon<=t['bbox'][0]-a[2]<=gaplimit]
                    if left or right:
                        candidates.append((int(bool(left))+int(bool(right)),-abs(a[3]-b['baseline']),b,{'vertical_overlap':vertical_overlap(a,b['bbox']),'left_gap':min(left) if left else None,'right_gap':min(right) if right else None,'baseline_distance':abs(a[3]-b['baseline']),'font_size':font}))
            candidates.sort(key=lambda c:(c[0],c[1]),reverse=True)
            if candidates:
                _,_,b,evidence=candidates[0]
                ambiguous=len(candidates)>1 and candidates[0][0]==candidates[1][0] and abs(candidates[0][1]-candidates[1][1])<=cfg.geometry_epsilon
                v.update(display='inline',layout_evidence={**evidence,'ambiguous':ambiguous},font_size=evidence['font_size']);b['items'].append(v)
            else:
                v.update(display='block',layout_evidence={'reason':'own line or no neighboring text baseline','ambiguous':False});blocks.append({'baseline':a[1],'bbox':a,'items':[v]})
        # Side-by-side figure panels share a bottom edge and read left-to-right.
        merged=[]
        for block in sorted(blocks,key=lambda b:b['bbox'][0]):
            target=next((row for row in merged if abs(row['bbox'][3]-block['bbox'][3])<=cfg.baseline_tolerance and 0<=block['bbox'][0]-row['bbox'][2]<=18),None)
            if target is None:merged.append(block)
            else:target['items']+=block['items'];target['bbox']=bbox_union([target['bbox'],block['bbox']])
        blocks=merged
        ordered=sorted(bands+blocks,key=lambda b:(b['bbox'][1] if b in blocks else min(e['bbox'][1] for e in b['items'] if e['kind']=='text'),b['bbox'][0]))
        for bi,b in enumerate(ordered):
            for e in sorted(b['items'],key=lambda e:e['bbox'][0]):
                e['line_id']=f'p{pn}:band{bi}';result.append(e)
    return result


def plain_text(segments):
    chunks=[];last=None
    for s in segments:
        if last is not None and (s['line_id']!=last or s.get('display')=='block'):chunks.append('\n')
        if s['kind']=='text':chunks.append(s['text'])
        else:chunks.append({'table':'[TABLE]','symbol':'[SYMBOL]','unresolved_symbol':'[UNRESOLVED_SYMBOL]'}.get(s.get('role'),'[VISUAL]'))
        last=s['line_id']
    return ''.join(chunks).strip()


def build_content(q,cfg):
    lines={(l['page'],l['id']):l for l in q['source_spans']}
    containers={None:[]};containers.update({a['letra']:[] for a in q['alternativas']})
    visuals=q.get('_visuals',[])
    embedded={(v['page'],id) for v in visuals for id in v.get('embedded_line_ids',[])}
    for c in q['content']:
        if c['kind']=='answer':continue
        owner=c.get('alternative');dest=containers[owner]
        base={'page':c['page'],'bbox':c['bbox'],'line_id':c.get('line_id',f"p{c['page']}:y{c['bbox'][1]}"),'source_line_id':c.get('source_line_id'),'document_sha256':q['document_sha256']}
        if c['kind']=='visual':
            v=visuals[c['visual_index']]
            dest.append({**base,'kind':'visual','display':v.get('display','block'),'role':v.get('role','unknown'),'visual_index':c['visual_index'],'layout_evidence':v.get('layout_evidence',{}),'font_size':v.get('font_size',9),'embedded_text':v.get('embedded_text'),'source_object_ids':v['objects']})
            if v.get('layout_evidence',{}).get('ambiguous'):warn(q,'CONTENT_ORDER_AMBIGUOUS','layout',page=c['page'],bbox=c['bbox'])
            continue
        if (c['page'],c.get('source_line_id')) in embedded:continue
        l=lines.get((c['page'],c.get('source_line_id')))
        if not l:
            if c.get('text'):dest.append({**base,'kind':'text','text':c['text']})
            continue
        prefix=c.get('prefix_length',0);offset=0
        for si,sp in enumerate(l['spans']):
            chars=sp.get('chars');st=sp['text'];skip=max(0,prefix-offset);offset+=len(st)
            if skip>=len(st):continue
            # PyMuPDF's TEXT_FONT_BOLD bit is native evidence from this exact span.
            # Keep styling separate from the plain-text projection.
            style={'script':'sup' if sp.get('flags',0)&1 else None,
                   'bold':bool(sp.get('flags',0)&16)}
            if not chars:
                dest.append({**base,'kind':'text','text':st[skip:],'bbox':sp['bbox'],'source_span_id':sp.get('id',f"{l['id']}s{si}"),'font_size':sp.get('size',9),**style});continue
            cs=chars[skip:];run=[];bad=None
            def emit(items,invalid):
                if not items:return
                box=bbox_union([x['bbox'] for x in items]);common={**base,'bbox':box,'source_span_id':sp.get('id'),'source_char_ids':[x['id'] for x in items],'font_size':sp.get('size',9),'baseline':sp.get('origin',[0,box[3]])[1]}
                if not invalid:dest.append({**common,'kind':'text','text':''.join(x['c'] for x in items),**style});return
                renderable=all(x.get('glyph_visible',False) for x in items)
                index=len(visuals);visuals.append({'page':c['page'],'bbox':box,'objects':[],'target':owner,'display':'inline','role':'symbol' if renderable else 'unresolved_symbol','glyph_renderable':renderable})
                dest.append({**common,'kind':'visual','display':'inline','role':'symbol' if renderable else 'unresolved_symbol','visual_index':index,'glyph_renderable':renderable,'glyph_ids':[x.get('glyph_id') for x in items],'source_object_ids':[]})
                candidate=unicode_candidate([x.get('raw_codepoint',ord(x['c'])) for x in items])
                if candidate:dest[-1]['recovery_candidate']=candidate
                if not renderable:warn(q,'UNRESOLVED_INVALID_GLYPH','statement' if owner is None else 'alternatives',page=c['page'],bbox=box,detail={'reason':'missing/.notdef glyph or unverified glyph geometry; crop is evidence, not a recovered symbol','glyph_ids':[x.get('glyph_id') for x in items]})
            for char in cs:
                invalid=char['c'] in ('\ufffd','\x00')
                if bad is not None and bad!=invalid:emit(run,bad);run=[]
                run.append(char);bad=invalid
            emit(run,bad)
    for owner,segs in containers.items():
        for i,s in enumerate(segs):
            s['order_index']=i;s['id']=hashlib.sha256(f"{q['extraction_id']}:{owner}:{i}".encode()).hexdigest()
        data={'segments':segs,'plain_text':plain_text(segs)}
        if owner is None:q['statement']=data;q['enunciado']=data['plain_text']
        else:
            a=next(a for a in q['alternativas'] if a['letra']==owner);a.update(data);a['texto']=''.join(s['text'] for s in segs if s['kind']=='text').strip() or None
    q['content_schema_version']=2
    q['metadata']['canonical_representation']='statement.segments and alternativas[].segments; text and asset lists are derived'
    q['content']=[{**s,'alternative':owner} for owner,segs in containers.items() for s in segs]
    return q
