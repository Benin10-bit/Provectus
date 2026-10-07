"""Hierarchical quotas. Availability, allocation and question sampling are separate.

AUTO draws uniformly among currently unsaturated groups, rather than weighting by
catalog size. Every participating nonempty group receives at least one question
when the budget allows it. Fixed quotas and descendant minima are reserved first.
This gives variable compositions without letting a huge catalog monopolize them.
"""
import json
import random
import secrets
from typing import Literal
from pydantic import BaseModel, Field
from fastapi import HTTPException
from sqlalchemy import text

class CompositionNode(BaseModel):
    path: list[str] = Field(min_length=1, max_length=12)
    direct: bool = False
    quantity: int | None = Field(None, ge=0, le=1000)
    distribution: Literal['auto','manual'] = 'auto'
    children: list['CompositionNode'] | None = Field(None, max_length=1000)

class Composition(BaseModel):
    distribution: Literal['auto','manual'] = 'auto'
    nodes: list[CompositionNode] = Field(default_factory=list, max_length=1000)
    seed: str = Field(default_factory=lambda: secrets.token_hex(16), max_length=64)


def fail(code,message,path=None,**details):
    raise HTTPException(422,dict(code=code,message=message,path=path or [],**details))


def key(path,direct=False):return (tuple(path),direct)


def catalog(rows):
    """Normalize both importer path formats; merge documents in the same bucket."""
    roots={}
    for subject,raw,count in rows:
        if not subject:continue
        parts=raw if isinstance(raw,list) else json.loads(raw or '[]')
        if parts and parts[0]==subject:parts=parts[1:]
        if any(not isinstance(part,str) or not part for part in parts):continue
        current=roots.setdefault(subject,dict(name=subject,path=[subject],available=0,own=0,children={}))
        for part in parts:
            current=current['children'].setdefault(part,dict(name=part,path=[*current['path'],part],available=0,own=0,children={}))
        current['own']+=count
        current['has_direct']=True
    def finish(node):
        children=[finish(child) for _,child in sorted(node['children'].items())]
        if children and node.get('has_direct'):
            children.insert(0,dict(name='Questões neste nível',path=node['path'],direct=True,available=node['own'],children=[]))
        return dict(name=node['name'],path=node['path'],direct=False,available=node['own']+sum(c['available'] for c in children if not c.get('direct')),children=children)
    return [finish(node) for _,node in sorted(roots.items())]


def allocate(total,ranges,rng,path=()):
    """Inclusive integer bounds; random remainder, one per group when feasible."""
    low=[a for a,b in ranges];high=[b for a,b in ranges]
    if total<sum(low):fail('under_total',f'As cotas mínimas somam {sum(low)}, acima das {total} questões deste grupo.',list(path),requested=total,minimum=sum(low))
    if total>sum(high):fail('capacity',f'Existem apenas {sum(high)} questões disponíveis neste grupo.',list(path),requested=total,available=sum(high))
    values=low[:];remaining=total-sum(values)
    newcomers=[i for i in range(len(values)) if values[i]==0 and high[i]>0]
    if remaining>=len(newcomers):
        for i in newcomers:values[i]+=1
        remaining-=len(newcomers)
    active=[i for i in range(len(values)) if values[i]<high[i]]
    while remaining:
        i=rng.choice(active);values[i]+=1;remaining-=1
        if values[i]==high[i]:active.remove(i)
    return values


