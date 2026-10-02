import { useRef, useState } from 'react';
import { Download, FileCheck2, ListChecks } from 'lucide-react';
import { toast } from 'sonner';
import { downloadUrl, type AnswerPlacement } from '@/lib/questionBank';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';

export default function ExportPdfButton({listId,name,compact=false}:{listId:string;name:string;compact?:boolean}) {
 const trigger=useRef<HTMLButtonElement>(null);
 const [open,setOpen]=useState(false),[placement,setPlacement]=useState<AnswerPlacement>('end'),[busy,setBusy]=useState(false);
 async function download(){
  setBusy(true);
  try {
   const response=await fetch(downloadUrl(listId,placement));
   if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(typeof error.detail==='string'?error.detail:'Não foi possível gerar o PDF.');}
   if(!response.headers.get('content-type')?.includes('application/pdf'))throw new Error('A API não retornou um PDF.');
   const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');
   link.href=url;link.download=`provectus-${name.replace(/[^\p{L}\p{N}_-]+/gu,'-')||'lista'}.pdf`;document.body.append(link);link.click();link.remove();
   window.setTimeout(()=>URL.revokeObjectURL(url),60000);setOpen(false);
  }catch(error){toast.error((error as Error).message);}finally{setBusy(false);}
 }
 return <><button ref={trigger} type="button" className={compact?'':'qb-secondary'} aria-label={`Baixar lista ${name}`} onClick={()=>setOpen(true)}><Download size={16}/>{!compact&&'Baixar PDF'}</button>
  <Dialog open={open} onOpenChange={value=>{if(!busy)setOpen(value);}}><DialogContent className="qb-page qb-export-dialog" onCloseAutoFocus={event=>{event.preventDefault();trigger.current?.focus();}}>
   <p className="micro-label">PROVECTUS / CADERNO DE QUESTÕES</p><DialogTitle>Exportar PDF</DialogTitle><DialogDescription>{name} — escolha onde consultar as respostas.</DialogDescription>
   <fieldset className="qb-export-options" disabled={busy}><legend className="sr-only">Posição do gabarito</legend>
    {([{value:'after_each',label:'Gabarito após cada questão',description:'Resposta logo após as alternativas.',icon:FileCheck2},{value:'end',label:'Gabarito somente ao final',description:'Resolva o caderno e confira a tabela final.',icon:ListChecks}] as const).map(option=><label className={placement===option.value?'selected':''} key={option.value}><input type="radio" name="answer-placement" value={option.value} checked={placement===option.value} onChange={()=>setPlacement(option.value)}/><option.icon size={22}/><span><strong>{option.label}</strong><small>{option.description}</small></span></label>)}
   </fieldset><button className="qb-primary" onClick={download} disabled={busy}><Download size={16}/>{busy?'Gerando PDF…':'Gerar e baixar PDF'}</button>
  </DialogContent></Dialog></>;
}
