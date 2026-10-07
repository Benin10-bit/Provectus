import { useDeferredValue, useMemo, useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { ChevronDown, ChevronRight, Eye, FolderPlus, Search, Trash2 } from 'lucide-react';
import AppLayout from '@/components/layout/AppLayout';
import { qb, type Filters, type Folder, type Node, type StudyList } from '@/lib/questionBank';
import { toast } from 'sonner';
import ListComposer from '@/components/question-bank/ListComposer';
import ExportPdfButton from '@/components/question-bank/ExportPdfButton';
import './questionBank.css';
const empty:Filters={paths:[],banks:[],difficulties:[],search:'',exclude_answered:false,result:'all'};
function savedSearch(params:URLSearchParams):Filters {
 try {
  const value=JSON.parse(params.get('f')||'{}');
  return {paths:Array.isArray(value.paths)?value.paths.filter((p:unknown)=>Array.isArray(p)&&p.every(x=>typeof x==='string')):[],
   banks:Array.isArray(value.banks)?value.banks.filter((x:unknown)=>typeof x==='string'):[],
   difficulties:Array.isArray(value.difficulties)?value.difficulties.filter((x:unknown)=>typeof x==='string'):[],
   search:typeof value.search==='string'?value.search:'',exclude_answered:value.exclude_answered===true&&!['correct','incorrect'].includes(value.result),result:value.result==='correct'||value.result==='incorrect'?value.result:'all'};
 }catch{return empty;}
}
const label=(path:string[])=>path.join(' › ');
function MultiFilter({title,values,selected,onToggle}:{title:string;values:string[];selected:string[];onToggle:(value:string)=>void}){
 return <fieldset className="qb-multi-filter"><legend>{title}</legend><p>{selected.length?`${selected.length} selecionada${selected.length>1?'s':''}`:'Todas — selecione uma ou mais'}</p><div className="qb-filter-options">{Array.from(new Set([...values,...selected])).map(value=><label key={value} className="qb-check"><input type="checkbox" checked={selected.includes(value)} onChange={()=>onToggle(value)}/><span>{value}</span></label>)}</div></fieldset>;
}
function TreeNode({node,selected,onToggle,search}:{node:Node;selected:string[][];onToggle:(path:string[])=>void;search:string}){
 const match=node.name.toLocaleLowerCase().includes(search.toLocaleLowerCase());
 const children=node.children.filter(x=>match||matches(x,search));
 const [expanded,setExpanded]=useState(false);
 if(search&&!match&&!children.length)return null;
 const isSelected=selected.some(p=>label(p)===label(node.path));
 const parent=selected.some(p=>p.length<node.path.length && p.every((s,i)=>s===node.path[i]));
 return <div className="qb-tree-node">
  <div className="qb-tree-row">
   <button type="button" disabled={!node.children.length} aria-label={`${expanded?'Recolher':'Expandir'} ${node.name}`} onClick={()=>setExpanded(v=>!v)}>{node.children.length?(expanded||search?<ChevronDown size={15}/>:<ChevronRight size={15}/>):<span className="inline-block w-4"/>}</button>
   <label><input type="checkbox" checked={isSelected||parent} disabled={parent} onChange={()=>onToggle(node.path)}/><span>{node.name}</span></label>
  </div>
  {(expanded||!!search)&&children.length>0&&<div className="qb-tree-children">{children.map(x=><TreeNode key={label(x.path)} node={x} selected={selected} onToggle={onToggle} search={search}/>)}</div>}
 </div>;
}
function matches(node:Node,query:string):boolean{return node.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())||node.children.some(x=>matches(x,query));}
function StudyFolder({folder,folders,lists,depth=0,onAction}:{folder:Folder;folders:Folder[];lists:StudyList[];depth?:number;onAction:(kind:string,id:string)=>void}){
 const [expanded,setExpanded]=useState(false);
 return <div className="qb-folder" style={{marginLeft:Math.min(depth,5)*12}}>
  <div className="qb-folder-title"><button onClick={()=>setExpanded(x=>!x)} aria-label={`${expanded?'Recolher':'Expandir'} ${folder.name}`}>{expanded?<ChevronDown size={17}/>:<ChevronRight size={17}/>}</button><strong>{folder.name}</strong><span className="text-xs text-muted-foreground">{lists.filter(l=>l.folder_id===folder.id).length} listas</span><div className="qb-actions"><button onClick={()=>onAction('subfolder',folder.id)}>Subpasta</button><button onClick={()=>onAction('editfolder',folder.id)}>Renomear</button><button onClick={()=>onAction('movefolder',folder.id)}>Mover</button><button onClick={()=>onAction('deletefolder',folder.id)} aria-label={`Excluir pasta ${folder.name}`}><Trash2 size={14}/></button></div></div>
  {expanded&&<div className="qb-folder-content">{lists.filter(l=>l.folder_id===folder.id).map(l=><ListRow key={l.id} value={l} onAction={onAction}/>)}{folders.filter(x=>x.parent_id===folder.id).map(x=><StudyFolder key={x.id} folder={x} folders={folders} lists={lists} depth={depth+1} onAction={onAction}/>)}{!lists.some(x=>x.folder_id===folder.id)&&!folders.some(x=>x.parent_id===folder.id)&&<p className="text-sm text-muted-foreground p-3">Pasta vazia.</p>}</div>}
 </div>;
}
function ListRow({value:l,onAction}:{value:StudyList;onAction:(kind:string,id:string)=>void}){
 return <div className="qb-list-row"><Link className="font-medium hover:text-primary min-w-0 truncate" to={`/banco-questoes/listas/${l.id}`}>{l.name}</Link><div className="qb-counts"><span>{l.total} questões</span><span>{l.answered} respondidas</span><span className="text-success">{l.correct} certas</span><span className="text-critical">{l.wrong} erradas</span>{l.answered>0&&<span>{Math.round(100*l.correct/l.answered)}%</span>}</div><div className="qb-actions"><ExportPdfButton listId={l.id} name={l.name} compact/><button onClick={()=>onAction('editlist',l.id)}>Renomear</button><button onClick={()=>onAction('movelist',l.id)}>Mover</button><button aria-label={`Excluir lista ${l.name}`} onClick={()=>onAction('deletelist',l.id)}><Trash2 size={15}/></button></div></div>;
}
export default function QuestionBankPage(){
 const location=useLocation(),cache=useQueryClient(),[url,setUrl]=useSearchParams();
 const [tab,setTab]=useState<'explorar'|'listas'>(url.get('tab')==='listas'?'listas':'explorar');
 const [filters,setFilters]=useState<Filters>(()=>savedSearch(url)),[treeSearch,setTreeSearch]=useState(''),[page,setPage]=useState(()=>Math.max(1,Number(url.get('page'))||1));
 const deferred=useDeferredValue(filters);
 const [librarySearch,setLibrarySearch]=useState('');
 useEffect(()=>{
  const next=new URLSearchParams(url);
  if(tab==='listas')next.set('tab','listas');else next.delete('tab');
  if(filters.paths.length||filters.banks.length||filters.difficulties.length||filters.search||filters.exclude_answered||filters.result!=='all')next.set('f',JSON.stringify(filters));else next.delete('f');
  if(page>1)next.set('page',String(page));else next.delete('page');
  if(next.toString()!==url.toString())setUrl(next,{replace:true});
 },[filters,page,tab,setUrl,url]);
 const [moveTarget,setMoveTarget]=useState<{kind:'movelist'|'movefolder';id:string}|null>(null),[moveDestination,setMoveDestination]=useState('');
 const options=useQuery({queryKey:['qb','filters'],queryFn:qb.filters,staleTime:300000});
 const results=useQuery({queryKey:['qb','search',deferred,page],queryFn:()=>qb.search(deferred,page),enabled:tab==='explorar'});
 const library=useQuery({queryKey:['qb','library'],queryFn:qb.library,enabled:tab==='listas'||tab==='explorar'});
 const toggle=(path:string[])=>{setPage(1);setFilters(f=>{const exact=f.paths.some(p=>label(p)===label(path));return {...f,paths:exact?f.paths.filter(p=>label(p)!==label(path)): [...f.paths.filter(p=>!(p.length>path.length&&path.every((x,i)=>x===p[i]))),path]};});};
 const toggleValue=(key:'banks'|'difficulties',value:string)=>{setPage(1);setFilters(f=>({...f,[key]:f[key].includes(value)?f[key].filter(x=>x!==value):[...f[key],value]}));};
 const mutate=useMutation({mutationFn:async(action:{kind:string;id:string;destination?:string})=>{
  const {kind,id}=action;
  if(kind.startsWith('delete')){if(!window.confirm('Excluir este item? Esta ação é permanente.'))return;await qb.remove(kind==='deletelist'?'lists':'folders',id);return;}
  if(kind==='movelist'||kind==='movefolder'){if(kind==='movelist')await qb.editList(id,{folder_id:action.destination||null});else await qb.editFolder(id,{parent_id:action.destination||null});return;}
  const value=window.prompt(kind==='subfolder'?'Nome da subpasta':kind==='editlist'?'Novo nome da lista':kind==='editfolder'?'Novo nome da pasta':'Nome da pasta');
  if(!value?.trim())return;
  if(kind==='subfolder')await qb.folder(value,id);
  else if(kind==='editlist')await qb.editList(id,{name:value});
  else if(kind==='editfolder')await qb.editFolder(id,{name:value});
  else await qb.folder(value,null);
 },onSuccess:()=>{cache.invalidateQueries({queryKey:['qb','library']});toast.success('Biblioteca atualizada');},onError:(e:Error)=>toast.error(e.message)});
 const act=(kind:string,id:string)=>{if(kind==='movelist'||kind==='movefolder'){setMoveTarget({kind,id});setMoveDestination('');return;}mutate.mutate({kind,id});};
 const visible=useMemo(()=>{
  const data=library.data;if(!data)return {folders:[],lists:[]};
  const q=librarySearch.toLocaleLowerCase().trim();if(!q)return data;
  const matched=new Set(data.folders.filter(f=>f.name.toLocaleLowerCase().includes(q)).map(f=>f.id));
  const descendants=new Set(matched);
  let expanded=true;while(expanded){expanded=false;for(const f of data.folders)if(f.parent_id&&descendants.has(f.parent_id)&&!descendants.has(f.id)){descendants.add(f.id);expanded=true}}
  const lists=data.lists.filter(l=>l.name.toLocaleLowerCase().includes(q)||!!(l.folder_id&&descendants.has(l.folder_id)));
  const folderIds=new Set([...descendants,...lists.map(l=>l.folder_id).filter(Boolean) as string[]]);
  for(const f of data.folders){let parent=f.parent_id;while(folderIds.has(f.id)&&parent){folderIds.add(parent);parent=data.folders.find(x=>x.id===parent)?.parent_id||null}}
  return {folders:data.folders.filter(f=>folderIds.has(f.id)),lists};
 },[library.data,librarySearch]);
 const roots=visible.folders.filter(f=>!f.parent_id);
 const folderLabel=(id:string)=>{const parts:string[]=[];let current=library.data?.folders.find(f=>f.id===id);while(current){parts.unshift(current.name);current=library.data?.folders.find(f=>f.id===current!.parent_id)}return parts.join(' / ')};
 return <AppLayout><div className="qb-page"><div className="qb-heading"><div><p className="micro-label">CATÁLOGO DE PRÁTICA</p><h1>Banco de Questões</h1><p className="text-muted-foreground text-sm mt-1">Encontre questões, monte listas e acompanhe seus acertos.</p></div><div className="qb-tabs" role="tablist"><button role="tab" aria-selected={tab==='explorar'} className={tab==='explorar'?'active':''} onClick={()=>setTab('explorar')}>Explorar</button><button role="tab" aria-selected={tab==='listas'} className={tab==='listas'?'active':''} onClick={()=>setTab('listas')}>Minhas listas</button></div></div>
 {tab==='explorar'?<div className="qb-explore"><aside className="tac-card qb-filters"><h2>Filtrar questões</h2><label className="qb-label">Buscar na árvore<input value={treeSearch} onChange={e=>setTreeSearch(e.target.value)} placeholder="Matéria ou conteúdo"/></label><div className="qb-tree" aria-label="Matérias e conteúdos">{options.isLoading?'Carregando conteúdos…':options.isError?'Não foi possível carregar os filtros.':options.data?.tree.map(node=><TreeNode key={node.name} node={node} selected={filters.paths} onToggle={toggle} search={treeSearch}/>)}</div><MultiFilter title="Bancas" values={options.data?.banks||[]} selected={filters.banks} onToggle={value=>toggleValue('banks',value)}/><MultiFilter title="Dificuldades" values={options.data?.difficulties||[]} selected={filters.difficulties} onToggle={value=>toggleValue('difficulties',value)}/><label className="qb-label">Resultado<select value={filters.result||'all'} onChange={e=>{setPage(1);setFilters(f=>({...f,result:e.target.value as Filters['result'],exclude_answered:e.target.value==='all'?f.exclude_answered:false}));}}><option value="all">Todos os resultados</option><option value="correct">Apenas as que acertei</option><option value="incorrect">Apenas as que errei</option></select></label><label className="qb-check qb-exclude"><input type="checkbox" checked={!!filters.exclude_answered} onChange={e=>{setPage(1);setFilters(f=>({...f,exclude_answered:e.target.checked,result:e.target.checked?'all':f.result}));}}/><span>Excluir já respondidas<small>Avulsas e listas, certas ou erradas.</small></span></label><button className="qb-link" onClick={()=>{setFilters(empty);setPage(1);}}>Limpar filtros</button></aside>
 <div className="qb-results"><ListComposer filters={filters} folders={library.data?.folders||[]} folderLabel={folderLabel}/><section className="tac-card"><div className="qb-results-header"><div><p className="micro-label">RESULTADO DA BUSCA</p><h2>{results.isLoading?'Consultando…':results.isError?'Busca indisponível':`${results.data?.total.toLocaleString('pt-BR')||0} questões encontradas`}</h2></div><label className="qb-search"><Search size={17}/><input placeholder="Buscar no enunciado" value={filters.search} onChange={e=>{setPage(1);setFilters(f=>({...f,search:e.target.value}));}}/></label></div><div className="qb-chips">{filters.paths.map(p=><button key={label(p)} onClick={()=>toggle(p)} aria-label={`Remover ${label(p)}`}>{label(p)} ×</button>)}{filters.banks.map(b=><button key={b} aria-label={`Remover banca ${b}`} onClick={()=>toggleValue('banks',b)}>{b} ×</button>)}{filters.difficulties.map(d=><button key={d} aria-label={`Remover dificuldade ${d}`} onClick={()=>toggleValue('difficulties',d)}>{d} ×</button>)}{filters.result&&filters.result!=='all'&&<button aria-label="Remover filtro de resultado" onClick={()=>{setPage(1);setFilters(f=>({...f,result:'all'}));}}>{filters.result==='correct'?'Acertei':'Errei'} ×</button>}{filters.exclude_answered&&<button onClick={()=>{setPage(1);setFilters(f=>({...f,exclude_answered:false}));}} aria-label="Incluir já respondidas">Não respondidas ×</button>}</div>{results.isError&&<p role="alert" className="text-critical">{(results.error as Error).message}</p>}{results.data?.items.map(q=><article key={q.id} className="qb-preview"><div className="qb-preview-meta">{q.materia} · {q.banca_normalizada||'Banca não informada'} · {q.dificuldade_normalizada||'Dificuldade não informada'}</div><p>{q.enunciado}</p><Link className="qb-open-question" to={`/banco-questoes/questoes/${encodeURIComponent(q.id)}`} state={{returnTo:location.pathname+location.search,resultIds:results.data?.items.map(item=>item.id)}}><Eye size={15}/>Abrir questão<ChevronRight size={15}/></Link></article>)}{results.data?.total===0&&<p className="text-muted-foreground py-8">Nenhuma questão corresponde aos filtros. Ajuste sua seleção.</p>}<div className="qb-pagination"><button disabled={page===1} onClick={()=>setPage(p=>p-1)}>Anterior</button><span>Página {page}</span><button disabled={page*12>=(results.data?.total||0)} onClick={()=>setPage(p=>p+1)}>Próxima</button></div></section>
 </div></div>:<section className="tac-card qb-library"><div className="qb-results-header"><div><p className="micro-label">ORGANIZAÇÃO</p><h2>Minhas listas</h2><p className="text-sm text-muted-foreground">{library.data?.lists.length||0} listas</p></div><div className="qb-library-tools"><label className="qb-search"><Search size={17}/><input placeholder="Buscar lista ou pasta" value={librarySearch} onChange={e=>setLibrarySearch(e.target.value)}/></label><button className="qb-primary" onClick={()=>act('newfolder','')}><FolderPlus size={16}/> Nova pasta</button></div></div>{library.isLoading?<p>Carregando listas…</p>:library.isError?<p role="alert" className="text-critical">Não foi possível carregar suas listas.</p>:<div className="qb-library-body">{visible.lists.filter(l=>!l.folder_id).map(l=><ListRow key={l.id} value={l} onAction={act}/>)}{roots.map(f=><StudyFolder key={f.id} folder={f} folders={visible.folders} lists={visible.lists} onAction={act}/>)}{!library.data?.lists.length&&!library.data?.folders.length&&<p className="text-muted-foreground">Nenhuma lista ainda. Selecione questões em Explorar para começar.</p>}</div>}</section>}{moveTarget&&<div className="qb-modal-backdrop" role="presentation" onMouseDown={()=>setMoveTarget(null)}><div className="tac-card qb-modal" role="dialog" aria-modal="true" aria-label="Mover item" onMouseDown={e=>e.stopPropagation()}><h2>Mover para pasta</h2><label className="qb-label">Destino<select autoFocus value={moveDestination} onChange={e=>setMoveDestination(e.target.value)}><option value="">Início</option>{library.data?.folders.filter(f=>f.id!==moveTarget.id).map(f=><option key={f.id} value={f.id}>{folderLabel(f.id)}</option>)}</select></label><div className="qb-modal-actions"><button className="qb-secondary" onClick={()=>setMoveTarget(null)}>Cancelar</button><button className="qb-primary" disabled={mutate.isPending} onClick={()=>{mutate.mutate({kind:moveTarget.kind,id:moveTarget.id,destination:moveDestination},{onSuccess:()=>setMoveTarget(null)});}}>Mover</button></div></div></div>}</div></AppLayout>;
}
