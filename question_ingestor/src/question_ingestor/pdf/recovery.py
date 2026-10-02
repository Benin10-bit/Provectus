"""Conservative object isolation and explicitly unconfirmed Unicode candidates."""
import hashlib,unicodedata
from io import BytesIO
from pathlib import Path
import pymupdf as fitz
from PIL import Image


def intersects(a,b,epsilon=.75):
    return min(a[2],b[2])-max(a[0],b[0])>epsilon and min(a[3],b[3])-max(a[1],b[1])>epsilon


def isolate_raster(doc,page,visual,question,root,cfg):
    ids=visual.get('objects',[])
    candidates=[o for o in page['objects'] if o['id'] in ids]
    if len(ids)!=1 or len(candidates)!=1:return None
    obj=candidates[0];box=obj['bbox']
    if any(intersects(box,d['bbox'],0) for d in page['drawings']):return None
    # Native academic content crossing a raster must not be silently removed.
    if any(s['kind']=='text' and s['page']==page['page'] and intersects(box,s['bbox'],cfg.geometry_epsilon) for s in question['content']):return None
    info=next((i for i in doc[page['page']-1].get_image_info(hashes=True,xrefs=True) if i['xref']==obj['xref'] and all(abs(a-b)<cfg.geometry_epsilon for a,b in zip(i['bbox'],box))),None)
    if info is None or info['digest'].hex()!=obj['pixel_digest']:return None
    a,b,c,d,_,_=info['transform']
    if b or c or a<=0 or d<=0:return None  # rotated/mirrored placements need a dedicated strategy
    pix=fitz.Pixmap(doc,obj['xref']);smask=doc.extract_image(obj['xref']).get('smask',0)
    if smask:pix=fitz.Pixmap(pix,fitz.Pixmap(doc,smask))
    if pix.colorspace and pix.colorspace.n!=3:pix=fitz.Pixmap(fitz.csRGB,pix)
    im=Image.frombytes('RGBA' if pix.alpha else 'RGB',[pix.width,pix.height],pix.samples)
    buf=BytesIO();im.save(buf,format='WEBP',lossless=True,quality=cfg.webp_quality);data=buf.getvalue();digest=hashlib.sha256(data).hexdigest()
    path=Path('storage/questions')/digest[:2]/(digest+'.webp');(root/path).parent.mkdir(parents=True,exist_ok=True);(root/path).write_bytes(data)
    return {'hash':digest,'path':path.as_posix(),'mime_type':'image/webp','width':im.width,'height':im.height,'size_bytes':len(data),'type':'ALTERNATIVE_IMAGE' if visual['target'] else 'STATEMENT_IMAGE','page':page['page'],'bbox':box,'recovery':{'method':'isolated_source_raster','source_xref':obj['xref'],'pixel_digest_verified':True,'native_resolution_preserved':True,'source_document_unchanged':True}}


def unicode_candidate(raw_codepoints):
    """A lost high surrogate cannot be uniquely recovered. Never return verified text."""
    if not raw_codepoints or len(raw_codepoints)%2:return None
    chars=[]
    for hi,lo in zip(raw_codepoints[::2],raw_codepoints[1::2]):
        if hi!=0xD800 or not 0xDC00<=lo<=0xDFFF:return None
        cp=0x10000+(0xD835-0xD800)*1024+lo-0xDC00
        if not 0x1D400<=cp<=0x1D7FF or not unicodedata.name(chr(cp),'').startswith('MATHEMATICAL '):return None
        chars.append(chr(cp))
    return {'text':''.join(chars),'unicode_names':[unicodedata.name(c) for c in chars],'raw_codepoints':raw_codepoints,'assumed_high_surrogate':'D835','observed_high_surrogate':'D800','method':'mathematical_alphanumeric_block_hypothesis','verified':False,'reason':'high surrogate bits missing; other Unicode blocks remain possible; source confirmation required'}
