import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { qb } from '@/lib/questionBank';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import QuestionCard from './QuestionCard';

export default function QuestionPreview({id,onClose,restoreFocus}:{id:string|null;onClose:()=>void;restoreFocus?:()=>void}) {
 const query=useQuery({queryKey:['qb','question',id],queryFn:()=>qb.question(id!),enabled:!!id,staleTime:300000});
 return <Dialog open={!!id} onOpenChange={open=>{if(!open)onClose();}}><DialogContent className="qb-page qb-preview-dialog" onCloseAutoFocus={event=>{if(restoreFocus){event.preventDefault();restoreFocus();}}}>
  <DialogTitle>Visualizar questão</DialogTitle><DialogDescription>Conteúdo integral da questão encontrada na busca.</DialogDescription>
  {query.isPending?<p role="status">Carregando questão…</p>:query.isError?<div role="alert"><p>Não foi possível abrir a questão.</p><button className="qb-secondary" onClick={()=>query.refetch()}>Tentar novamente</button></div>:query.data&&<QuestionCard question={query.data} title={query.data.numero_original!=null?`Questão ${query.data.numero_original}`:'Questão'}>
   <details className="qb-answer-details" key={id}><summary>Mostrar gabarito</summary><p>{query.data.answer?`Gabarito: ${query.data.answer}`:'Sem gabarito cadastrado.'}</p></details>
  </QuestionCard>}
  <button className="qb-secondary justify-self-start" onClick={onClose}><ArrowLeft size={16}/>Voltar aos resultados</button>
 </DialogContent></Dialog>;
}
