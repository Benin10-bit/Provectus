import os,re,unicodedata
from pathlib import Path

def key(value):return unicodedata.normalize('NFC',value.strip()).casefold()

def hierarchy(relative,cfg):
    p=Path(relative);parents=list(p.parent.parts);warnings=[]
    materia=parents[0] if parents else None
    if materia is None:warnings.append('MISSING_MATERIA')
    levels=parents[1:] if parents else []
    generic=any(re.fullmatch(pattern,p.stem,re.I) for pattern in cfg.generic_filename_patterns)
    if not generic:levels.append(p.stem)
    result=[]
    for value in levels:
        if not result or key(value)!=key(result[-1]):result.append(value)
    if not result:warnings.append('EMPTY_CONTENT_PATH')
    if any(v!=v.strip() for v in p.parts):warnings.append('PATH_WHITESPACE')
    return {'relative_path':p.as_posix(),'filename':p.name,'file_stem':p.stem,'materia':materia,'content_path':result,'generic_filename':generic,'hierarchy_warnings':warnings,'hierarchy_status':'REVIEW' if warnings else 'OK'}

def discover(root,out,cfg,materia=None,path_prefix=None):
    root=Path(root).resolve();out=Path(out).resolve()
    if not root.is_dir():raise ValueError('Input root must be a directory')
    if root==out:raise ValueError('Input and output directories must differ')
    found=[]
    excluded=set(cfg.discovery_ignore_directories)
    for current,dirs,files in os.walk(root,followlinks=False):
        here=Path(current)
        dirs[:]=sorted(d for d in dirs if not d.startswith('.') and d not in excluded and not (here/d).is_symlink() and (here/d).resolve()!=out)
        for name in files:
            p=here/name
            if p.is_symlink() or name.startswith(('.','~')) or p.suffix.casefold()!='.pdf':continue
            rel=p.relative_to(root);h=hierarchy(rel,cfg)
            if materia is not None and key(h['materia'] or '')!=key(materia):continue
            if path_prefix:
                prefix=Path(path_prefix).parts
                if rel.parts[:len(prefix)]!=prefix:continue
            found.append(h)
    return sorted(found,key=lambda h:(key(h['relative_path']),h['relative_path']))
