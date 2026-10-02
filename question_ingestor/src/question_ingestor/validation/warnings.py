def warn(q,code,component,*,page=None,bbox=None,detail=None,severity='REVIEW'):
    item={'code':code,'severity':severity,'component':component,'page':page,'bbox':bbox,'detail':detail or {}}
    if item not in q['warnings']:q['warnings'].append(item)
