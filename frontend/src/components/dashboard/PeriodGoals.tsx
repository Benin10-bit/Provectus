import { duration, periodGoals, type Week } from '@/lib/goals';
import { ValueChange } from '@/components/experience/StudyUI';

export function PeriodGoals({ week }: { week: Week }) {
 return <div className="period-goals">
  <div className="period-goals-grid">
   {(['mes', 'ano'] as const).map(period => {
    const goal = periodGoals(week, period);
    return <section key={period} className="period-goal-card" data-reactive-surface="subtle" aria-label={period === 'mes' ? 'Projeção mensal' : 'Projeção anual'}>
     <div className="period-goal-heading"><h3>{period === 'mes' ? 'Projeção mensal' : 'Projeção anual'}</h3><span>{period === 'mes' ? '4 × referência semanal' : '12 × mês'}</span></div>
     <dl className="period-goal-values">
      <div><dt>Tempo líquido</dt><dd>{goal.minutos==null?'Indisponível':<ValueChange value={goal.minutos}>{duration(goal.minutos)}</ValueChange>}</dd></div>
      <div><dt>Questões</dt><dd>{goal.questoes==null?'Indisponível':<ValueChange value={goal.questoes}>{goal.questoes.toLocaleString('pt-BR')}</ValueChange>}</dd></div>
      <div><dt>Redações</dt><dd>{goal.redacoes==null?'Indisponível':<ValueChange value={goal.redacoes}>{goal.redacoes.toLocaleString('pt-BR')}</ValueChange>}</dd></div>
     </dl>
    </section>;
   })}
  </div>
  <p className="period-goals-note">Projeções pela referência semanal persistida; ajustes excepcionais e semanas parciais não as alteram. Configurações para próximas semanas atualizam a referência na próxima segunda-feira.</p>
 </div>;
}
