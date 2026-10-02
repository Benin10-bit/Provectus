import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import MissionStatus from '@/components/dashboard/MissionStatus';
import CardRecomendacao from '@/components/dashboard/CardRecomendacao';
import type { DashboardResumo, CriticalTopic } from '@/lib/types';
afterEach(cleanup);
const topic: CriticalTopic={assunto_id:'topic-1',assunto:'Cinemática',materia_id:'subject-1',materia:'Física',precisao:50,questoes:40,registros:2,tarefa:'Refazer erros',destino:'/estudar?materia=subject-1&assunto=topic-1&atividade=REVISAO'};
it('renders the critical subject and evidence without a catalog lookup',()=>{
 render(<MemoryRouter><MissionStatus status="NO RITMO" academic="ASSUNTOS EXIGEM ATENÇÃO" academicVariant="critical" tendencia="ESTÁVEL" assuntosCriticos={['topic-1']} details={[topic]}/></MemoryRouter>);
 expect(screen.getByText('Física')).toBeInTheDocument();expect(screen.getByText('Cinemática')).toBeInTheDocument();
 expect(screen.getByText(/50% · 40 questões · 2 registros/)).toBeInTheDocument();
 expect(screen.getByRole('link',{name:/Preparar revisão/})).toHaveAttribute('href',topic.destino);
});
it('shows only the first text recommendation and toggles the rest',()=>{
 const d={status_missao:'REFAZER HORÁRIOS',recomendacao:['resumo antigo'],recomendacoes_estudo:['Avalie os erros das suas 50 questões.','Reserve parte das 2 horas para verificar retenção.']} as DashboardResumo;
 render(<CardRecomendacao d={d}/>);
 expect(screen.getByText(d.recomendacoes_estudo![0])).toBeInTheDocument();
 expect(screen.queryByText(d.recomendacoes_estudo![1])).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Mostrar outras recomendações'}));
 expect(screen.getByText(d.recomendacoes_estudo![1])).toBeInTheDocument();
 expect(screen.queryByRole('link')).toBeNull();
 expect(screen.queryByText('resumo antigo')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Ocultar outras recomendações'}));
 expect(screen.queryByText(d.recomendacoes_estudo![1])).toBeNull();
});
it('distinguishes insufficient evidence in the empty critical area',()=>{
 render(<MemoryRouter><MissionStatus status="NO RITMO" tendencia="SEM PRÁTICA" assuntosCriticos={[]} details={[]} context="Amostra insuficiente por assunto neste período."/></MemoryRouter>);
 expect(screen.getByText('Amostra insuficiente por assunto neste período.')).toBeInTheDocument();
});
