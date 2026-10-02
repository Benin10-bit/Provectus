import {useQuery} from '@tanstack/react-query';
import {Link} from 'react-router-dom';
import {getWeek,goalsKey,duration,Advice,Guidance,Source} from '@/lib/goals';
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
 return <div className="goal-reading min-w-0"><p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p><p className="font-mono text-xl mt-1">{format(actual)} <span className="text-sm text-muted-foreground">/ {target>0?format(target):'sem meta'}</span></p><div className="h-2 bg-secondary rounded-full my-2 overflow-hidden" role="progressbar" aria-label={label} aria-valuenow={Math.round(percent)} aria-valuemin={0} aria-valuemax={100}><div className={`h-full ${fill} transition-all`} style={{width:`${percent}%`}}/></div><p className={`text-xs ${color}`}>{status}</p></div>;
}
export function WeeklyGoals() {
 const q=useQuery({queryKey:[...goalsKey,'semana'],queryFn:getWeek});
 if(q.isLoading)return <LoadingState message="Carregando metas da semana..."/>;
 if(q.isError)return <ErrorState message="Não foi possível carregar as metas."/>;
 const w=q.data!;const color=w.status_missao==='METAS DA SEMANA CONCLUÍDAS'?'border-success/40':w.status_missao==='REPLANEJAR SEMANA'?'border-warning/40':'border-accent/30';
 return <section className={`tac-card weekly-goals mb-6 ${color}`} aria-label="Metas desta semana"><div className="flex flex-wrap justify-between gap-3 mb-4"><div><h2 className="font-bold">Metas desta semana</h2><p className="text-xs text-muted-foreground mt-1">{w.inicio} a {w.fim} · {w.fuso}</p></div><Link className="text-accent text-sm underline" to="/metas">Ver plano e ajustar</Link></div><div className="grid sm:grid-cols-3 gap-5"><GoalBar label="Tempo líquido" actual={w.realizado.minutos} target={w.meta_minutos} status={w.status.horas} format={duration}/><GoalBar label="Questões" actual={w.realizado.questoes} target={w.meta_questoes} status={w.status.questoes}/><GoalBar label="Redações" actual={w.realizado.redacoes} target={w.meta_redacoes} status={w.status.redacoes}/></div><p className="text-sm mt-4 text-accent">{w.status_missao}</p><p className="text-xs text-muted-foreground mt-2">Cumprir as metas indica execução do plano, não domínio. {w.parcial?'Primeira semana parcial: dias anteriores à ativação não criam metas; registros desta semana continuam contando.':''}</p></section>;
}
export function StudySuggestions() {
 const q=useQuery({queryKey:[...goalsKey,'orientacoes'],queryFn:()=>request<Advice[]>('/api/v1/metas/orientacoes')});
 if(q.isLoading)return <LoadingState message="Preparando sugestões..."/>;
 if(q.isError)return <ErrorState message="Não foi possível carregar as sugestões de estudo."/>;
 return <section className="mb-6"><h2 className="font-bold mb-3">Orientações para agora</h2><div className="grid sm:grid-cols-2 gap-4">{q.data?.map(a=><article className="tac-card" key={a.titulo}><h3 className="font-semibold text-accent">{a.titulo}</h3><p className="text-xs text-muted-foreground mt-2">{a.motivo}</p><ol className="list-decimal pl-5 text-sm space-y-1 my-3">{a.passos.map(p=><li key={p}>{p}</li>)}</ol><Link to={a.destino} className="text-sm underline text-accent">Ir para a ação</Link>{a.fonte?<SourceNote source={a.fonte}/>:<p className="text-xs text-muted-foreground mt-3">Regra de planejamento baseada no seu cronograma; não é uma dose científica.</p>}</article>)}</div></section>;
}
