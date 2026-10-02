import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import ExportPdfButton from '@/components/question-bank/ExportPdfButton';
import { downloadUrl } from '@/lib/questionBank';
import { toast } from 'sonner';
vi.mock('sonner',()=>({toast:{error:vi.fn()}}));
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});

it.each([['end','Gabarito somente ao final'],['after_each','Gabarito após cada questão']] as const)('exports selected answer placement %s',async(mode,label)=>{
 const fetchMock=vi.fn().mockResolvedValue(new Response(new Blob(['%PDF-test']),{headers:{'Content-Type':'application/pdf'}}));
 vi.stubGlobal('fetch',fetchMock);
 const create=vi.fn(()=> 'blob:pdf');Object.defineProperty(URL,'createObjectURL',{value:create,configurable:true});Object.defineProperty(URL,'revokeObjectURL',{value:vi.fn(),configurable:true});
 const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
 render(<ExportPdfButton listId="list1" name="Mecânica"/>);
 fireEvent.click(screen.getByRole('button',{name:'Baixar lista Mecânica'}));
 expect(screen.getAllByRole('radio')).toHaveLength(2);
 fireEvent.click(screen.getByRole('radio',{name:new RegExp(label)}));
 fireEvent.click(screen.getByRole('button',{name:'Gerar e baixar PDF'}));
 await waitFor(()=>expect(fetchMock).toHaveBeenCalledWith(downloadUrl('list1',mode)));
 await waitFor(()=>expect(click).toHaveBeenCalled());
 expect(screen.queryByRole('dialog')).toBeNull();
});

it('shows the API error instead of downloading an incomplete PDF',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'PDF não gerado: imagem ausente.'}),{status:422,headers:{'Content-Type':'application/json'}})));
 render(<ExportPdfButton listId="list1" name="Mecânica"/>);
 fireEvent.click(screen.getByRole('button',{name:'Baixar lista Mecânica'}));
 fireEvent.click(screen.getByRole('button',{name:'Gerar e baixar PDF'}));
 await waitFor(()=>expect(toast.error).toHaveBeenCalledWith('PDF não gerado: imagem ausente.'));
 expect(screen.getByRole('dialog')).toBeInTheDocument();
});
