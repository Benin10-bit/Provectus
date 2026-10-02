from .rendering import render_asset
from .recovery import isolate_raster
from ..validation.warnings import warn

def extract_assets(q,doc,root,cfg,pages=None):
    def diagnostics(a):
        for code in a.get('source_diagnostics',[]):warn(q,code,'layout',page=a['page'],bbox=a['bbox'])
    overlap=any(w['code']=='SOURCE_LAYOUT_OVERLAP' for w in q['warnings'])
    isolated=[]
    for i,v in enumerate(q.pop('_visuals')):
        kind='ALTERNATIVE_IMAGE' if v['target'] else 'STATEMENT_IMAGE'
        a=isolate_raster(doc,pages[v['page']-1],v,q,root,cfg) if overlap and pages and v.get('objects') else None
        if a:isolated.append((v['page'],v['bbox']))
        else:a=render_asset(doc,v['page'],v['bbox'],root,kind,cfg,padding=0 if v.get('display')=='inline' else None)
        diagnostics(a)
        a.update(document_sha256=q['document_sha256'],order=i,source_objects=v['objects'])
        if v['target']:
            targets=[o for o in q['alternativas'] if o['letra']==v['target']]
            if len(targets)!=1:warn(q,'POSSIBLE_UNASSOCIATED_IMAGE','images',page=v['page'],bbox=v['bbox'])
            if targets:targets[-1]['imagens'].append(a)
        else:q['imagens'].append(a)
        for c in q['content']+q.get('statement',{}).get('segments',[])+[s for o in q['alternativas'] for s in o.get('segments',[])]:
            if c.get('visual_index')==i:c['asset_hash']=a['hash'];c['asset_id']=a['hash'];c['asset_path']=a['path']
        if v.get('role')!='unresolved_symbol' and not v.get('layout_evidence',{}).get('ambiguous'):
            warn(q,'INLINE_VISUAL_CAPTURED' if v.get('display')=='inline' else 'VISUAL_BLOCK_CAPTURED','images',page=v['page'],bbox=v['bbox'],severity='INFO')
    for warning in q['warnings']:
        if warning['code']=='SOURCE_LAYOUT_OVERLAP' and any(p==warning['page'] and box==warning['bbox'] for p,box in isolated):
            warning['code']='SOURCE_OVERLAP_RECOVERED';warning['severity']='INFO';warning['detail']['recovery']='isolated original raster; original crop retained for audit'
    for option in q['alternativas']:
        if not option['texto'] and option['imagens']:warn(q,'GRAPHICAL_ALTERNATIVE','alternatives',severity='INFO',detail={'alternative':option['letra']})
    if cfg.save_originals:
        for i,r in enumerate(q['source_regions']):
            a=render_asset(doc,r['page'],r['bbox'],root,'ORIGINAL_CROP',cfg)
            diagnostics(a)
            a.update(document_sha256=q['document_sha256'],order=i);q['originals'].append(a)
