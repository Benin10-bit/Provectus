import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import StudyPage from '@/pages/StudyPage';
import CoveragePage from '@/pages/CoveragePage';
import {DRAFT_KEY,completionData,loadDraft} from '@/lib/study';

const m='11111111-1111-4111-8111-111111111111',a='22222222-2222-4222-8222-222222222222';
const suggestion={materia_id:m,materia:'Física',assunto_id:a,assunto:'Capacitores',atividade:'QUESTOES',finalidade:'REVISAO',
 objetivo_revisao:'contato:origem',classe_revisao:'RECORRENTE',tarefa:'Tente recuperar uma solução sem consulta.',acao_id:null,referencia:null,
 explicacao:'Dificuldade observada em duas tentativas.',duracao_sugerida_minutos:15};
let current:unknown,posts:{url:string;body:Record<string,unknown>}[],clients:QueryClient[];
function mount(page=<StudyPage/>,path='/estudar'){
 const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0},mutations:{retry:false}}});clients.push(client);
 return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>{page}</MemoryRouter></QueryClientProvider>);
}
beforeEach(()=>{
 clients=[];posts=[];localStorage.clear();current={ciclo:null,recomendacao:suggestion,motivo:null};
 vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
  const url=String(input);let data:unknown=[];
  if(init?.method){posts.push({url,body:JSON.parse(String(init.body))});data={};}
  else if(url.includes('/estudos/agora'))data=current;
  else if(url.includes('/estudos/cobertura'))data=[{id:a,materia_id:m,nome:'Capacitores',ordem:0,estado:'SEM REGISTRO',familiaridade:'DESCONHECIDO',familiaridade_declarada:null,total_questoes:0,precisao:null,pendencias:[]}];
  else if(url.endsWith('/configuracoes/materias'))data=[{id:m,nome:'Física',peso_prova:1}];
  else if(url.includes('/configuracoes/materias/'))data=[{id:a,nome:'Capacitores',materia_id:m}];
  return {ok:true,headers:{get:()=> 'application/json'},json:async()=>data};
 }));
});
afterEach(()=>{cleanup();clients.forEach(c=>c.clear());vi.unstubAllGlobals();});

it('R01 T12 displays and accepts without creating study records; completion carries purpose',async()=>{
 mount();await screen.findByRole('heading',{name:'Capacitores'});
 expect(screen.getByText('Revisão · Questões')).toBeInTheDocument();expect(posts).toHaveLength(0);
 fireEvent.click(screen.getByRole('button',{name:'Começar sessão'}));
 const draft=loadDraft()!;
 expect(draft).toMatchObject({materia_id:m,assunto_id:a,finalidade:'REVISAO',objetivo_revisao:'contato:origem'});
 expect(draft.aceita_em).toBeTruthy();expect(draft.iniciada_em).toBeTruthy();expect(posts).toHaveLength(0);
 fireEvent.click(screen.getByRole('button',{name:'Pausar'}));
 fireEvent.change(screen.getByLabelText('Duração líquida'),{target:{value:'15'}});
 fireEvent.click(screen.getByRole('button',{name:'Concluir e registrar'}));
 await waitFor(()=>expect(posts).toHaveLength(1));
 expect(posts[0].body).toMatchObject({finalidade:'REVISAO',classe_revisao:'RECORRENTE',segundos:900,bloco:null});
});

it('R18 T11 reload resumes the same active draft without another write',async()=>{
 const first=mount();await screen.findByRole('heading',{name:'Capacitores'});
 fireEvent.click(screen.getByRole('button',{name:'Começar sessão'}));const id=loadDraft()!.id;
 first.unmount();mount();
 expect(screen.getByRole('status')).toHaveTextContent('Sessão em andamento');
 expect(screen.queryByRole('button',{name:'Começar sessão'})).not.toBeInTheDocument();
 expect(loadDraft()!.id).toBe(id);expect(posts).toHaveLength(0);
});

it('T05 Saturday empty state stays honest and allows optional time adjustment',async()=>{
 current={ciclo:null,recomendacao:null,motivo:'Sábado é revisional. Não há assunto conhecido.'};mount();
 await screen.findByText(/Sábado é revisional/);
 expect(screen.queryByRole('button',{name:'Começar sessão'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Minutos disponíveis agora'),{target:{value:'15'}});
 await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(([url])=>String(url).includes('/agora?minutos=15'))).toBe(true));
 expect(posts).toHaveLength(0);
});

it('R26 R34 familiarity declaration is optional and never posts a session',async()=>{
 mount(<CoveragePage/>,'/conteudos');await screen.findByRole('heading',{name:'Capacitores'});
 fireEvent.change(screen.getByLabelText('Contato prévio: Capacitores'),{target:{value:'ESTUDADO'}});
 await waitFor(()=>expect(posts).toHaveLength(1));
 expect(posts[0]).toEqual({url:`/api/api/v1/estudos/assuntos/${a}/familiaridade`,body:{declaracao:'ESTUDADO'}});
});

it('T15 old drafts remain valid without inventing a purpose',()=>{
 localStorage.setItem(DRAFT_KEY,JSON.stringify({id:'legacy',materia_id:m,assunto_id:a,atividade:'QUESTOES',data:'2026-09-21T12:00:00Z',elapsed:60000,runningSince:null,total:'',acertos:'',proximo:'',retomar:'',acao_id:null}));
 const payload=completionData(loadDraft()!,60);expect(payload).not.toHaveProperty('finalidade');
 expect(payload.bloco).toBeNull();expect(payload.segundos).toBe(60);
});

it('prepared question-based review preserves its purpose on manual start',async()=>{
 mount(<StudyPage/>,`/estudar?materia=${m}&assunto=${a}&atividade=QUESTOES&finalidade=REVISAO&objetivo=contato:origem&classe=MANUTENCAO`);
 await screen.findByRole('heading',{name:'Capacitores'});
 fireEvent.click(screen.getByRole('button',{name:'Começar esta sessão'}));
 expect(loadDraft()).toMatchObject({finalidade:'REVISAO',classe_revisao:'MANUTENCAO'});expect(posts).toHaveLength(0);
});
