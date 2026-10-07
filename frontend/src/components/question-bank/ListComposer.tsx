import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronRight, ListPlus, Minus, Plus, RefreshCw, Shuffle, SlidersHorizontal } from 'lucide-react';
import { toast } from 'sonner';
import { displaySubject } from './QuestionCard';
import { ApiError } from '@/lib/api';
import { qb, type AvailableNode, type Composition, type CompositionNode, type CompositionPreview, type Distribution, type Filters, type Folder } from '@/lib/questionBank';

const id=(n:{path:string[];direct?:boolean})=>JSON.stringify([n.path,!!n.direct]);
const title=(n:{path:string[];direct?:boolean})=>n.path.join(' › ')+(n.direct?' › Neste nível':'');
const defaultNode=(n:AvailableNode):CompositionNode=>({path:n.path,direct:n.direct,quantity:null,distribution:'auto',children:n.children.filter(c=>c.available>0).map(defaultNode)});
function entries(nodes:CompositionNode[]):CompositionNode[]{return nodes.flatMap(n=>[n,...entries(n.children)]);}
function setBranch(nodes:CompositionNode[],target:string,change:(node:CompositionNode)=>CompositionNode):CompositionNode[]{return nodes.map(n=>id(n)===target?change(n):{...n,children:setBranch(n.children,target,change)});}
function initializeManual(nodes:CompositionNode[],preview:Map<string,CompositionNode>){return nodes.map(n=>({...n,quantity:n.quantity??preview.get(id(n))?.quantity??0}));}

function Stepper({value,max,label,onChange}:{value:number;max:number;label:string;onChange:(n:number)=>void}){
 return <div className="qb-stepper"><button type="button" aria-label={`Diminuir ${label}`} disabled={value<=0} onClick={()=>onChange(value-1)}><Minus size={13}/></button><input aria-label={label} type="number" min={0} max={max} step={1} value={value} onChange={e=>onChange(e.target.value===''?0:Number(e.target.value))}/><button type="button" aria-label={`Aumentar ${label}`} disabled={value>=max} onClick={()=>onChange(value+1)}><Plus size={13}/></button></div>;
}
function Mode({label,value,onChange}:{label:string;value:Distribution;onChange:(mode:Distribution)=>void}){
 return <label className="qb-composer-mode"><span>{label}</span><select aria-label={label} value={value} onChange={e=>onChange(e.target.value as Distribution)}><option value="auto">Automática</option><option value="manual">Personalizada</option></select></label>;
}
function Branch({available,node,parentMode,preview,change,toggle,depth=0,parentKey=null}:{available:AvailableNode;node?:CompositionNode;parentMode:Distribution;preview:Map<string,CompositionNode>;change:(key:string,fn:(n:CompositionNode)=>CompositionNode)=>void;toggle:(parent:string|null,child:AvailableNode)=>void;depth?:number;parentKey?:string|null}){
 const [open,setOpen]=useState(false),key=id(available),pathTitle=title(available),qty=preview.get(key)?.quantity;
 const target=parentMode==='manual'?node?.quantity:qty;
 const assigned=node?.children.reduce((sum,n)=>sum+(n.quantity??0),0)||0;
 const flexible=node?.children.some(n=>n.quantity===null);
 return <div className={`qb-compose-branch ${node?'selected':''} ${depth===0?'subject':''}`}>
  <div className="qb-compose-row">
   <button type="button" className="qb-branch-toggle" aria-label={`${open?'Recolher':'Expandir'} ${pathTitle}`} aria-expanded={open} disabled={!available.children.length||!node} onClick={()=>setOpen(v=>!v)}>{available.children.length?(open?<ChevronDown size={15}/>:<ChevronRight size={15}/>):<span/>}</button>
   <label className="qb-compose-select"><input type="checkbox" aria-label={`Incluir ${pathTitle}`} checked={!!node} disabled={!node&&available.available===0} onChange={()=>toggle(parentKey,available)}/><span><strong>{depth===0?displaySubject(available.name):available.name.replace(/_/g,' ')}</strong><small>{available.available.toLocaleString('pt-BR')} disponíveis</small></span></label>
   {node&&<div className="qb-compose-quantity">{parentMode==='manual'&&node.quantity!==null?<Stepper label={`Quantidade de ${pathTitle}`} value={node.quantity} max={available.available} onChange={value=>change(key,n=>({...n,quantity:value}))}/>:<span className="qb-auto-value">{qty!==undefined&&<b>{qty}</b>}<small>AUTO</small></span>}{parentMode==='manual'&&<button className="qb-auto-toggle" type="button" aria-label={`${node.quantity===null?'Definir quantidade de':'Usar quantidade automática em'} ${pathTitle}`} onClick={()=>change(key,n=>({...n,quantity:n.quantity===null?(qty??0):null}))}>{node.quantity===null?'Definir':'AUTO'}</button>}</div>}
  </div>
  {open&&node&&<div className="qb-compose-children">
   <Mode label={`Distribuição em ${pathTitle}`} value={node.distribution} onChange={mode=>change(key,n=>({...n,distribution:mode,children:mode==='manual'?initializeManual(n.children,preview):n.children}))}/>
   {node.distribution==='manual'&&<div className="qb-node-balance" aria-live="polite"><span>{assigned}{target!=null?` / ${target}`:''} distribuídas{flexible?' · Restante AUTO':target!=null&&assigned!==target?` · ${assigned>target?`${assigned-target} excedentes`:`Faltam ${target-assigned}`}`:''}</span>{!flexible&&target!=null&&assigned<target&&node.children.some(n=>n.quantity===0)&&<button type="button" className="qb-link" onClick={()=>change(key,n=>({...n,children:n.children.map(c=>c.quantity===0?{...c,quantity:null}:c)}))}>Completar restante em AUTO</button>}</div>}
   {available.children.map(child=><Branch key={id(child)} available={child} node={node.children.find(n=>id(n)===id(child))} parentMode={node.distribution} preview={preview} change={change} toggle={toggle} parentKey={key} depth={depth+1}/>)}
  </div>}
 </div>;
}

