import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import QuestionBankPage from '@/pages/QuestionBankPage';
import { qb } from '@/lib/questionBank';
vi.mock('@/components/layout/AppLayout',()=>({default:({children}:{children:React.ReactNode})=><>{children}</>}));
vi.mock('@/lib/questionBank',async()=>{const actual=await vi.importActual<typeof import('@/lib/questionBank')>('@/lib/questionBank');return {...actual,qb:{...actual.qb,availability:vi.fn(),preview:vi.fn(),filters:vi.fn(),search:vi.fn(),library:vi.fn(),create:vi.fn()}};});
afterEach(()=>{cleanup();vi.clearAllMocks();});
function setup(url='/banco-questoes'){
 vi.mocked(qb.filters).mockResolvedValue({tree:[],banks:['EsPCEx','ENEM','ITA'],difficulties:['FACIL','MEDIA','DIFICIL']});
 vi.mocked(qb.availability).mockResolvedValue({total:30,tree:[{name:'Física',path:['Física'],direct:false,available:30,children:[]}]});
 vi.mocked(qb.library).mockResolvedValue({folders:[],lists:[]});
 vi.mocked(qb.search).mockResolvedValue({total:30,items:[]});
 vi.mocked(qb.create).mockResolvedValue({id:'new-list'});
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[url]}><QuestionBankPage/></MemoryRouter></QueryClientProvider>);
 return client;
}
it('combines multiple banks and difficulties, excludes solved questions in search AND creation, resets page and clears filters',async()=>{
 setup();await screen.findByRole('checkbox',{name:'EsPCEx'});
 fireEvent.click(screen.getByRole('button',{name:'Próxima'}));
 await screen.findByText('Página 2');
 for(const name of ['EsPCEx','ENEM','FACIL','DIFICIL'])fireEvent.click(screen.getByRole('checkbox',{name}));
 fireEvent.click(screen.getByRole('checkbox',{name:/Excluir já respondidas/}));
 const selected={banks:['EsPCEx','ENEM'],difficulties:['FACIL','DIFICIL'],exclude_answered:true};
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining(selected),1));
 expect(screen.getByText('Página 1')).toBeInTheDocument();
 fireEvent.change(screen.getByPlaceholderText('Ex.: Cinemática — revisão'),{target:{value:'Prática nova'}});
 await waitFor(()=>expect(screen.getByRole('button',{name:'Criar lista'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Criar lista'}));
 await waitFor(()=>expect(qb.create).toHaveBeenCalledWith('Prática nova',20,null,expect.objectContaining(selected),expect.objectContaining({distribution:'auto'}),'shuffle'));
 fireEvent.click(screen.getByRole('button',{name:'Remover banca ENEM'}));
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({banks:['EsPCEx']}),1));
 expect(screen.getByRole('checkbox',{name:'ENEM'})).not.toBeChecked();
 fireEvent.click(screen.getByRole('button',{name:'Limpar filtros'}));
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({banks:[],difficulties:[],exclude_answered:false}),1));
});
it('restores multiple selections and exclusion from a saved URL and preserves each other selection when toggling',async()=>{
 const f={banks:['EsPCEx','ITA'],difficulties:['MEDIA','DIFICIL'],exclude_answered:true};
 setup('/banco-questoes?f='+encodeURIComponent(JSON.stringify(f))+'&page=2');
 await screen.findByRole('checkbox',{name:'EsPCEx'});
 for(const name of ['EsPCEx','ITA','MEDIA','DIFICIL'])expect(screen.getByRole('checkbox',{name})).toBeChecked();
 expect(screen.getByRole('checkbox',{name:/Excluir já respondidas/})).toBeChecked();
 expect(within(screen.getByRole('group',{name:'Bancas'})).getByText('2 selecionadas')).toBeInTheDocument();
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining(f),2));
 fireEvent.click(screen.getByRole('button',{name:'Remover dificuldade MEDIA'}));
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({...f,difficulties:['DIFICIL']}),1));
});

it('filters correct and incorrect attempts for search and creation without conflicting with unanswered selection',async()=>{
 setup();await screen.findByRole('checkbox',{name:'EsPCEx'});
 fireEvent.click(screen.getByRole('checkbox',{name:/Excluir já respondidas/}));
 fireEvent.change(screen.getByLabelText('Resultado'),{target:{value:'incorrect'}});
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({result:'incorrect',exclude_answered:false}),1));
 expect(screen.getByRole('checkbox',{name:/Excluir já respondidas/})).not.toBeChecked();
 fireEvent.change(screen.getByPlaceholderText('Ex.: Cinemática — revisão'),{target:{value:'Rever erros'}});
 await waitFor(()=>expect(screen.getByRole('button',{name:'Criar lista'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Criar lista'}));
 await waitFor(()=>expect(qb.create).toHaveBeenCalledWith('Rever erros',20,null,expect.objectContaining({result:'incorrect',exclude_answered:false}),expect.objectContaining({distribution:'auto'}),'shuffle'));
 fireEvent.change(screen.getByLabelText('Resultado'),{target:{value:'correct'}});
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({result:'correct'}),1));
 fireEvent.click(screen.getByRole('checkbox',{name:/Excluir já respondidas/}));
 expect(screen.getByLabelText('Resultado')).toHaveValue('all');
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({result:'all',exclude_answered:true}),1));
});

it('restores result selection from a saved URL and removes it with the chip',async()=>{
 setup('/banco-questoes?f='+encodeURIComponent(JSON.stringify({result:'incorrect',exclude_answered:true})));
 await screen.findByRole('checkbox',{name:'EsPCEx'});
 expect(screen.getByLabelText('Resultado')).toHaveValue('incorrect');
 expect(screen.getByRole('checkbox',{name:/Excluir já respondidas/})).not.toBeChecked();
 fireEvent.click(screen.getByRole('button',{name:'Remover filtro de resultado'}));
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({result:'all'}),1));
});
