import { useQuery } from '@tanstack/react-query';
import { Clock, ListChecks, Percent, TrendingUp } from 'lucide-react';
import { getWeek, goalsKey, goalVariant, type Week } from '@/lib/goals';
import { formatarHoras } from '@/lib/utils';
import type { DashboardResumo, Periodo } from '@/lib/types';
import KpiCard from './KpiCard';

export function kpiTargets(d: DashboardResumo, period: Periodo, week?: Week, materia = '') {
 if (period === 'total') return { hours: undefined, questions: undefined };
 const factor = period === 'mes' ? 4 : period === 'ano' ? 48 : 1;
 if (!week) return { hours: d.meta_horas ?? undefined, questions: d.meta_questoes ?? undefined };
 const minutes = materia ? week.materias.find(m=>m.materia_id===materia)?.meta_minutos : week.meta_minutos;
 return { hours: minutes == null ? undefined : minutes * factor / 60, questions: materia ? undefined : week.meta_questoes * factor };
}
export default function DashboardKpis({ d, period, materia = '' }: { d: DashboardResumo; period: Periodo; materia?: string }) {
 const week = useQuery({queryKey:[...goalsKey,'semana'],queryFn:getWeek});
 const targets=kpiTargets(d,period,week.data,materia);
 const status=(actual:number,target:number|undefined,original:string)=>period==='total'?'Sem meta para todo o histórico':target===0?'SEM META':target!=null&&period!=='semana'?(actual>=target?'META ATINGIDA':'EM ANDAMENTO'):original;
 const hoursStatus=status(d.horas_liquidas,targets.hours,d.status_horas);
 const questionsStatus=status(d.total_questoes,targets.questions,d.status_questoes);
 const variant=(s:string)=>s==='ACIMA'?'success':s==='ABAIXO'?'critical':s==='DENTRO'?'warning':goalVariant(s);
 return <div className="kpi-grid dashboard-kpis grid grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 stagger-children">
  <KpiCard title="Horas Líquidas" value={formatarHoras(d.horas_liquidas)} meta={targets.hours==null?undefined:formatarHoras(targets.hours)} icon={Clock} variant={variant(hoursStatus)} subtitle={hoursStatus}/>
  <KpiCard title="Questões Resolvidas" value={d.total_questoes} meta={targets.questions} icon={ListChecks} variant={variant(questionsStatus)} subtitle={questionsStatus}/>
  <KpiCard title="Precisão observada" value={d.tem_evidencia?`${d.percentual_medio}%`:'—'} icon={Percent} reference="Referência: ≥80%" variant={!d.tem_evidencia?'default':d.percentual_medio>=80?'success':d.percentual_medio>=70?'warning':'critical'} subtitle={d.tem_evidencia?`${d.total_acertos} acertos / ${d.total_questoes} questões`:'Sem questões no período'}/>
  <KpiCard title="Tendência" value={d.tendencia} icon={TrendingUp} variant={d.tendencia==='ASCENDENTE'?'success':d.tendencia==='DECLÍNIO'?'critical':'default'} detail={d.tendencia_contexto}/>
 </div>;
}
