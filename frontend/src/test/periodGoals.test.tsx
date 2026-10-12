import { afterEach, expect, it } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { periodGoals, type Week, type Projection } from '@/lib/goals';
import { PeriodGoals } from '@/components/dashboard/PeriodGoals';
afterEach(cleanup);
const projection=(minutos:number,questoes:number,redacoes:number):Projection=>({minutos,questoes,redacoes,contexto:'Referência persistida',natureza:'PROJECAO_DE_PLANEJAMENTO',referencia:null});
const week={meta_minutos:1500,meta_questoes:200,meta_redacoes:1,projecoes:{mes:projection(6000,800,4),ano:projection(72000,9600,48)}} as Week;
it('consumes the server projections without recalculating from a paused week',()=>{
 expect(periodGoals(week,'mes').minutos).toBe(6000);
 expect(periodGoals({...week,meta_minutos:0,meta_questoes:0} as Week,'ano').questoes).toBe(9600);
});
it('keeps visible projections stable through an exceptional weekly reduction',()=>{
 const view=render(<PeriodGoals week={week}/>);
 expect(screen.getByText('100h00')).toBeInTheDocument();expect(screen.getByText('9.600')).toBeInTheDocument();
 view.rerender(<PeriodGoals week={{...week,meta_minutos:750,meta_questoes:100}}/>);
 expect(screen.getByText('100h00')).toBeInTheDocument();expect(screen.getByText('9.600')).toBeInTheDocument();
});
it('shows unavailable projections instead of fabricating from an older API',()=>{
 render(<PeriodGoals week={{meta_minutos:840,meta_questoes:200} as Week}/>);
 expect(screen.getAllByText('Indisponível')).toHaveLength(6);
 expect(screen.queryByText('56h00')).toBeNull();
});
