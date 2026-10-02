import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { qb } from '@/lib/questionBank';
import QuestionListPage from '@/pages/QuestionListPage';
vi.mock('@/lib/questionBank',async importOriginal=>{const actual=await importOriginal<typeof import('@/lib/questionBank')>();return {...actual,qb:{...actual.qb,list:vi.fn(),answer:vi.fn(),eliminate:vi.fn()}}});
afterEach(()=>{cleanup();vi.clearAllMocks()});
const base={id:'l1',name:'Revisão de Física',total:1,items:[{id:'q1',ordinal:1,enunciado:'Qual a alternativa correta?',numero_original:1,materia:'Física',banca_normalizada:'EsPCEx',dificuldade_normalizada:'MEDIA',content_path:[],alternatives:[{letter:'A',ordinal:1,text:'Primeira',assets:[]},{letter:'B',ordinal:2,text:'Segunda',assets:[]}],assets:[],selected:null,answer:null,answered_at:null,correct:null,eliminated:[]}]};
it('cuts and restores choices, then reveals the correct answer after submission',async()=>{
 vi.mocked(qb.list).mockResolvedValue(base);
 vi.mocked(qb.eliminate).mockResolvedValue({eliminated:['A']});
 vi.mocked(qb.answer).mockResolvedValue({selected:'A',correct:false,answer:'B'});
 const c=new QueryClient({defaultOptions:{queries:{retry:false}}});
 render(<QueryClientProvider client={c}><MemoryRouter initialEntries={['/banco-questoes/listas/l1']}><Routes><Route path="/banco-questoes/listas/:id" element={<QuestionListPage/>}/></Routes></MemoryRouter></QueryClientProvider>);
 expect(await screen.findByText('Qual a alternativa correta?')).toBeInTheDocument();
 expect(screen.queryByText('Gabarito: B')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Cortar alternativa A'}));
 await waitFor(()=>expect(qb.eliminate).toHaveBeenCalledWith('l1','q1',['A']));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Restaurar alternativa A'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Restaurar alternativa A'}));
 await waitFor(()=>expect(qb.eliminate).toHaveBeenLastCalledWith('l1','q1',[]));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Selecionar alternativa A'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Selecionar alternativa A'}));
 fireEvent.click(screen.getByRole('button',{name:'Responder'}));
 expect(await screen.findByText('Gabarito: B')).toBeInTheDocument();
 expect(screen.getByText('Primeira').closest('.qb-alternative')).toHaveClass('wrong');
 expect(screen.getByText('Segunda').closest('.qb-alternative')).toHaveClass('right');
});

it('shows a legible question header and inline content without repeating the formula below', async () => {
 const hash='d'.repeat(64);
 const item={...base.items[0],materia:'portugues',banca_normalizada:'APMBB',dificuldade_normalizada:'FACIL',
  enunciado:'A expressão [VISUAL] completa a frase.',
  statement_segments:[{kind:'text' as const,text:'A expressão ',line_id:'line1'},
   {kind:'visual' as const,display:'inline' as const,asset_hash:hash,line_id:'line1'},
   {kind:'text' as const,text:' completa a frase.',line_id:'line1'}],
  assets:[{hash,url:`/api/v1/question-bank/assets/${hash}`,type:'STATEMENT_IMAGE',alt:'fórmula',mime_type:'image/webp'}]};
 vi.mocked(qb.list).mockResolvedValue({...base,items:[item]});
 const c=new QueryClient({defaultOptions:{queries:{retry:false}}});
 const {container}=render(<QueryClientProvider client={c}><MemoryRouter initialEntries={['/banco-questoes/listas/l1']}><Routes><Route path="/banco-questoes/listas/:id" element={<QuestionListPage/>}/></Routes></MemoryRouter></QueryClientProvider>);
 expect(await screen.findByText('Português')).toBeInTheDocument();
 expect([...container.querySelectorAll('.qb-question-meta span')].map(x=>x.textContent)).toEqual(['Português','APMBB','Fácil']);
 expect(container.querySelector('.qb-statement')?.textContent).toBe('A expressão  completa a frase.');
 expect(container.querySelectorAll('.qb-statement img')).toHaveLength(1);
 expect(container.querySelectorAll('.qb-images img')).toHaveLength(0);
});
