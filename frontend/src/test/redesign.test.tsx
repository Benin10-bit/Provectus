import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import SessionForm from '@/pages/SessionForm';
import BlockForm from '@/pages/BlockForm';
import ExamForm from '@/pages/ExamForm';
import RedacaoForm from '@/pages/RedacaoForm';
import TimerPage from '@/pages/TimerPage';
import CoveragePage from '@/pages/CoveragePage';
import StudyPage from '@/pages/StudyPage';
import ReviewPage from '@/pages/ReviewPage';
import { DRAFT_KEY } from '@/lib/study';
import { GoalBar } from '@/components/dashboard/WeeklyGoals';
import { LoadingState } from '@/components/ui/states';
import KpiCard from '@/components/dashboard/KpiCard';
import { Clock } from 'lucide-react';
import type { ReactElement } from 'react';

// Isolated transport fixtures for regression testing. Production never imports these.
const materia = {id:'11111111-1111-4111-8111-111111111111',nome:'Matemática',peso_prova:1};
const assunto = {id:'22222222-2222-4222-8222-222222222222',nome:'Funções',materia_id:materia.id,semana_do_ciclo:1};
let posted: {url:string; body:Record<string,unknown>}[];
const clients: QueryClient[]=[];
function mount(node:ReactElement,path='/') {
 const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0},mutations:{retry:false}}}); clients.push(client);
 return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>{node}</MemoryRouter></QueryClientProvider>);
}
beforeEach(()=>{
 posted=[]; localStorage.removeItem(DRAFT_KEY);
 vi.stubGlobal('requestAnimationFrame',(cb:FrameRequestCallback)=>setTimeout(()=>cb(performance.now()),0));
 vi.stubGlobal('cancelAnimationFrame',(id:number)=>clearTimeout(id));
 vi.stubGlobal('fetch',vi.fn(async (input:RequestInfo|URL, init?:RequestInit)=>{
  const url=String(input); let value:unknown=[];
  if(init?.method==='POST') {const body=JSON.parse(String(init.body));posted.push({url,body}); value={id:'saved',percentual_acerto:75,nota_total:800,status:'boa',...body};}
  else if(url.endsWith('/configuracoes/materias'))value=[materia];
  else if(url.includes('/configuracoes/materias/'))value=[assunto];
  else if(url.endsWith('/estudos/agora'))value={ciclo:null,motivo:null,recomendacao:{materia_id:materia.id,materia:materia.nome,assunto_id:assunto.id,assunto:assunto.nome,atividade:'TEORIA',tarefa:'Estudar o exemplo do material.',referencia:null,acao_id:null,explicacao:'Saldo do ciclo.',duracao_sugerida_minutos:30}};
  else if(url.includes('/estudos/revisoes'))value=[{id:'r1',origem:'AUTOMATICA',materia_id:materia.id,materia:materia.nome,assunto_id:assunto.id,assunto:assunto.nome,atividade:'REVISAO',tarefa:'Rever o exemplo.',motivo:'Retomar o assunto.',prevista_em:'2026-09-21T12:00:00Z',disponivel:true,acao_id:null,referencia:null}];
  else if(url.includes('/estudos/cobertura'))value=[{...assunto,ordem:1,referencia:null,estado:'SEM REGISTRO',ultimo_contato:null,total_questoes:0,questoes_recentes:0,blocos_recentes:0,precisao:null,pendencias:[]}];
  return {ok:true,headers:{get:()=> 'application/json'},json:async()=>value};
 }));
});
afterEach(()=>{cleanup();clients.splice(0).forEach(c=>c.clear());vi.unstubAllGlobals();});
async function selectTopic() {
 await screen.findByRole('option',{name:'Matemática'});
 fireEvent.change(screen.getByLabelText('Matéria'),{target:{value:materia.id}});
 await screen.findByRole('option',{name:'Funções'});
 fireEvent.change(screen.getByLabelText('Assunto'),{target:{value:assunto.id}});
}
const fill=(label:string,value:string)=>fireEvent.change(screen.getByLabelText(label,{exact:true}),{target:{value}});