function checkComposition(nodes:CompositionNode[],mode:Distribution,total:number,lookup:Map<string,AvailableNode>){
 const errors:string[]=[];
 function bounds(n:CompositionNode):[number,number]{
  const av=lookup.get(id(n));if(!av){errors.push(`${title(n)}: conteúdo indisponível.`);return [0,0];}
  if(!av.children.length)return [0,av.available];
  return groupBounds(n.children,n.distribution);
 }
 function groupBounds(children:CompositionNode[],dist:Distribution):[number,number]{
  const ranges=children.map(n=>{const [lo,hi]=bounds(n);if(dist==='manual'&&n.quantity!==null){if(!Number.isInteger(n.quantity)||n.quantity<lo||n.quantity>hi)errors.push(`${title(n)}: cota ${n.quantity}; disponíveis até ${hi}, mínimo ${lo}.`);return [n.quantity,n.quantity];}return [lo,hi];});
  return [ranges.reduce((s,r)=>s+r[0],0),ranges.reduce((s,r)=>s+r[1],0)];
 }
 const [minimum,maximum]=groupBounds(nodes,mode);
 if(!Number.isInteger(total)||total<1||total>1000)errors.push('Escolha de 1 a 1.000 questões inteiras.');
 if(!nodes.length)errors.push('Selecione ao menos uma matéria.');
 if(total<minimum)errors.push(`${minimum-total} questões excedentes na composição.`);
 if(total>maximum)errors.push(mode==='manual'&&minimum===maximum?`Faltam ${total-maximum} questões na distribuição.`:`Existem apenas ${maximum} questões elegíveis nos grupos selecionados.`);
 return {errors,minimum,maximum};
}

