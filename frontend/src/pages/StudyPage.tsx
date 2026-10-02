import { SectionHeading, ActionArrow } from "@/components/experience/StudyUI";
import {useEffect,useState} from 'react';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {Link,useSearchParams} from 'react-router-dom';
import {Play,Pause,Check,Target,RotateCcw} from 'lucide-react';
import {toast} from 'sonner';
import AppLayout from '@/components/layout/AppLayout';
import {MateriaSelect,AssuntoSelect} from '@/components/form/Selectors';
import {LoadingState,ErrorState} from '@/components/ui/states';
import {Method} from '@/components/dashboard/WeeklyGoals';
import {useMaterias} from '@/hooks/useConfiguracoes';
import {Activity,activityNames,Cycle,Draft,DRAFT_KEY,elapsedMs,getNow,loadDraft,studyPost} from '@/lib/study';

export default function StudyPage(){
 const qc=useQueryClient();const [params]=useSearchParams();
 const now=useQuery({queryKey:['estudos','agora'],queryFn:getNow});
 const [draft,setDraft]=useState<Draft|null>(loadDraft);
 const [manual,setManual]=useState(Boolean(params.get('assunto')));
 const [materia,setMateria]=useState(params.get('materia')||'');const [assunto,setAssunto]=useState(params.get('assunto')||'');
 const [activity,setActivity]=useState<Activity>((params.get('atividade') as Activity)||'TEORIA');
 useEffect(()=>{const sync=(e:StorageEvent)=>{if(e.key===DRAFT_KEY)setDraft(loadDraft());};window.addEventListener('storage',sync);return()=>window.removeEventListener('storage',sync);},[]);
 const saveDraft=(d:Draft|null)=>{try{if(d)localStorage.setItem(DRAFT_KEY,JSON.stringify(d));else localStorage.removeItem(DRAFT_KEY);setDraft(d);window.dispatchEvent(new Event('provectus:study-draft'));}catch{toast.error('Não foi possível guardar o rascunho neste navegador. Libere o armazenamento antes de começar.');}};
 const start=(m:string,a:string,t:Activity,task:string,action:string|null)=>{
  if(!m||!a){toast.error('Selecione matéria e assunto.');return;}
  if(task==='Estude o ponto escolhido no seu material.'&&a===params.get('assunto')&&t===params.get('atividade'))task=params.get('tarefa')||task;
  saveDraft({id:crypto.randomUUID(),materia_id:m,assunto_id:a,atividade:t,data:new Date().toISOString(),elapsed:0,runningSince:Date.now(),acao_id:action,tarefa:task,total:'',acertos:'',proximo:'',retomar:'',causa:'',resultado:'CONSEGUI'});
 };
 const n=now.data;
 return <AppLayout><div className="page-header"><h1 className="page-title">Estudar agora</h1></div>
 {draft?<ActiveSession draft={draft} change={saveDraft} done={()=>{saveDraft(null);qc.invalidateQueries();}}/>:<>
 {now.isLoading?<LoadingState/>:now.isError?<ErrorState message={(now.error as Error).message}/>:<>
 {n?.recomendacao&&<section className="study-decision tac-card">
  <div className="study-decision-main">
   <p className="page-eyebrow"><Target size={14}/> PRÓXIMA SESSÃO DO CICLO</p>
   <div className="decision-meta"><span className="status-chip">{n.recomendacao.materia}</span><span className="status-chip neutral">{activityNames[n.recomendacao.atividade]}</span></div>
   <h2>{n.recomendacao.assunto}</h2>
   <div className="decision-task"><span className="micro-label">O que fazer agora</span><p>{n.recomendacao.tarefa}</p></div>
   {n.recomendacao.referencia&&<p className="text-sm text-muted-foreground">Material: {n.recomendacao.referencia}</p>}
   <div className="decision-actions"><button className="btn-tactical inline-flex" onClick={()=>{const r=n.recomendacao!;start(r.materia_id,r.assunto_id,r.atividade,r.tarefa,r.acao_id);}}><Play size={16}/> Começar sessão <ActionArrow/></button><button className="text-sm text-accent underline" onClick={()=>setManual(!manual)}>Escolher outra</button></div>
  </div>
  <aside className="decision-reason">
   <div className="suggested-duration"><span className="micro-label">Tempo de referência</span>{n.recomendacao.duracao_sugerida_minutos?<p><strong>{n.recomendacao.duracao_sugerida_minutos}</strong><span>min líquidos</span></p>:<p className="text-sm">Sem meta de duração para agora.</p>}</div>
   <div><h3>Por que esta sessão?</h3><p>{n.recomendacao.explicacao}</p></div>
   {n.recomendacao.aviso&&<p className="context-note">{n.recomendacao.aviso}</p>}
   <Method activity={n.recomendacao.atividade}/>
  </aside>
 </section>}
 {n?.motivo&&<p className="tac-card mb-4 text-sm">{n.motivo} <Link className="text-accent underline" to="/conteudos">Organizar conteúdos</Link></p>}
 {(!n?.ciclo||n.ciclo.completo)&&<CycleSetup previous={n?.ciclo}/>}
 {n?.ciclo&&<><SectionHeading number="02" title="Seu ciclo" description="O saldo continua de onde você parou."/><CycleProgress cycle={n.ciclo}/></>}
 </>}
 <button className="text-sm text-accent underline mb-4" onClick={()=>setManual(!manual)}>{manual?'Fechar escolha manual':'Escolher matéria e atividade'}</button>
 {manual&&assunto===params.get('assunto')&&activity===params.get('atividade')&&params.get('tarefa')&&<p className="tac-card mb-4 text-sm">Sessão preparada: {params.get('tarefa')}</p>}
 {manual&&<div className="tac-card space-y-4"><h2 className="font-bold">Sua escolha também conta no ciclo</h2><MateriaSelect value={materia} onChange={v=>{setMateria(v);setAssunto('');}}/><AssuntoSelect materiaId={materia} value={assunto} onChange={setAssunto}/><label className="block text-sm">Atividade<select aria-label="Atividade" value={activity} onChange={e=>setActivity(e.target.value as Activity)} className="form-select mt-1">{Object.entries(activityNames).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><button className="btn-tactical inline-flex items-center justify-center gap-2" onClick={()=>start(materia,assunto,activity,'Estude o ponto escolhido no seu material.',assunto===params.get('assunto')?params.get('acao'):null)}><Play size={16}/> Começar esta sessão</button><p className="text-xs text-muted-foreground">O tempo real será contabilizado na matéria estudada. Não há dívida acumulada por dias sem estudo.</p></div>}
 </>}
 </AppLayout>;
}

function CycleSetup({previous}:{previous?:Cycle|null}){
 const {data:materias=[]}=useMaterias();const qc=useQueryClient();
 const [values,setValues]=useState<Record<string,string>>(()=>Object.fromEntries((previous?.metas||[]).map(g=>[g.materia_id,String(g.minutos/60)])));
 const save=useMutation({mutationFn:()=>studyPost('ciclo',{nome:'Meu ciclo',metas:materias.filter(m=>Number(values[m.id])>0).map(m=>({materia_id:m.id,minutos:Math.round(Number(values[m.id])*60)}))}),onSuccess:()=>{qc.invalidateQueries();toast.success('Ciclo iniciado. Seu histórico anterior foi preservado.');},onError:(e:Error)=>toast.error(e.message)});
 return <form className="tac-card mb-6 space-y-4" onSubmit={e=>{e.preventDefault();save.mutate();}}><h2 className="font-bold">{previous?'Próximo ciclo':'Cotas do seu ciclo'}</h2><p className="text-xs text-muted-foreground">Copie a quantidade de quadradinhos: 1 quadradinho = 1 hora. Deixe vazio o que não participa. A contagem começa agora, sem alterar seu histórico.</p><div className="grid sm:grid-cols-2 gap-3">{materias.map(m=><label key={m.id} className="text-sm">{m.nome} (horas)<input aria-label={`Cota de ${m.nome}`} type="number" step="0.25" min="0" max="1000" className="form-input mt-1" value={values[m.id]||''} onChange={e=>setValues({...values,[m.id]:e.target.value})}/></label>)}</div>{!materias.length?<Link className="text-accent underline" to="/conteudos">Cadastrar minhas matérias</Link>:<button className="btn-tactical inline-flex items-center justify-center gap-2" disabled={save.isPending||!Object.values(values).some(v=>Number(v)>0)}>{save.isPending?'Salvando...':previous?'Iniciar próximo ciclo':'Salvar cotas e começar'}</button>}</form>;
}
function CycleProgress({cycle}:{cycle:Cycle}){
 return <div className="tac-card cycle-progress mb-6"><h2 className="font-bold mb-3">Saldo do ciclo</h2><p className="text-xs text-muted-foreground mb-4">Frações de hora são preservadas. Cada quadrado representa 1h; o excedente permanece neste ciclo.</p><div className="space-y-4">{cycle.metas.map(g=><div key={g.materia_id}><div className="flex justify-between gap-2 text-sm mb-2"><span>{g.nome}</span><span className="font-mono">{(g.segundos_consumidos/3600).toFixed(2)} / {g.minutos/60}h</span></div><div className="flex gap-1 flex-wrap" aria-label={`${g.nome}: ${Math.round(g.proporcao*100)}% da cota`}>{Array.from({length:Math.min(100,Math.ceil(g.minutos/60))},(_,i)=>{const fill=Math.max(0,Math.min(1,g.segundos_consumidos/3600-i));return <span key={i} className="relative w-5 h-5 border border-accent/50 rounded-sm overflow-hidden bg-secondary"><span className="absolute left-0 top-0 bottom-0 bg-accent/80" style={{width:`${fill*100}%`}}/></span>;})}</div>{g.minutos>6000&&<p className="text-xs text-muted-foreground">Exibindo os primeiros 100 quadrados; o total acima inclui toda a cota.</p>}</div>)}</div></div>;
}
function ActiveSession({draft:d,change,done}:{draft:Draft;change:(d:Draft|null)=>void;done:()=>void}){
 const [,tick]=useState(0);const [confirmCancel,setConfirmCancel]=useState(false);
 useEffect(()=>{const t=setInterval(()=>tick(n=>n+1),500);return()=>clearInterval(t);},[]);
 const ms=elapsedMs(d);const seconds=Math.floor(ms/1000);const patch=(value:Partial<Draft>)=>change({...d,...value});
 const mutation=useMutation({mutationFn:()=>studyPost('concluir',{chave_registro:d.id,materia_id:d.materia_id,assunto_id:d.assunto_id,atividade:d.atividade,data:d.data,segundos:seconds,proximo_passo:d.proximo||null,
 bloco:d.total?{total_questoes:Number(d.total),total_acertos:Number(d.acertos),dificuldade:3}:null,
 acao_id:d.acao_id,resultado_acao:d.acao_id?d.resultado:null,
 nova_acao:d.retomar?{assunto_id:d.assunto_id,descricao:d.retomar,causa:d.causa||null}:null}),onSuccess:()=>{toast.success('Sessão salva. Tempo contado uma única vez.');done();},onError:(e:Error)=>toast.error(e.message)});
 const pause=()=>patch({elapsed:ms,runningSince:null});
 return <div className="tac-card active-study max-w-3xl mx-auto space-y-5" data-running={Boolean(d.runningSince)}><div className="focus-state" role="status"><span/>{d.runningSince?"Sessão em andamento":"Sessão pausada"}</div><h2 className="text-xl font-bold">{activityNames[d.atividade]} em andamento</h2><p className="text-sm text-muted-foreground">{d.tarefa}</p><p className="active-study-time" role="timer">{Math.floor(seconds/60).toString().padStart(2,'0')}:{(seconds%60).toString().padStart(2,'0')}</p><div className="flex justify-center gap-3"><button className="btn-tactical inline-flex items-center justify-center gap-2" disabled={mutation.isPending} onClick={()=>d.runningSince?pause():patch({runningSince:Date.now()})}>{d.runningSince?<><Pause size={16}/> Pausar</>:<><Play size={16}/> Retomar</>}</button></div><p className="text-xs text-muted-foreground">Rascunho salvo neste navegador. Ao voltar de uma pausa ou recarga, confira a duração antes de salvar.</p>
 <Method activity={d.atividade}/>
 {!d.runningSince&&<form onSubmit={e=>{e.preventDefault();mutation.mutate();}} className="space-y-4"><label className="block text-sm">Duração líquida (minutos; pode ajustar)<input aria-label="Duração líquida" className="form-input mt-1" type="number" min="0.02" max="1440" step="0.01" value={Math.round(d.elapsed/600)/100} onChange={e=>patch({elapsed:Number(e.target.value)*60000})}/></label><div className="grid grid-cols-2 gap-3"><label className="text-sm">Questões (opcional)<input aria-label="Questões da sessão" className="form-input mt-1" type="number" min="1" step="1" value={d.total} onChange={e=>patch({total:e.target.value})}/></label><label className="text-sm">Acertos<input aria-label="Acertos da sessão" className="form-input mt-1" required={Boolean(d.total)} type="number" min="0" max={Number(d.total)||undefined} step="1" value={d.acertos} onChange={e=>patch({acertos:e.target.value})}/></label></div>
 <label className="block text-sm">Onde continuar? (opcional)<input className="form-input mt-1" maxLength={300} value={d.proximo} onChange={e=>patch({proximo:e.target.value})} placeholder="Ex.: próximo exemplo da página 32"/></label>
 {d.acao_id&&<label className="block text-sm">Resultado da retomada<select className="form-select mt-1" value={d.resultado} onChange={e=>patch({resultado:e.target.value as Draft['resultado']})}><option value="CONSEGUI">Consegui realizar a ação</option><option value="REPETIR">Preciso retomar novamente (daqui a 2 dias)</option></select></label>}
 <details className="rounded-lg border border-border p-3"><summary className="text-sm cursor-pointer text-accent">Quero retomar um erro ou revisar depois</summary><label className="block text-sm mt-3">Ação concreta<input className="form-input mt-1" maxLength={300} value={d.retomar} onChange={e=>patch({retomar:e.target.value})} placeholder="Refazer a questão 12 sem consulta"/></label><label className="block text-sm mt-3">Causa conhecida (opcional)<select className="form-select mt-1" value={d.causa} onChange={e=>patch({causa:e.target.value})}><option value="">Não sei / revisão</option>{['CONCEITO','INTERPRETACAO','CALCULO','DISTRACAO','PRESSA','CONTEUDO_ESQUECIDO'].map(c=><option key={c}>{c}</option>)}</select></label></details>
 <button className="btn-tactical w-full inline-flex items-center justify-center gap-2" disabled={mutation.isPending||seconds<1}><Check size={16}/>{mutation.isPending?'Salvando...':'Concluir e registrar'}</button></form>}
 <button className="text-xs text-muted-foreground underline" disabled={mutation.isPending} onClick={()=>setConfirmCancel(!confirmCancel)}>Descartar rascunho</button>{confirmCancel&&<div className="border border-warning/40 rounded-lg p-3 text-sm"><p>Descartar esta sessão sem registrar tempo?</p><button className="text-warning underline mt-2" onClick={()=>change(null)}>Sim, descartar</button><button className="ml-4 underline" onClick={()=>setConfirmCancel(false)}>Continuar estudando</button></div>}
 </div>;
}
