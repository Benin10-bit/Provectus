import { ArrowUpRight, RotateCcw, CalendarDays } from "lucide-react";
import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Link} from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import {MateriaSelect} from '@/components/form/Selectors';
import {LoadingState,ErrorState,EmptyState} from '@/components/ui/states';
import {request} from '@/lib/api';
import {Activity,activityNames} from '@/lib/study';

interface Review {
 id:string;origem:'AUTOMATICA'|'PROGRAMADA';materia_id:string;materia:string;
 assunto_id:string;assunto:string;atividade:Activity;tarefa:string;motivo:string;
 prevista_em:string;disponivel:boolean;acao_id:string|null;referencia:string|null;
}

export default function ReviewPage(){
 const [materia,setMateria]=useState('');
 const q=useQuery({queryKey:['estudos','revisoes',materia],queryFn:()=>request<Review[]>(`/api/v1/estudos/revisoes${materia?`?materia_id=${materia}`:''}`)});
 const rows=q.data||[];
 const automatic=rows.filter(r=>r.origem==='AUTOMATICA'&&r.disponivel);
 const scheduled=rows.filter(r=>r.origem==='PROGRAMADA'&&r.disponivel);
 const future=rows.filter(r=>!r.disponivel);
 function card(r:Review){
  const params=new URLSearchParams({materia:r.materia_id,assunto:r.assunto_id,atividade:r.atividade,tarefa:r.tarefa});
  if(r.acao_id)params.set('acao',r.acao_id);
  return <article key={r.id} className="tac-card review-card space-y-3">
   <div className="review-card-meta"><span className="status-chip">{r.materia}</span><span className="status-chip neutral">{r.origem==='AUTOMATICA'?'Automática':'Programada'}</span></div><p className="micro-label">{activityNames[r.atividade]} · {r.disponivel?'Disponível agora':'Próximo retorno'}</p>
   <h3 className="text-base font-bold">{r.assunto}</h3>
   <p className="text-sm">{r.tarefa}</p>
   <div className="review-reason"><span className="micro-label">Por que retomar</span><p>{r.motivo}</p></div>
   {!r.disponivel&&<p className="text-xs text-muted-foreground">Retorno sugerido: {new Date(r.prevista_em).toLocaleDateString('pt-BR')}</p>}
   {r.referencia&&<p className="text-xs text-muted-foreground">Material: {r.referencia}</p>}
   <Link className="btn-tactical inline-flex items-center justify-center gap-2" to={`/estudar?${params}`}>{r.disponivel?'Preparar esta sessão':'Antecipar esta sessão'}<ArrowUpRight size={16}/></Link>
  </article>;
 }
 return <AppLayout>
  <div className="page-header"><h1 className="page-title">Lista de Revisão</h1></div>
  <div className="review-guide tac-card mb-6 space-y-3"><h2 className="font-bold">Próxima revisão</h2><p className="text-sm text-muted-foreground">Use a recomendação ou escolha uma revisão abaixo.</p><Link to="/estudar" className="text-accent underline text-sm">Estudar agora</Link></div>
  <div className="review-filter mb-5"><MateriaSelect value={materia} onChange={setMateria}/></div>
  {q.isLoading?<LoadingState/>:q.isError?<ErrorState message={(q.error as Error).message}/>:<><div className="review-lanes">
   <section className="review-lane"><header><RotateCcw size={18}/><h2>Retomadas automáticas</h2><span>{automatic.length}</span></header>
    {automatic.length?<div className="review-stack">{automatic.map(card)}</div>:<EmptyState message={rows.length?'Nenhum retorno automático disponível agora. Confira os próximos retornos abaixo ou avance pelo ciclo.':'Ainda não há histórico que justifique revisão. Comece um assunto em Estudar agora; assuntos nunca estudados ficam em Conteúdos.'}/>}</section>
   <section className="review-lane"><header><CalendarDays size={18}/><h2>Programadas por você</h2><span>{scheduled.length}</span></header>
    {scheduled.length?<div className="review-stack">{scheduled.map(card)}</div>:<p className="text-sm text-muted-foreground">Nenhuma ação manual disponível. Cadastrar ações é opcional.</p>}</section>
   </div>{future.length>0&&<details className="future-reviews tac-card mb-6"><summary className="text-sm text-accent cursor-pointer">Próximos retornos · {future.length}</summary><div className="grid lg:grid-cols-2 gap-4 mt-4">{future.map(card)}</div></details>}
  </>}
  <details className="context-disclosure"><summary>Sobre estes dados</summary><p className="text-xs text-muted-foreground">Sugestões não são dívidas. A fila é recalculada após novos registros: 1 dia para ampliar prática, 7 dias para verificar retenção e pelo menos 2 dias após revisão. São regras iniciais ajustáveis, não intervalos científicos personalizados. Baixa precisão considera duas tentativas recentes e ao menos 20 questões; contato antigo não prova esquecimento.</p></details>
 </AppLayout>;
}