export default function ListComposer({filters,folders,folderLabel}:{filters:Filters;folders:Folder[];folderLabel:(id:string)=>string}){
 const cache=useQueryClient(),navigate=useNavigate();
 const [name,setName]=useState(''),[count,setCount]=useState(20),[folder,setFolder]=useState(''),[advanced,setAdvanced]=useState(false),[mode,setMode]=useState<Distribution>('auto'),[nodes,setNodes]=useState<CompositionNode[]|null>(null),[order,setOrder]=useState<'shuffle'|'grouped'>('shuffle');
 const [autoSelection,setAutoSelection]=useState(true);
 const [debounced,setDebounced]=useState(filters),[drawn,setDrawn]=useState<{key:string;value:CompositionPreview}|null>(null),[serverError,setServerError]=useState('');
 const filterKey=JSON.stringify(filters);
 useEffect(()=>{const timer=window.setTimeout(()=>setDebounced(filters),180);return ()=>window.clearTimeout(timer);},[filterKey]);
 const availability=useQuery({queryKey:['qb','availability',debounced],queryFn:()=>qb.availability(debounced),staleTime:15000});
 useEffect(()=>{if(availability.data)setNodes(current=>current===null||(autoSelection&&mode==='auto'&&!advanced)?availability.data.tree.filter(n=>n.available>0).map(defaultNode):current);},[availability.data,autoSelection,mode,advanced]);
 const tree=availability.data?.tree||[];
 const lookup=useMemo(()=>{const map=new Map<string,AvailableNode>();function visit(list:AvailableNode[]){for(const n of list){map.set(id(n),n);visit(n.children);}}visit(tree);return map;},[tree]);
 const configuration:Composition={distribution:mode,nodes:nodes||[]};
 const configKey=JSON.stringify({count,filters,configuration,availability:availability.data});
 const active=drawn?.key===configKey?drawn.value:undefined;
 const previewMap=useMemo(()=>new Map(entries(active?.resolved.nodes||[]).map(n=>[id(n),n])),[active]);
 const validation=useMemo(()=>checkComposition(nodes||[],mode,count,lookup),[nodes,mode,count,lookup]);
 const busy=availability.isFetching||JSON.stringify(debounced)!==filterKey;
 const ready=!busy&&!availability.isError&&nodes!==null&&!validation.errors.length;
 function errorMessage(error:Error){if(error instanceof ApiError&&typeof error.detail==='object'&&error.detail){const d=error.detail as {path?:string[]};return `${d.path?.length?d.path.join(' › ')+': ':''}${error.message}`;}return error.message;}
 const draw=useMutation({mutationFn:(request:{key:string;count:number;filters:Filters;composition:Composition})=>qb.preview(request.count,request.filters,request.composition),onMutate:()=>setServerError(''),onSuccess:(value,request)=>{setDrawn({key:request.key,value});},onError:(e:Error)=>{setServerError(errorMessage(e));cache.invalidateQueries({queryKey:['qb','availability']});}});
 const create=useMutation({mutationFn:()=>qb.create(name.trim(),count,folder||null,filters,active?.resolved||configuration,order),onMutate:()=>setServerError(''),onSuccess:value=>{cache.invalidateQueries({queryKey:['qb','library']});toast.success('Lista criada com a composição escolhida.');navigate(`/banco-questoes/listas/${value.id}`);},onError:(e:Error)=>{setServerError(errorMessage(e));cache.invalidateQueries({queryKey:['qb','availability']});}});
 function change(target:string,fn:(n:CompositionNode)=>CompositionNode){setAutoSelection(false);setServerError('');setNodes(current=>setBranch(current||[],target,fn));}
 function toggle(parent:string|null,child:AvailableNode){setAutoSelection(false);setServerError('');const toggleChildren=(children:CompositionNode[])=>children.some(n=>id(n)===id(child))?children.filter(n=>id(n)!==id(child)):[...children,defaultNode(child)];if(parent)change(parent,n=>({...n,children:toggleChildren(n.children)}));else setNodes(current=>toggleChildren(current||[]));}
 function materialize(){if(active){setAutoSelection(false);setNodes(active.resolved.nodes);setMode('manual');setAdvanced(true);setServerError('');}}
 const fixed=validation.minimum;
 return <section className="tac-card qb-composer" aria-label="Construtor de listas">
  <header className="qb-composer-header"><div className="qb-composer-icon"><ListPlus size={22}/></div><div><p className="micro-label">SUA PRÓXIMA PRÁTICA</p><h2>Uma lista do seu jeito</h2><p>Comece com um sorteio. Ajuste cada parte quando quiser.</p></div><span className="qb-composer-badge">{busy?'Recalculando…':`${(availability.data?.total||0).toLocaleString('pt-BR')} elegíveis`}</span></header>
  <form onSubmit={e=>{e.preventDefault();if(ready&&name.trim()&&!draw.isPending)create.mutate();}}>
   <div className="qb-composer-fields"><label>Nome da lista<input required maxLength={160} value={name} onChange={e=>setName(e.target.value)} placeholder="Ex.: Cinemática — revisão"/></label><label>Total de questões<input aria-label="Total de questões" required type="number" min={1} max={1000} value={count} onChange={e=>setCount(e.target.value===''?0:Number(e.target.value))}/></label><label>Salvar em<select value={folder} onChange={e=>setFolder(e.target.value)}><option value="">Início</option>{folders.map(f=><option value={f.id} key={f.id}>{folderLabel(f.id)}</option>)}</select></label></div>
   <div className="qb-composer-chips">{filters.banks.map(b=><span key={b}>{b}</span>)}{filters.difficulties.map(d=><span key={d}>{d}</span>)}{filters.exclude_answered&&<span>Não respondidas</span>}{filters.result&&filters.result!=='all'&&<span>{filters.result==='correct'?'Acertadas':'Erradas'}</span>}{filters.paths.map(p=><span key={p.join('/')}>{p.join(' › ')}</span>)}{filters.search&&<span>Busca: {filters.search}</span>}</div>
   <div className="qb-composer-toolbar"><span><Shuffle size={15}/> Questões sempre sorteadas dentro de cada grupo</span><button type="button" aria-expanded={advanced} className={advanced?'active':''} onClick={()=>setAdvanced(v=>!v)}><SlidersHorizontal size={15}/>{advanced?'Recolher composição':'Personalizar composição'}<ChevronDown size={14}/></button></div>
   {availability.isPending?<div className="qb-composer-skeleton" role="status">Carregando disponibilidade…</div>:availability.isError?<p role="alert">Não foi possível calcular a disponibilidade. <button type="button" className="qb-link" onClick={()=>availability.refetch()}>Tentar novamente</button></p>:<div className={`qb-composer-grid ${advanced?'advanced':''}`}>
    <div className="qb-composer-selection" aria-busy={busy}>
     {advanced?<><Mode label="Distribuição entre matérias" value={mode} onChange={value=>{setAutoSelection(false);setMode(value);if(value==='manual')setNodes(current=>initializeManual(current||[],previewMap));}}/>{tree.map(n=><Branch key={id(n)} available={n} node={nodes?.find(p=>id(p)===id(n))} parentMode={mode} preview={previewMap} change={change} toggle={toggle}/>)}</>:<fieldset className="qb-quick-subjects"><legend>Matérias da lista</legend>{tree.map(n=><label key={id(n)} className={nodes?.some(p=>id(p)===id(n))?'selected':''}><input type="checkbox" aria-label={`Incluir ${n.name}`} checked={!!nodes?.some(p=>id(p)===id(n))} disabled={!n.available&&!nodes?.some(p=>id(p)===id(n))} onChange={()=>toggle(null,n)}/><span>{displaySubject(n.name)}<small>{n.available.toLocaleString('pt-BR')}</small></span></label>)}</fieldset>}
     {!tree.some(n=>n.available>0)&&<p className="qb-composer-empty">Nenhuma questão elegível. Ajuste os filtros ao lado.</p>}
     {advanced&&<p className="qb-composer-hint">Personalizada permite cotas fixas e ramos AUTO. O restante vai para os ramos AUTO selecionados.</p>}
    </div>
    <aside className="qb-composer-summary" aria-label="Resumo da composição">
     <p className="micro-label">COMPOSIÇÃO</p><div className="qb-composer-total"><strong>{count}</strong><span>questões</span></div>
     <div className="qb-composer-distribution">{(nodes||[]).map((n,i)=>{const qty=previewMap.get(id(n))?.quantity??(mode==='manual'?n.quantity:null);return <div key={id(n)}><div><span>{displaySubject(n.path[0])}</span><b>{qty===null||qty===undefined?'AUTO':qty}</b></div><div className="qb-composer-bar"><span style={{width:qty!=null&&count>0?`${Math.min(100,100*qty/count)}%`:'0%',background:`var(--qb-subject-${i%4})`}}/></div>{active&&entries(n.children).filter(c=>!c.children.length&&(previewMap.get(id(c))?.quantity||0)>0).map(c=><small key={id(c)}>{c.path.slice(1).join(' › ')}{c.direct?' · Neste nível':''}<b>{previewMap.get(id(c))?.quantity}</b></small>)}</div>;})}</div>
     <p className={`qb-composer-status ${validation.errors.length?'invalid':'valid'}`} aria-live="polite">{busy?'Recalculando disponibilidade…':active?`${count} / ${count} distribuídas · Pronto para criar`:validation.errors[0]||`${fixed} fixadas · ${Math.max(0,count-fixed)} para distribuição automática`}</p>
     <label className="qb-composer-order">Ordem da lista<select value={order} onChange={e=>setOrder(e.target.value as typeof order)}><option value="shuffle">Embaralhada</option><option value="grouped">Agrupar por matéria/conteúdo</option></select></label>
     <button type="button" className="qb-secondary qb-draw" disabled={!ready||draw.isPending||create.isPending} onClick={()=>draw.mutate({key:configKey,count,filters,composition:configuration})}><RefreshCw size={15} className={draw.isPending?'qb-spinning':''}/>{draw.isPending?'Sorteando…':active?'Sortear novamente':'Sortear distribuição'}</button>
     {active&&<button type="button" className="qb-link" onClick={materialize}>Ajustar quantidades sorteadas</button>}
     <button type="submit" className="qb-primary qb-create-final" disabled={!ready||!name.trim()||create.isPending||draw.isPending}>{create.isPending?'Criando lista…':'Criar lista'}<ChevronRight size={16}/></button>
    </aside>
   </div>}
   {validation.errors.length>1&&advanced&&<ul className="qb-compose-errors" role="alert">{validation.errors.slice(1,6).map((message,i)=><li key={i}>{message}</li>)}</ul>}
   {serverError&&<p role="alert" className="qb-compose-error">{serverError}</p>}
  </form>
 </section>;
}
