import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import AppLayout from '@/components/layout/AppLayout';
import { qb, type Question } from '@/lib/questionBank';
import QuestionCard from '@/components/question-bank/QuestionCard';
import ExportPdfButton from '@/components/question-bank/ExportPdfButton';
import './questionBank.css';
export default function QuestionListPage(){
 const {id=''}=useParams(),[params,setParams]=useSearchParams();
 const page=Math.max(1,Number(params.get('q'))||1),cache=useQueryClient();
 const query=useQuery({queryKey:['qb','list',id,page],queryFn:()=>qb.list(id,page),enabled:!!id});
 const q=query.data?.items[0];const [selected,setSelected]=useState<string|null>(null),[eliminated,setEliminated]=useState<string[]>([]),[saving,setSaving]=useState(false),[cutting,setCutting]=useState(false);
 useEffect(()=>{setSelected(q?.selected||null);setEliminated(q?.eliminated||[]);},[q?.id,q?.selected,JSON.stringify(q?.eliminated)]);
 const move=(next:number)=>setParams({q:String(next)});
 const update=(transform:(x:Question)=>Question)=>cache.setQueryData(['qb','list',id,page],(old:typeof query.data)=>old?{...old,items:old.items.map(transform)}:old);
 async function cut(letter:string){if(!q||q.answered_at)return;const next=eliminated.includes(letter)?eliminated.filter(x=>x!==letter):[...eliminated,letter];setEliminated(next);setCutting(true);try{await qb.eliminate(id,q.id,next);update(x=>({...x,eliminated:next}));}catch(e){setEliminated(eliminated);toast.error((e as Error).message)}finally{setCutting(false)}}
 async function answer(){if(!q||!selected)return;setSaving(true);try{const response=await qb.answer(id,q.id,selected);update(x=>({...x,selected:response.selected,correct:response.correct,answer:response.answer,answered_at:new Date().toISOString()}));cache.invalidateQueries({queryKey:['qb','library']});cache.invalidateQueries({queryKey:['qb','search']});cache.invalidateQueries({queryKey:['qb','availability']});toast[response.correct?'success':'info'](response.correct?'Resposta correta':'Resposta registrada. Confira o gabarito.');}catch(e){toast.error((e as Error).message)}finally{setSaving(false)}}
 return <AppLayout><div className="qb-page qb-solve"><div className="qb-heading"><div><Link to="/banco-questoes?tab=listas" className="qb-back"><ArrowLeft size={16}/> Minhas listas</Link><p className="micro-label">PRÁTICA DIRECIONADA</p><h1>{query.data?.name||'Carregando lista…'}</h1></div><ExportPdfButton listId={id} name={query.data?.name||'Lista'}/></div>
 {query.isError?<div className="tac-card text-critical" role="alert">Não foi possível carregar a lista. {(query.error as Error).message}</div>:query.isLoading?<div className="tac-card">Carregando questão…</div>:q?<><div className="qb-progress"><span>Questão {page} de {query.data!.total}</span><div className="qb-progress-track"><div style={{width:`${page/query.data!.total*100}%`}}/></div><select aria-label="Ir para questão" value={page} onChange={e=>move(Number(e.target.value))}>{Array.from({length:query.data!.total},(_,i)=><option value={i+1} key={i+1}>{i+1}</option>)}</select></div><QuestionCard question={q} title={`Questão ${q.ordinal}`} selected={selected} eliminated={eliminated} cutting={cutting} onSelect={setSelected} onCut={cut}>{q.has_answer===false&&<p role="status" className="text-warning">Sem gabarito cadastrado; não é possível corrigir esta questão.</p>}{q.answered_at?<div className="qb-feedback" role="status"><strong className={q.correct?'text-success':'text-critical'}>{q.correct?'Você acertou.':'Você errou.'}</strong><span>Gabarito: {q.answer||'não disponível'}</span></div>:<button className="qb-primary" disabled={!selected||saving||cutting||!q.alternatives.length||q.has_answer===false} onClick={answer}>{saving?'Registrando…':'Responder'}</button>}</QuestionCard><div className="qb-navigation"><button className="qb-secondary" disabled={page<=1} onClick={()=>move(page-1)}><ChevronLeft size={18}/> Anterior</button><button className="qb-primary" disabled={page>=query.data!.total} onClick={()=>move(page+1)}>Próxima <ChevronRight size={18}/></button></div></>:<div className="tac-card">Esta lista está vazia.</div>}</div></AppLayout>
}
