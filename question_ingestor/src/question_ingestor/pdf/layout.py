"""Group geometric primitives; zero-height rules remain meaningful objects."""
def union(boxes):
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]

def touches(a,b,t):
    return a[0]<=b[2]+t and b[0]<=a[2]+t and a[1]<=b[3]+t and b[1]<=a[3]+t

def graphical_regions(page,cfg):
    regions=[]
    for o in page['objects']+page['drawings']:
        b=o['bbox'];area=max(b[2]-b[0],.5)*max(b[3]-b[1],.5)
        if area<cfg.min_asset_area:continue
        regions.append({'bbox':b.copy(),'objects':[o['id']],'kind':o['kind']})
    changed=True
    while changed:
        changed=False
        for i,a in enumerate(regions):
            hit=next((j for j in range(i+1,len(regions)) if a['kind']=='drawing' and regions[j]['kind']=='drawing' and touches(a['bbox'],regions[j]['bbox'],cfg.drawing_join_tolerance)),None)
            if hit is not None:
                b=regions.pop(hit);a['bbox']=union([a['bbox'],b['bbox']]);a['objects']+=b['objects'];a['kind']='composite' if a['kind']!=b['kind'] else a['kind'];changed=True;break
    # Parallel column rules with matching extents and regular row gaps indicate a table.
    rules=sorted([r for r in regions if r['kind']=='drawing' and r['bbox'][3]-r['bbox'][1]<=cfg.geometry_epsilon and r['bbox'][2]-r['bbox'][0]>50],key=lambda r:r['bbox'][1])
    groups=[]
    for r in rules:
        group=next((g for g in groups if abs(g[-1]['bbox'][0]-r['bbox'][0])<=cfg.drawing_join_tolerance and abs(g[-1]['bbox'][2]-r['bbox'][2])<=cfg.drawing_join_tolerance and r['bbox'][1]-g[-1]['bbox'][1]<=cfg.table_max_row_gap),None)
        if group is None:groups.append([r])
        else:group.append(r)
    for group in groups:
        if len(group)<2:continue
        box=union([r['bbox'] for r in group]);gap=(group[-1]['bbox'][1]-group[0]['bbox'][1])/(len(group)-1)
        candidates=[l for l in page['lines'] if l['bbox'][0]>=box[0]-cfg.geometry_epsilon and l['bbox'][2]<=box[2]+cfg.geometry_epsilon and l['bbox'][1]>=box[1]-gap*cfg.table_header_rows and l['bbox'][3]<=box[3]+gap]
        for r in group:regions.remove(r)
        regions.append({'bbox':union([box]+[l['bbox'] for l in candidates]),'objects':[o for r in group for o in r['objects']],'kind':'composite','role':'table','embedded_line_ids':[l['id'] for l in candidates],'embedded_text':'\n'.join(l['text'] for l in candidates)})
    return regions
