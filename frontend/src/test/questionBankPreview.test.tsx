import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import QuestionBankPage from '@/pages/QuestionBankPage';
import { qb } from '@/lib/questionBank';
import { navGroups } from '@/components/layout/AppSidebar';
vi.mock('@/components/layout/AppLayout',()=>({default:({children}:{children:React.ReactNode})=><>{children}</>}));
vi.mock('@/lib/questionBank',async()=>{const actual=await vi.importActual<typeof import('@/lib/questionBank')>('@/lib/questionBank');return {...actual,qb:{...actual.qb,filters:vi.fn(),search:vi.fn(),library:vi.fn(),question:vi.fn()}};});
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('opens full rich question, returns to the same filtered page, and reveals answer only on request',async()=>{
 const hash='a'.repeat(64);
 const q={id:'q1',ordinal:1,numero_original:17,materia:'Física',content_path:['Mecânica'],banca_normalizada:'EsPCEx',dificuldade_normalizada:'MEDIA',enunciado:'Calcule [VISUAL] agora.',
  statement_segments:[{kind:'text' as const,text:'Calcule ',line_id:'1'},{kind:'visual' as const,asset_hash:hash,display:'inline' as const,line_id:'1'},{kind:'text' as const,text:' agora.',line_id:'1'}],
  assets:[{hash,url:`/api/v1/question-bank/assets/${hash}`,type:'FIGURE',alt:'Fórmula',mime_type:'image/webp'}],alternatives:[{letter:'A',ordinal:1,text:'Primeira alternativa',assets:[]}],answer:'A',selected:null,answered_at:null,correct:null,eliminated:[]};
 vi.mocked(qb.filters).mockResolvedValue({tree:[],banks:['EsPCEx'],difficulties:['MEDIA']});
 vi.mocked(qb.library).mockResolvedValue({folders:[],lists:[]});
 vi.mocked(qb.search).mockResolvedValue({total:25,items:[q]});vi.mocked(qb.question).mockResolvedValue(q);
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 render(<QueryClientProvider client={client}><MemoryRouter><QuestionBankPage/></MemoryRouter></QueryClientProvider>);
 await screen.findByText('25 questões encontradas');
 fireEvent.change(screen.getByPlaceholderText('Buscar no enunciado'),{target:{value:'Calcule'}});
 fireEvent.change(screen.getByLabelText('Banca'),{target:{value:'EsPCEx'}});
 await waitFor(()=>expect(screen.getByRole('button',{name:'Próxima'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Próxima'}));
 await waitFor(()=>expect(qb.search).toHaveBeenLastCalledWith(expect.objectContaining({search:'Calcule',banks:['EsPCEx']}),2));
 fireEvent.click(await screen.findByRole('button',{name:'Abrir questão'}));
 const dialog=await screen.findByRole('dialog');
 expect(await within(dialog).findByText('Primeira alternativa')).toBeInTheDocument();
 expect(within(dialog).getByText('Questão 17')).toBeInTheDocument();
 expect(within(dialog).queryByText(/\[VISUAL\]/)).toBeNull();
 expect(dialog.querySelectorAll('img')).toHaveLength(1);
 const details=within(dialog).getByText('Mostrar gabarito').closest('details')!;
 expect(details.open).toBe(false);fireEvent.click(within(dialog).getByText('Mostrar gabarito'));expect(details.open).toBe(true);
 fireEvent.click(within(dialog).getByRole('button',{name:'Voltar aos resultados'}));
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(screen.getByPlaceholderText('Buscar no enunciado')).toHaveValue('Calcule');
 expect(screen.getByLabelText('Banca')).toHaveValue('EsPCEx');
 expect(screen.getByText('Página 2')).toBeInTheDocument();
});

it('numbers every sidebar entry in order including question bank',()=>{
 const items=navGroups.flatMap(g=>g.items);
 expect(items.map(i=>i.code)).toEqual(items.map((_,i)=>String(i+1).padStart(2,'0')));
 expect(items.find(i=>i.to==='/banco-questoes')?.code).toBe('05');
 expect(items.some(i=>i.code==='BQ')).toBe(false);
});
