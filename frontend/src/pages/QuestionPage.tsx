import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useLocation, useParams } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import AppLayout from '@/components/layout/AppLayout';
import QuestionCard from '@/components/question-bank/QuestionCard';
import { qb } from '@/lib/questionBank';
import './questionBank.css';

type SearchContext = { returnTo?: string; resultIds?: string[] };

/** Full-page question practice from search, with a local, unsaved answer. */
export default function QuestionPage() {
 const {questionId=''}=useParams();
 const location=useLocation();
 const context=(location.state || {}) as SearchContext;
 const returnTo=context.returnTo?.match(/^\/banco-questoes(?:\?.*)?$/) ? context.returnTo : '/banco-questoes';
 const resultIds=Array.isArray(context.resultIds) ? context.resultIds : [];
 const position=resultIds.indexOf(questionId);
 const query=useQuery({queryKey:['qb','question',questionId],queryFn:()=>qb.question(questionId),enabled:!!questionId});
 const [selected,setSelected]=useState<string|null>(null);
 const [eliminated,setEliminated]=useState<string[]>([]);
 const [outcome,setOutcome]=useState<{selected:string;correct:boolean;answer:string}|null>(null);
 const [saving,setSaving]=useState(false);
 useEffect(()=>{setSelected(null);setEliminated([]);setOutcome(null);},[questionId]);
 async function answer(){
  if(!selected||!query.data||saving)return;
  setSaving(true);
  try {const response=await qb.check(questionId,selected);setOutcome(response);}
  catch(error){toast.error((error as Error).message);}
  finally{setSaving(false);}
 }
 const q=query.data;
 const displayed=q&&outcome?{...q,selected:outcome.selected,correct:outcome.correct,answer:outcome.answer,answered_at:new Date().toISOString()}:q;
 const nextContext={returnTo,resultIds};
 return <AppLayout><div className="qb-page qb-solve qb-individual">
  <div className="qb-heading"><div><Link to={returnTo} className="qb-back"><ArrowLeft size={16}/>Voltar aos resultados</Link><p className="micro-label">BANCO DE QUESTÕES / QUESTÃO AVULSA</p><h1>Resolver questão</h1></div></div>
  {query.isPending?<div className="tac-card" role="status">Carregando questão…</div>:query.isError?<div className="tac-card text-critical" role="alert">Não foi possível carregar a questão. <button type="button" className="qb-secondary" onClick={()=>query.refetch()}>Tentar novamente</button></div>:displayed&&<>
   {position>=0&&<div className="qb-progress"><span>Questão {position+1} de {resultIds.length} nesta página de resultados</span><div className="qb-progress-track"><div style={{width:`${(position+1)/resultIds.length*100}%`}}/></div></div>}
   <QuestionCard question={displayed} title={displayed.numero_original!=null?`Questão ${displayed.numero_original}`:'Questão'} selected={selected} eliminated={eliminated} onSelect={setSelected} onCut={letter=>setEliminated(v=>v.includes(letter)?v.filter(x=>x!==letter):[...v,letter])}>
    {q.has_answer===false&&<p role="status" className="text-warning">Sem gabarito cadastrado; não é possível corrigir esta questão.</p>}
    {outcome?<div className="qb-feedback" role="status"><strong className={outcome.correct?'text-success':'text-critical'}>{outcome.correct?'Você acertou.':'Você errou.'}</strong><span>Gabarito: {outcome.answer}</span></div>:<button className="qb-primary" disabled={!selected||saving||!q.alternatives.length||q.has_answer===false} onClick={answer}>{saving?'Conferindo…':'Responder'}</button>}
   </QuestionCard>
   <p className="qb-individual-note">Resposta avulsa: esta tentativa não entra no histórico das listas.</p>
   <div className="qb-navigation"><div>{position>0&&<Link className="qb-secondary" state={nextContext} to={`/banco-questoes/questoes/${encodeURIComponent(resultIds[position-1])}`}><ChevronLeft size={18}/>Anterior</Link>}</div><div>{position>=0&&position<resultIds.length-1&&<Link className="qb-primary" state={nextContext} to={`/banco-questoes/questoes/${encodeURIComponent(resultIds[position+1])}`}>Próxima<ChevronRight size={18}/></Link>}</div></div>
  </>}
 </div></AppLayout>;
}
