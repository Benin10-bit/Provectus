import { PeriodGoals } from './PeriodGoals';
import { ProgressRing, ValueChange } from "@/components/experience/StudyUI";
import {useQuery} from '@tanstack/react-query';
import {Link} from 'react-router-dom';
import {getWeek,goalsKey,goalVariant,duration,Advice,Guidance,Source} from '@/lib/goals';
import {request} from '@/lib/api';
import {ErrorState,LoadingState} from '@/components/ui/states';

export function SourceNote({source}:{source:Source}) {
 return <details className="text-xs text-muted-foreground mt-3"><summary className="cursor-pointer text-accent">Base científica e limite</summary><p className="mt-2"><a href={source.url} target="_blank" rel="noreferrer" className="underline">{source.titulo}</a> · {source.limite}</p></details>;
}
export function Method({activity}:{activity:string}) {
 const methods=useQuery({queryKey:['metodos'],queryFn:()=>request<Record<string,Guidance>>('/api/v1/metas/metodos'),staleTime:Infinity});
 const g=methods.data?.[activity];
 if(methods.isError)return <p className="text-xs text-muted-foreground">Orientação indisponível. Você pode continuar a sessão.</p>;
 return g?<details className="border border-border p-3 rounded-lg"><summary className="text-accent text-sm cursor-pointer">Como realizar esta atividade</summary><p className="font-semibold text-sm mt-3">{g.titulo}</p><ol className="list-decimal pl-5 text-sm space-y-1 mt-2">{g.passos.map(p=><li key={p}>{p}</li>)}</ol><SourceNote source={g.fonte}/></details>:null;
}
export function GoalBar({label,actual,target,status,format=String}:{label:string;actual:number;target:number;status:string;format?:(n:number)=>string}) {
 const color=status==='META ATINGIDA'?'text-success':status==='REAJUSTAR RITMO'?'text-warning':'text-muted-foreground';
 const fill=status==='META ATINGIDA'?'bg-success':status==='REAJUSTAR RITMO'?'bg-warning':'bg-accent';
 const percent=target>0?Math.min(100,Math.max(0,actual/target*100)):0;
 return <div className="goal-reading" data-tone={target>0?goalVariant(status):"default"} data-achieved={target>0&&actual>=target}>
   <div className="goal-top"><div><p className="micro-label">{label}</p><p className="goal-number"><ValueChange value={actual}>{format(actual)}</ValueChange></p><p className="goal-target">de {target>0?format(target):'sem meta'}</p></div><ProgressRing value={percent} label={label} caption={target>0?'da meta':'sem meta'}/></div>
   <div className="goal-track" role="progressbar" aria-label={label} aria-valuenow={Math.round(percent)} aria-valuemin={0} aria-valuemax={100}><div className={fill} style={{width:`${percent}%`}}/></div>
   <div className="goal-bottom"><p className={color}>{status}</p>{target>0&&<p className="goal-remaining">{actual>=target?'Meta concluída':`Faltam ${format(Math.max(0,target-actual))}`}</p>}</div>
 </div>;
}
export function WeeklyGoals() {
 const q=useQuery({queryKey:[...goalsKey,'semana'],queryFn:getWeek});
 if(q.isLoading)return <LoadingState message="Carregando metas da semana..."/>;
 if(q.isError)return <ErrorState message="Não foi possível carregar as metas."/>;
 const w=q.data!;const color=w.status_missao==='METAS DA SEMANA CONCLUÍDAS'?'border-success/40':['REPLANEJAR SEMANA','AJUSTAR PLANO','RETOMAR O RITMO'].includes(w.status_missao)?'border-warning/40':'border-accent/30';
 return <section className={`tac-card weekly-goals mb-6 ${color}`} aria-label="Metas desta semana"><div className="flex flex-wrap justify-between gap-3 mb-4"><div><h2 className="font-bold">Metas desta semana</h2><p className="text-xs text-muted-foreground mt-1">{w.inicio} a {w.fim} · {w.fuso}</p></div><Link className="text-accent text-sm underline" to="/metas">Ver plano e ajustar</Link></div><div className="weekly-goals-grid"><GoalBar label="Tempo líquido" actual={w.realizado.minutos} target={w.meta_minutos} status={w.status.horas} format={duration}/><GoalBar label="Questões" actual={w.realizado.questoes} target={w.meta_questoes} status={w.status.questoes}/><GoalBar label="Redações" actual={w.realizado.redacoes} target={w.meta_redacoes} status={w.status.redacoes}/></div><PeriodGoals week={w}/><details className="context-disclosure"><summary>Sobre as metas</summary><p>Cumprir as metas indica execução do plano, não domínio.</p></details><p className="text-xs text-muted-foreground mt-2">{w.parcial?'Primeira semana parcial: dias anteriores à ativação não criam metas; registros desta semana continuam contando.':''}</p></section>;
}
export function StudySuggestions() {
 const q=useQuery({queryKey:[...goalsKey,'orientacoes'],queryFn:()=>request<Advice[]>('/api/v1/metas/orientacoes')});
 if(q.isLoading)return <LoadingState message="Preparando sugestões..."/>;
 if(q.isError)return <ErrorState message="Não foi possível carregar as sugestões de estudo."/>;
 return <section className="mb-6"><h2 className="font-bold mb-3">Orientações para agora</h2><div className="grid sm:grid-cols-2 gap-4">{q.data?.map(a=><article className="tac-card" key={a.titulo}><h3 className="font-semibold text-accent">{a.titulo}</h3><p className="text-xs text-muted-foreground mt-2">{a.motivo}</p><ol className="list-decimal pl-5 text-sm space-y-1 my-3">{a.passos.map(p=><li key={p}>{p}</li>)}</ol><Link to={a.destino} className="text-sm underline text-accent">Ir para a ação</Link>{a.fonte?<SourceNote source={a.fonte}/>:<p className="text-xs text-muted-foreground mt-3">Regra de planejamento baseada no seu cronograma; não é uma dose científica.</p>}</article>)}</div></section>;
}
