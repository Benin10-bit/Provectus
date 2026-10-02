from pathlib import Path
from io import BytesIO
import hashlib
import pymupdf as fitz
from PIL import Image, ImageDraw

def render_asset(doc,page,bbox,root,kind,cfg,padding=None):
    pad=cfg.asset_padding if padding is None else padding
    clip=(fitz.Rect(bbox)+(-pad,-pad,pad,pad)) & doc[page-1].rect
    cached=getattr(doc,'_verified_render_cache',{}).get((kind,page,tuple(clip),cfg.dpi))
    if cached:return dict(cached)
    fitz.TOOLS.mupdf_warnings(reset=True)
    pix=doc[page-1].get_pixmap(matrix=fitz.Matrix(cfg.dpi/72,cfg.dpi/72),clip=clip,alpha=False)
    engine_warning=fitz.TOOLS.mupdf_warnings(reset=True)
    # This source emits a known malformed-hex warning even before sanitization.
    # Resource/rendering warnings introduced by a transformation must never pass silently.
    remaining=[l for l in engine_warning.splitlines() if l and l not in ('invalid character in hex string','closepath with no current point') and not l.startswith('... repeated ')]
    if remaining:raise RuntimeError('PDF_RENDER_DIAGNOSTIC')
    im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    # Mask recurring margin text only when it intersects a requested regional render.
    painter=ImageDraw.Draw(im)
    scale=cfg.dpi/72
    for box in getattr(doc,'_privacy_exclusions',{}).get(page,[]):
        r=fitz.Rect(box)&clip
        if not r.is_empty:painter.rectangle(((r.x0-clip.x0)*scale,(r.y0-clip.y0)*scale,(r.x1-clip.x0)*scale,(r.y1-clip.y0)*scale),fill='white')
    buf=BytesIO();im.save(buf,format='WEBP',lossless=cfg.lossless_webp,quality=cfg.webp_quality,method=4)
    data=buf.getvalue();digest=hashlib.sha256(data).hexdigest()
    directory='originals' if kind=='ORIGINAL_CROP' else 'questions'
    path=Path('storage')/directory/digest[:2]/(digest+'.webp');(root/path).parent.mkdir(parents=True,exist_ok=True)
    if not (root/path).exists() or hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:(root/path).write_bytes(data)
    return {'hash':digest,'path':path.as_posix(),'mime_type':'image/webp','width':pix.width,'height':pix.height,'size_bytes':len(data),'type':kind,'page':page,'bbox':list(clip),'dpi':cfg.dpi,'source_diagnostics':['SOURCE_EMPTY_CLOSEPATH'] if 'closepath with no current point' in engine_warning else []}