def resolve(tree,composition,total):
    lookup={}
    def index(nodes):
        for node in nodes:
            lookup[key(node['path'],node.get('direct',False))]=node;index(node['children'])
    index(tree)
    visited=0
    def default(node):return CompositionNode(path=node['path'],direct=node.get('direct',False))
    def prepare(nodes,parent=None):
        nonlocal visited
        result=[];seen=set()
        for node in nodes:
            visited+=1
            if visited>6000:fail('too_many_nodes','A composição excede 6.000 grupos.')
            if any(not part.strip() or len(part)>160 for part in node.path):fail('path','Caminho de conteúdo inválido.',node.path)
            k=key(node.path,node.direct)
            if k in seen:fail('duplicate_group','Grupo repetido na composição.',node.path)
            seen.add(k)
            available=lookup.get(k)
            if available is None:fail('unknown_group','Este grupo não existe na hierarquia do banco.',node.path)
            if parent is None and (len(node.path)!=1 or node.direct):fail('hierarchy','A composição deve começar pelas matérias.',node.path)
            if parent is not None and k not in {key(x['path'],x.get('direct',False)) for x in parent['children']}:
                fail('hierarchy','O conteúdo não pertence diretamente a este nível.',node.path)
            if node.direct and node.children:fail('hierarchy','Questões deste nível não têm subdivisões.',node.path)
            if node.children and not available['children']:fail('hierarchy','Este conteúdo não tem subdivisões.',node.path)
            children=prepare(node.children,available) if node.children else [ ]
            # Unexpanded AUTO subtrees still draw a composition at every level.
            if node.children is None and available['children']:
                children=prepare([default(c) for c in available['children']],available)
            if children:
                ranges=child_ranges(children,node.distribution)
                lo=sum(x[0] for x in ranges);hi=sum(x[1] for x in ranges)
            else:lo,hi=0,(0 if available['children'] else available['available'])
            result.append(dict(node=node,available=available,children=children,low=lo,high=hi))
        return result
    def child_ranges(children,mode):
        result=[]
        for child in children:
            n=child['node'];lo,hi=child['low'],child['high']
            if mode=='manual' and n.quantity is not None:
                if n.quantity<lo or n.quantity>hi:
                    fail('quota',f'Cota de {n.quantity} incompatível: este grupo permite de {lo} a {hi} questões.',n.path,requested=n.quantity,minimum=lo,available=hi)
                lo=hi=n.quantity
            result.append((lo,hi))
        return result
    if composition.distribution=='manual' and not composition.nodes:fail('empty','Selecione ao menos uma matéria.')
    selected=composition.nodes or [default(node) for node in tree if node['available']>0]
    prepared=prepare(selected)
    rng=random.Random(composition.seed)
    leaves=[]
    def draw(children,count,mode,path=()):
        values=allocate(count,child_ranges(children,mode),rng,path)
        result=[]
        for child,qty in zip(children,values):
            n=child['node'];av=child['available']
            nested=draw(child['children'],qty,n.distribution,n.path) if child['children'] else []
            if not child['children'] and qty:leaves.append(dict(path=n.path,direct=n.direct,quantity=qty))
            result.append(dict(path=n.path,direct=n.direct,quantity=qty,distribution='manual',children=nested))
        return result
    resolved=draw(prepared,total,composition.distribution)
    return dict(total=total,seed=composition.seed,resolved=dict(distribution='manual',nodes=resolved,seed=composition.seed),groups=leaves)


def sample(db,fragment,params,groups,run_filter):
    """One ranked SQL query samples every disjoint terminal bucket. No N+1 reads."""
    cases=[];args=dict(params);quotas=[]
    postgres=db.get_bind().dialect.name=='postgresql'
    for i,group in enumerate(groups):
        path=group['path'];args[f'subject{i}']=path[0]
        args[f'path{i}']=json.dumps(path[1:],ensure_ascii=False)
        args[f'full{i}']=json.dumps(path,ensure_ascii=False)
        if postgres:
            exact=f'(d.content_path = CAST(:path{i} AS jsonb) OR d.content_path = CAST(:full{i} AS jsonb))'
        else:
            # SQLite is used only by isolated tests; decode each JSON string so
            # escaped and literal Unicode paths compare identically.
            for j,part in enumerate(path):args[f'part{i}_{j}']=part
            short=' AND '.join(f'd.content_path ->> {j} = :part{i}_{j+1}' for j in range(len(path)-1))
            full=' AND '.join(f'd.content_path ->> {j} = :part{i}_{j}' for j in range(len(path)))
            exact=f'((json_array_length(d.content_path)={len(path)-1}'+(f' AND {short}' if short else '')+f') OR (json_array_length(d.content_path)={len(path)} AND {full}))'
        cases.append(f'WHEN d.materia=:subject{i} AND {exact} THEN {i}')
        args[f'quota{i}']=group['quantity'];quotas.append(f'WHEN {i} THEN :quota{i}')
    if not groups:return []
    sql='WITH candidates AS (SELECT q.id,CASE '+' '.join(cases)+' END AS bucket'+fragment+'''),
      ranked AS (SELECT id,bucket,row_number() OVER(PARTITION BY bucket ORDER BY random()) AS rn
      FROM candidates WHERE bucket IS NOT NULL)
      SELECT id,bucket FROM ranked WHERE rn <= CASE bucket '''+' '.join(quotas)+' END ORDER BY bucket,rn'
    return run_filter(db,sql,args).all()
