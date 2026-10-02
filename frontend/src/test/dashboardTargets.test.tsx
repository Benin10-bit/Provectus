import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import DashboardKpis from '@/components/dashboard/DashboardKpis';
import CardRecomendacao from '@/components/dashboard/CardRecomendacao';
import type { DashboardResumo } from '@/lib/types';
import { goalsKey, type Week } from '@/lib/goals';
const clients:QueryClient[]=[];
afterEach(()=>{cleanup();clients.forEach(c=>c.clear());clients.length=0;vi.unstubAllGlobals();});
const d={horas_liquidas:2,total_questoes:50,total_acertos:40,percentual_medio:80,tem_evidencia:true,tendencia:'ESTÁVEL',meta_horas:null,meta_questoes:null,status_horas:'SEM META DE PERÍODO',status_questoes:'SEM META DE PERÍODO',recomendacao:['Semana: 2h / 14h; 50 / 200 questões'],assuntos_criticos:[]} as DashboardResumo;
function client(){const c=new QueryClient({defaultOptions:{queries:{retry:false,staleTime:Infinity}}});clients.push(c);return c;}
it('renders period targets in the actual KPI cards even with legacy dashboard fields',async()=>{
 const c=client();c.setQueryData([...goalsKey,'semana'],{meta_minutos:840,meta_questoes:200,materias:[]} as unknown as Week);
 const renderCards=(period:'mes'|'ano'|'total')=><QueryClientProvider client={c}><DashboardKpis d={d} period={period}/></QueryClientProvider>;
 const view=render(renderCards('mes'));
 expect(screen.getByText('Horas Líquidas').closest('.kpi-card')?.querySelector('.kpi-target')).toHaveTextContent('56');
 expect(screen.getByText('Questões Resolvidas').closest('.kpi-card')?.querySelector('.kpi-target')).toHaveTextContent('800');
 view.rerender(renderCards('ano'));
 expect(screen.getByText('Horas Líquidas').closest('.kpi-card')?.querySelector('.kpi-target')).toHaveTextContent('672');
 expect(screen.getByText('Questões Resolvidas').closest('.kpi-card')?.querySelector('.kpi-target')).toHaveTextContent('9600');
 view.rerender(renderCards('total'));expect(document.querySelector('.kpi-target')).toBeNull();
});
it('legacy recommendations evaluate real aggregates without showing goal summaries',()=>{
 render(<CardRecomendacao d={d}/>);
 expect(screen.getByText(/80% de acertos/)).toBeInTheDocument();
 expect(screen.queryByText(/Semana: 2h/)).toBeNull();
 expect(screen.queryByRole('link')).toBeNull();
});
