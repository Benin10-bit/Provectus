import { expect, it } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { periodGoals, type Week } from '@/lib/goals';
import { PeriodGoals } from '@/components/dashboard/PeriodGoals';
it('projects the weekly targets with 4 and 48, including paused weeks', () => {
 const week = { meta_minutos: 840, meta_questoes: 200, meta_redacoes: 1 };
 expect(periodGoals(week, 'mes')).toEqual({minutos:3360, questoes:800, redacoes:4});
 expect(periodGoals(week, 'ano')).toEqual({minutos:40320, questoes:9600, redacoes:48});
 expect(periodGoals({meta_minutos:0,meta_questoes:0,meta_redacoes:0}, 'ano')).toEqual({minutos:0,questoes:0,redacoes:0});
});
it('updates displayed goals when the weekly plan changes', () => {
 const week = { meta_minutos:840, meta_questoes:200, meta_redacoes:1 } as Week;
 const view=render(<PeriodGoals week={week}/>);
 expect(screen.getByText('56h00')).toBeInTheDocument(); expect(screen.getByText('9.600')).toBeInTheDocument();
 view.rerender(<PeriodGoals week={{...week, meta_minutos:420,meta_questoes:100}}/>);
 expect(screen.getByText('28h00')).toBeInTheDocument();expect(screen.getByText('4.800')).toBeInTheDocument();cleanup();
});
