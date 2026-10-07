import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import QuestionBankPage from '@/pages/QuestionBankPage';
import QuestionPage from '@/pages/QuestionPage';
import { qb } from '@/lib/questionBank';
import { navGroups } from '@/components/layout/AppSidebar';
vi.mock('@/components/layout/AppLayout',()=>({default:({children}:{children:React.ReactNode})=><>{children}</>}));
vi.mock('@/lib/questionBank',async()=>{const actual=await vi.importActual<typeof import('@/lib/questionBank')>('@/lib/questionBank');return {...actual,qb:{...actual.qb,availability:vi.fn(),preview:vi.fn(),filters:vi.fn(),search:vi.fn(),library:vi.fn(),question:vi.fn(),check:vi.fn()}};});
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('opens a full page and answers without a list while preserving search filters and page',async()=>{
 const hash='a'.repeat(64);
 const q={id:'q1',ordinal:1,numero_original:17,materia:'Física',content_path:['Mecânica'],banca_normalizada:'EsPCEx',dificuldade_normalizada:'MEDIA',enunciado:'Calcule [VISUAL] agora.',
  statement_segments:[{kind:'text' as const,text:'Calcule ',line_id:'1'},{kind:'visual' as const,asset_hash:hash,display:'inline' as const,line_id:'1'},{kind:'text' as const,text:' agora.',line_id:'1'}],
  assets:[{hash,url:`/api/v1/question-bank/assets/${hash}`,type:'FIGURE',alt:'Fórmula',mime_type:'image/webp'}],alternatives:[{letter:'A',ordinal:1,text:'Primeira alternativa',assets:[]},{letter:'B',ordinal:2,text:'Segunda alternativa',assets:[]}],has_answer:true,selected:null,answered_at:null,correct:null,eliminated:[]};
 vi.mocked(qb.filters).mockResolvedValue({tree:[],banks:['EsPCEx'],difficulties:['MEDIA']});
 vi.mocked(qb.availability).mockResolvedValue({total:30,tree:[{name:'Física',path:['Física'],direct:false,available:30,children:[]}]});
 vi.mocked(qb.library).mockResolvedValue({folders:[],lists:[]});
 vi.mocked(qb.search).mockResolvedValue({total:25,items:[q]});vi.mocked(qb.question).mockResolvedValue(q);
 vi.mocked(qb.check).mockResolvedValue({selected:'A',correct:false,answer:'B'});
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/banco-questoes']}><Routes><Route path="/banco-questoes" element={<QuestionBankPage/>}/><Route path="/banco-questoes/questoes/:questionId" element={<QuestionPage/>}/></Routes></MemoryRouter></QueryClientProvider>);
 await screen.findByText('25 questões encontradas');
 fireEvent.change(screen.getByPlaceholderText('Buscar no enunciado'),{target:{value:'Calcule'}});
 fireEvent.click(screen.getByRole('checkbox',{name:'EsPCEx'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Próxima'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Próxima'}));
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({search:'Calcule',banks:['EsPCEx']}),2));
 fireEvent.click(await screen.findByRole('link',{name:'Abrir questão'}));
 expect(await screen.findByRole('heading',{name:'Resolver questão'})).toBeInTheDocument();
 expect(await screen.findByRole('heading',{name:'Questão 17'})).toBeInTheDocument();
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(screen.queryByText(/\[VISUAL\]/)).toBeNull();
 expect(document.querySelectorAll('.qb-statement img')).toHaveLength(1);
 expect(screen.getByText('Primeira alternativa')).toBeInTheDocument();
 expect(screen.queryByText('Gabarito: B')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Cortar alternativa B'}));
 expect(screen.getByRole('button',{name:'Restaurar alternativa B'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Selecionar alternativa A'}));
 fireEvent.click(screen.getByRole('button',{name:'Responder'}));
 expect(await screen.findByText('Gabarito: B')).toBeInTheDocument();
 expect(qb.check).toHaveBeenCalledWith('q1','A');
 fireEvent.click(screen.getByRole('link',{name:'Voltar aos resultados'}));
 expect(screen.getByPlaceholderText('Buscar no enunciado')).toHaveValue('Calcule');
 expect(screen.getByRole('checkbox',{name:'EsPCEx'})).toBeChecked();
 expect(screen.getByText('Página 2')).toBeInTheDocument();
});

it('opens a direct question URL without prior search and handles missing answer',async()=>{
 const item={id:'q1',ordinal:1,numero_original:17,materia:'Física',content_path:[],banca_normalizada:'EsPCEx',dificuldade_normalizada:'MEDIA',enunciado:'Enunciado',alternatives:[{letter:'A',ordinal:1,text:'Resposta',assets:[]}],assets:[],has_answer:false,selected:null,answered_at:null,correct:null,eliminated:[]};
 vi.mocked(qb.question).mockResolvedValue(item);
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/banco-questoes/questoes/q1']}><Routes><Route path="/banco-questoes/questoes/:questionId" element={<QuestionPage/>}/></Routes></MemoryRouter></QueryClientProvider>);
 expect(await screen.findByRole('heading',{name:'Questão 17'})).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Responder'})).toBeDisabled();
 expect(screen.getByRole('link',{name:'Voltar aos resultados'})).toHaveAttribute('href','/banco-questoes');
});

it('numbers every sidebar entry in order including question bank',()=>{
 const items=navGroups.flatMap(g=>g.items);
 expect(items.map(i=>i.code)).toEqual(items.map((_,i)=>String(i+1).padStart(2,'0')));
 expect(items.find(i=>i.to==='/banco-questoes')?.code).toBe('05');
 expect(items.some(i=>i.code==='BQ')).toBe(false);
});
