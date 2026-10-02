"""Sanitized raw extraction. No arbitrary PDF metadata or private margin strings persist."""
from abc import ABC, abstractmethod
from collections import defaultdict, Counter
from pathlib import Path
import hashlib, json, math
import pymupdf as fitz

class TextExtractionStrategy(ABC):
    @abstractmethod
    def extract(self, page): ...

class NativePdfTextStrategy(TextExtractionStrategy):
    def extract(self, page):
        return page.get_text('dict', flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)

class OCRStrategy(TextExtractionStrategy):
    def extract(self, page):
        raise NotImplementedError('OCR fallback requires an explicitly configured provider')

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def dump(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(path)

def lines_of(page):
    out=[]
    raw=page.get_text('rawdict',flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)
    bad=[]
    for bi,b in enumerate(raw['blocks']):
        if b['type']!=0:continue
        for li,l in enumerate(b['lines']):
            spans=[]
            for si,s in enumerate(l['spans']):
                s=dict(s);s['id']=f'b{bi}l{li}s{si}'
                for ci,c in enumerate(s['chars']):
                    c['id']=f"{s['id']}c{ci}"
                    cp=ord(c['c'])
                    if cp in (0,65533) or 0xD800<=cp<=0xDFFF:
                        c['raw_codepoint']=cp;c['c']='\ufffd';bad.append((s,c))
                s['text']=''.join(c['c'] for c in s['chars']);spans.append(s)
            out.append({'id':f'b{bi}l{li}','bbox':list(l['bbox']),'dir':list(l['dir']),
                'text':''.join(s['text'] for s in spans),'spans':spans})
    if bad:
        trace=page.get_texttrace()
        for span,char in bad:
            matches=[(abs(c[2][0]-char['origin'][0])+abs(c[2][1]-char['origin'][1]),c[1],s['type']) for s in trace if s['font']==span['font'] for c in s['chars']]
            best=min(matches,default=(999,None,None))
            char['glyph_id']=best[1] if best[0]<=.5 else None
            char['glyph_visible']=best[2] in (0,1,2) and char['glyph_id'] not in (None,0)
    return out

def detect_repeated(doc,cfg):
    texts=defaultdict(set); images=defaultdict(set); occurrences=[]
    resource_xrefs={im[0] for p in doc for im in p.get_images(full=True)}
    resource_digests={xr:fitz.Pixmap(doc,xr).digest.hex() for xr in resource_xrefs}
    doc._resource_digests=resource_digests
    for n,p in enumerate(doc):
        ls=lines_of(p); ims=p.get_image_info(hashes=True)
        by_digest={}
        for item in p.get_images(full=True):by_digest.setdefault(resource_digests[item[0]],item[0])
        for im in ims:im['xref']=by_digest.get(im['digest'].hex(),0)
        def pos(box):return tuple(round(v/cfg.position_tolerance) for v in box)
        tk=[(l['text'],pos(l['bbox'])) for l in ls]
        ik=[(im['digest'].hex(),pos(im['bbox'])) for im in ims]
        for k,l in zip(tk,ls):
            # Only recurring margin text is eligible for automatic removal.
            if l['bbox'][3]<p.rect.height*cfg.margin_ratio or l['bbox'][1]>p.rect.height*(1-cfg.margin_ratio):texts[k].add(n)
        for k in ik:images[k].add(n)
        occurrences.append((ls,ims,tk,ik))
    minimum=max(cfg.min_recurrence_pages,math.ceil(len(doc)*cfg.recurrence_ratio))
    removed_text={k for k,v in texts.items() if len(v)>=minimum}
    removed_images={k for k,v in images.items() if len(v)>=minimum}
    return occurrences,removed_text,removed_images

def repair_font_system_info(doc):
    """Repair only unreadable auxiliary CIDSystemInfo dictionaries, never glyph mappings."""
    broken=[];references={};known=set()
    for xr in range(1,doc.xref_length()):
        try:doc.xref_object(xr)
        except RuntimeError:broken.append(xr);continue
        if doc.xref_get_key(xr,'Subtype')[1]=='/CIDFontType2':
            kind,value=doc.xref_get_key(xr,'CIDSystemInfo')
            if kind=='xref':references.setdefault(int(value.split()[0]),[]).append(xr)
    if not broken:return []
    for xr in references:
        if xr not in broken:
            values=tuple(doc.xref_get_key(xr,k) for k in ['Registry','Ordering','Supplement'])
            known.add(values)
    expected=(('string','Adobe'),('string','UCS'),('int','0'))
    # Other, readable CID fonts in the same source may declare a different (or
    # misspelled) collection. They do not determine the broken font's mapping.
    # Require an intact canonical reference, and repair only the unreadable
    # auxiliary dictionaries exclusively owned by CIDFontType2 fonts.
    if expected not in known or any(x not in references for x in broken):raise RuntimeError('UNRECOVERABLE_SOURCE_OBJECT')
    # Every reference to a broken object must be the auxiliary font dictionary.
    import re
    for xr in broken:
        pattern=re.compile(r'(?<![0-9])'+str(xr)+r'\s+0\s+R\b')
        for other in range(1,doc.xref_length()):
            if other in broken:continue
            if pattern.search(doc.xref_object(other)) and other not in references[xr]:raise RuntimeError('UNSAFE_FONT_REPAIR_REFERENCE')
    before=[p.get_text() for p in doc]
    for xr in broken:doc.update_object(xr,'<< /Registry (Adobe) /Ordering (UCS) /Supplement 0 >>')
    if any(p.get_text()!=before[i] for i,p in enumerate(doc)):raise RuntimeError('FONT_REPAIR_TEXT_CHANGED')
    return [{'code':'SOURCE_FONT_SYSTEM_INFO_REPAIRED','xref':xr,'native_text_unchanged':True} for xr in broken]

def sanitized_copy(doc,xrefs,exclusions):
    if xrefs:
        mask=doc.get_new_xref()
        doc.update_object(mask,'<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceGray /BitsPerComponent 8 >>')
        doc.update_stream(mask,b'\x00')
        for xr in xrefs:
            doc.update_object(xr,f'<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceRGB /BitsPerComponent 8 /SMask {mask} 0 R >>')
            doc.update_stream(xr,b'\xff\xff\xff')
        data=doc.tobytes();doc.close();doc=fitz.open(stream=data,filetype='pdf')
    doc._privacy_exclusions={i+1:boxes for i,boxes in enumerate(exclusions)}
    return doc

def check_graphics(doc,pages):
    expected=Counter((o['pixel_digest'],tuple(o['bbox'])) for p in pages for o in p['objects'])
    actual=Counter((im['digest'].hex(),tuple(im['bbox'])) for p in doc for im in p.get_image_info(hashes=True) if not (im['width']==1 and im['height']==1))
    if expected!=actual:raise RuntimeError('SANITIZATION_GRAPHIC_INTEGRITY_FAILURE')

def raw_extract(path,root,cfg):
    digest=sha256_file(path); dest=root/'data/raw'/digest/f'v{cfg.raw_schema_version}'
    cached=dest/'document.json';doc=fitz.open(path)
    fitz.TOOLS.mupdf_display_errors(False)
    repairs=repair_font_system_info(doc)
    if cached.exists():
        meta=json.loads(cached.read_text())
        if meta.get('raw_config_hash')==cfg.raw_fingerprint() and len(meta.get('page_hashes',{}))==len(doc) and all((dest/rel).exists() and sha256_file(dest/rel)==h for rel,h in meta['page_hashes'].items()):
            pages=[json.loads((dest/f'pages/page_{i+1:04}.json').read_text()) for i in range(len(doc))]
            doc=sanitized_copy(doc,meta['sanitization_resource_xrefs'],[p['excluded_regions'] for p in pages])
            check_graphics(doc,pages);meta['raw_cache_reused']=True
            return meta,pages,doc
    fitz.TOOLS.mupdf_warnings(reset=True)
    occ,rt,ri=detect_repeated(doc,cfg)
    diagnostics=fitz.TOOLS.mupdf_warnings(reset=True);engine_types=[]
    if 'invalid character in hex string' in diagnostics:engine_types.append('SOURCE_INVALID_HEX_STRING')
    if any(l and l!='invalid character in hex string' and not l.startswith('... repeated ') for l in diagnostics.splitlines()):engine_types.append('OTHER_SOURCE_ENGINE_WARNING')
    original_drawings=[p.get_drawings() for p in doc]
    recurring_digests={key[0] for key in ri}
    xrefs={xr for xr,digest_value in doc._resource_digests.items() if digest_value in recurring_digests}
    exclusions=[[l['bbox'] for l,k in zip(ls,tk) if k in rt] for ls,ims,tk,ik in occ]
    pages=[]
    for i,(ls,ims,tk,ik) in enumerate(occ):
        kept=sorted([l for l,k in zip(ls,tk) if k not in rt],key=lambda l:(l['bbox'][1],l['bbox'][0]))
        objects=[{'id':f'image{j}','kind':'raster','bbox':list(im['bbox']),'width':im['width'],'height':im['height'],'xref':im['xref'],'pixel_digest':im['digest'].hex()} for j,(im,k) in enumerate(zip(ims,ik)) if k not in ri]
        drawings=[]
        for j,d in enumerate(original_drawings[i]):
            drawings.append({'id':f'drawing{j}','kind':'drawing','bbox':list(d['rect']),'type':d['type'],'items':json.loads(json.dumps(d['items'],default=lambda v:list(v) if hasattr(v,'__iter__') else str(v))),'width':d.get('width'),'fill':d.get('fill'),'color':d.get('color')})
        page={'page':i+1,'width':doc[i].rect.width,'height':doc[i].rect.height,'text':'\n'.join(l['text'] for l in kept),'lines':kept,'objects':objects,'drawings':drawings,'excluded_regions':exclusions[i],'excluded_image_count':sum(k in ri for k in ik)}
        pages.append(page);dump(dest/f'pages/page_{i+1:04}.json',page)
    doc=sanitized_copy(doc,xrefs,exclusions);check_graphics(doc,pages)
    meta={'document_sha256':digest,'source_file':Path(path).name,'pages':len(doc),'raw_config_hash':cfg.raw_fingerprint(),'schema_version':cfg.raw_schema_version,'profile':cfg.profile,'raw_sanitized':True,'raw_revision':4,'source_repairs':repairs,'raw_cache_reused':False,'raw_directory':str(dest.relative_to(root)),'source_engine_warnings':engine_types,'sanitization_raster_integrity_verified':True,'sanitization_resource_xrefs':sorted(xrefs),'page_hashes':{f'pages/page_{i+1:04}.json':sha256_file(dest/f'pages/page_{i+1:04}.json') for i in range(len(doc))},'excluded_text_occurrences':sum(len(x) for x in exclusions),'excluded_image_occurrences':sum(p['excluded_image_count'] for p in pages)}
    dump(cached,meta);return meta,pages,doc
