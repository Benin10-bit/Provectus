import {useState} from 'react';
import {useMutation,useQueryClient} from '@tanstack/react-query';
import {toast} from 'sonner';
import {Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription,DialogTrigger} from '@/components/ui/dialog';
import {MateriaSelect,AssuntoSelect} from '@/components/form/Selectors';
import {studyPost} from '@/lib/study';
import {SessaoEstudoResponse,BlocoQuestoesResponse,SimuladoSemanalResponse} from '@/lib/types';
type RecordValue = SessaoEstudoResponse|BlocoQuestoesResponse|SimuladoSemanalResponse;
export default function RecordEditor({kind,value}:{kind:'sessoes'|'blocos'|'simulados';value:RecordValue}){
 const [open,setOpen]=useState(false);const qc=useQueryClient();
 const initial={...value} as Record<string,unknown>;const [data,setData]=useState(initial);
 const set=(key:string,val:unknown)=>setData(prev=>({...prev,[key]:val}));
 const save=useMutation({mutationFn:()=>studyPost(`${kind}/${value.id}`,data,'PUT'),onSuccess:()=>{qc.invalidateQueries();setOpen(false);toast.success('Registro corrigido. Estatísticas atualizadas.');},onError:(e:Error)=>toast.error(e.message)});
 const number=(key:string,label:string,min=0,max?:number)=><label className="text-sm block" key={key}>{label}<input required type="number" step="1" min={min} max={max} value={String(data[key]??'')} onChange={e=>set(key,Number(e.target.value))} className="form-input mt-1"/></label>;
 return <Dialog open={open} onOpenChange={v=>{setOpen(v);if(v)setData({...value});}}><DialogTrigger asChild><button className="text-xs text-accent underline">Editar</button></DialogTrigger><DialogContent className="max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>Corrigir registro</DialogTitle><DialogDescription>O identificador e o histórico do ciclo serão preservados. Sessão e bloco vinculados compartilham tempo e assunto.</DialogDescription></DialogHeader><form className="space-y-3" onSubmit={e=>{e.preventDefault();save.mutate();}}>
 {kind!=='simulados'&&<><MateriaSelect value={String(data.materia_id)} onChange={v=>{set('materia_id',v);set('assunto_id','');}}/><AssuntoSelect materiaId={String(data.materia_id)} value={String(data.assunto_id)} onChange={v=>set('assunto_id',v)}/><label className="text-sm block">Data e hora do estudo<input aria-label="Data e hora do estudo" className="form-input mt-1" type="datetime-local" required value={(()=>{const d=new Date(String(data.data||data.criado_em));return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);})()} onChange={e=>{if(e.target.value)set('data',new Date(e.target.value).toISOString());}}/></label></>}
 {kind==='sessoes'?<><label className="text-sm block">Tipo<select className="form-select mt-1" value={String(data.tipo_sessao)} onChange={e=>set('tipo_sessao',e.target.value)}><option>TEORIA</option><option>QUESTOES</option><option>REVISAO</option></select></label>{number('minutos_liquidos','Minutos líquidos',1)}</>:<>{number('total_questoes','Total de questões',1)}{number('total_acertos','Acertos',0,Number(data.total_questoes))}{number('tempo_total_segundos','Tempo total em segundos',1)}{kind==='blocos'?number('dificuldade','Dificuldade',1,5):<>{number('numero_ciclo','Número do ciclo',1)}{number('numero_semana','Semana',1,4)}</>}</>}
 <button className="btn-tactical" disabled={save.isPending}>{save.isPending?'Salvando...':'Salvar correção'}</button></form></DialogContent></Dialog>;
}