describe('Redesign preserves study workflows',()=>{
 it('submits the original session payload and clears the form after success',async()=>{
  mount(<SessionForm/>,'/sessao'); await selectTopic();fill('Minutos Líquidos','45');
  fireEvent.click(screen.getByRole('button',{name:'Revisão'}));
  fireEvent.click(screen.getByRole('button',{name:'Registrar Sessão'}));
  await waitFor(()=>expect(posted).toHaveLength(1));
  expect(posted[0]).toEqual({url:'/api/api/v1/performance/sessoes',body:{materia_id:materia.id,assunto_id:assunto.id,tipo_sessao:'REVISAO',minutos_liquidos:45,nivel_foco:null,nivel_energia:null}});
  await waitFor(()=>expect(screen.getByLabelText('Minutos Líquidos')).toHaveValue(null));
 });
 it('preserves block duration conversion and optional confidence',async()=>{
  mount(<BlockForm/>,'/bloco');await selectTopic();fill('Total de Questões','20');fill('Total de Acertos','15');fill('Tempo Total (minutos)','30');
  fireEvent.click(screen.getByRole('button',{name:'Registrar Bloco'}));
  await waitFor(()=>expect(posted).toHaveLength(1));
  expect(posted[0].url).toBe('/api/api/v1/performance/blocos');
  expect(posted[0].body).toMatchObject({total_questoes:20,total_acertos:15,tempo_total_segundos:1800,nivel_confianca_medio:null});
  expect(await screen.findByText('75% de acerto')).toBeInTheDocument();
 });
 it('preserves simulated-exam submission and does not invent optional ratings',async()=>{
  mount(<ExamForm/>,'/simulado');fill('Número do Ciclo','2');fill('Número da Semana','3');fill('Total de Questões','60');fill('Total de Acertos','45');fill('Tempo Total (minutos)','180');
  fireEvent.click(screen.getByRole('button',{name:'Registrar Simulado'}));await waitFor(()=>expect(posted).toHaveLength(1));
  expect(posted[0].body).toMatchObject({numero_ciclo:2,numero_semana:3,total_questoes:60,total_acertos:45,tempo_total_segundos:10800,nivel_ansiedade:null,nivel_fadiga:null,qualidade_sono:null});
 });
 it('keeps the essay inputs mounted and submits existing competency fields',async()=>{
  mount(<RedacaoForm/>,'/redacoes/nova');fill('Tema da Redação *','Tema de teste');fill('Tempo de Escrita (min)','90');
  const scores=screen.getAllByRole('spinbutton').filter(e=>e.getAttribute('max')==='200');expect(scores).toHaveLength(5);
  scores.forEach(el=>fireEvent.change(el,{target:{value:'160'}}));fireEvent.click(screen.getByRole('button',{name:'Enviar Redação'}));
  await waitFor(()=>expect(posted).toHaveLength(1));expect(posted[0].body).toMatchObject({tema:'Tema de teste',tempo_escrita_min:90,competencia1:160,competencia5:160});
 });
 it('catalog disclosure keeps all topic actions and the original status filter',async()=>{
  const {container}=mount(<CoveragePage/>,'/conteudos');await screen.findByRole('heading',{name:'Funções'});
  const group=container.querySelector('details.subject-group');expect(group).toHaveAttribute('open');
  const action=within(group as HTMLElement).getByRole('link',{name:'Estudar este assunto'});expect(action.getAttribute('href')).toContain('atividade=TEORIA');
  fill('Filtrar cobertura','PRÁTICA REGISTRADA');expect(await screen.findByText('Nenhum assunto neste filtro. Escolha Todos para ver a cobertura.')).toBeInTheDocument();
  fill('Filtrar cobertura','TODOS');expect(await screen.findByRole('heading',{name:'Funções'})).toBeInTheDocument();
 });
 it('timer start, pause, presets and mode switching still respond',()=>{
  mount(<TimerPage/>,'/timer');fireEvent.click(screen.getByRole('button',{name:'25:00'}));expect(screen.getByText('25:00',{selector:'span'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Iniciar'}));expect(screen.getByRole('status')).toHaveTextContent('Foco em andamento');
  fireEvent.click(screen.getByRole('button',{name:'Pausar'}));expect(screen.getByRole('button',{name:'Iniciar'})).toBeEnabled();
  fireEvent.click(screen.getByRole('button',{name:'Cronômetro'}));expect(screen.getByText('00:00')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Tela cheia'}));expect(screen.getByRole('button',{name:'Sair da tela cheia'})).toBeInTheDocument();
 });
 it('keeps the recommended study action and records a paused session',async()=>{
  mount(<StudyPage/>,'/estudar');await screen.findByRole('heading',{name:'Funções'});
  fireEvent.click(screen.getByRole('button',{name:'Começar sessão'}));
  expect(screen.getByRole('status')).toHaveTextContent('Sessão em andamento');
  expect(JSON.parse(localStorage.getItem(DRAFT_KEY)!)).toMatchObject({materia_id:materia.id,assunto_id:assunto.id,atividade:'TEORIA'});
  fireEvent.click(screen.getByRole('button',{name:'Pausar'}));fill('Duração líquida','12');
  fireEvent.click(screen.getByRole('button',{name:'Concluir e registrar'}));await waitFor(()=>expect(posted).toHaveLength(1));
  expect(posted[0].url).toBe('/api/api/v1/estudos/concluir');expect(posted[0].body).toMatchObject({segundos:720,materia_id:materia.id,assunto_id:assunto.id,atividade:'TEORIA'});
  await waitFor(()=>expect(localStorage.getItem(DRAFT_KEY)).toBeNull());
 });
 it('review card preserves the prepared-session URL and explains the origin',async()=>{
  mount(<ReviewPage/>,'/revisao');const action=await screen.findByRole('link',{name:'Preparar esta sessão'});
  const href=action.getAttribute('href')!;expect(href).toContain(`materia=${materia.id}`);expect(href).toContain(`assunto=${assunto.id}`);expect(href).toContain('atividade=REVISAO');expect(screen.getByText('Automática')).toBeInTheDocument();expect(screen.getByText('Retomar o assunto.')).toBeInTheDocument();
 });
 it('shows the precise remaining target and handles absent/overshot targets',()=>{
  const {rerender}=render(<GoalBar label="Questões" actual={100} target={200} status="EM ANDAMENTO"/>);
  expect(screen.getByText('Faltam 100')).toBeInTheDocument();expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','50');
  rerender(<GoalBar label="Questões" actual={250} target={200} status="META ATINGIDA"/>);expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','100');expect(screen.getByText('250')).toBeInTheDocument();
  rerender(<GoalBar label="Questões" actual={0} target={0} status="SEM META"/>);expect(screen.queryByText(/Faltam/)).not.toBeInTheDocument();
 });
 it('keeps compound and decimal KPI formatting intact',()=>{
  const {rerender}=render(<KpiCard title="Tempo" value="14h30min" icon={Clock}/>);expect(screen.getByText('14h30min')).toBeInTheDocument();
  rerender(<KpiCard title="Precisão" value="78,25%" icon={Clock}/>);expect(screen.getByText('78,25%')).toBeInTheDocument();
 });
 it('announces skeleton loading instead of presenting invented values',()=>{
  render(<LoadingState message="Carregando metas"/>);expect(screen.getByRole('status')).toHaveAttribute('aria-busy','true');expect(screen.getByRole('status')).toHaveAccessibleName('Carregando metas');expect(screen.queryByText(/%/)).not.toBeInTheDocument();
 });
});
