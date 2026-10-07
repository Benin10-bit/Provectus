import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ListComposer from '@/components/question-bank/ListComposer';
import { qb, type AvailableNode, type CompositionNode, type CompositionPreview, type Filters } from '@/lib/questionBank';
import { ApiError } from '@/lib/api';
vi.mock('@/lib/questionBank',async()=>{const actual=await vi.importActual<typeof import('@/lib/questionBank')>('@/lib/questionBank');return {...actual,qb:{...actual.qb,availability:vi.fn(),preview:vi.fn(),create:vi.fn()}};});
afterEach(()=>{cleanup();vi.clearAllMocks();});
const leaf=(path:string[],available:number):AvailableNode=>({path,name:path.at(-1)!,available,direct:false,children:[]});
const geometry={...leaf(['Matemática','Geometria'],12),children:[leaf(['Matemática','Geometria','Plana'],12)]};
const math={...leaf(['Matemática'],32),children:[geometry,leaf(['Matemática','Funções'],20)]};
const portuguese={...leaf(['Português'],23),children:[leaf(['Português','Regência'],18),leaf(['Português','Crase'],5)]};
const filters:Filters={paths:[],banks:[],difficulties:[],search:'',exclude_answered:false,result:'all'};
const resolvedNode=(path:string[],quantity:number,children:CompositionNode[]=[]):CompositionNode=>({path,quantity,distribution:'manual',children,direct:false});
const previewValue:CompositionPreview={total:20,seed:'confirmed',groups:[],resolved:{distribution:'manual',seed:'confirmed',nodes:[resolvedNode(['Matemática'],12,[resolvedNode(['Matemática','Geometria'],7,[resolvedNode(['Matemática','Geometria','Plana'],7)]),resolvedNode(['Matemática','Funções'],5)]),resolvedNode(['Português'],8,[resolvedNode(['Português','Regência'],5),resolvedNode(['Português','Crase'],3)])]}};
function setup(initial=filters){
 vi.mocked(qb.availability).mockResolvedValue({tree:[math,portuguese],total:55});
 vi.mocked(qb.preview).mockResolvedValue(previewValue);vi.mocked(qb.create).mockResolvedValue({id:'list'});
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 const wrapper=({value}:{value:Filters})=><QueryClientProvider client={client}><MemoryRouter><ListComposer filters={value} folders={[]} folderLabel={id=>id}/></MemoryRouter></QueryClientProvider>;
 const result=render(wrapper({value:initial}));
 return {client,rerender:(value:Filters)=>result.rerender(wrapper({value}))};
}
async function named(){await screen.findByRole('checkbox',{name:'Incluir Matemática'});fireEvent.change(screen.getByPlaceholderText('Ex.: Cinemática — revisão'),{target:{value:'Minha prática'}});await waitFor(()=>expect(screen.getByRole('button',{name:'Criar lista'})).toBeEnabled());}
function personalize(){fireEvent.click(screen.getByRole('button',{name:'Personalizar composição'}));fireEvent.change(screen.getByLabelText('Distribuição entre matérias'),{target:{value:'manual'}});}

it('starts compact, previews a random composition and creates with the exact confirmed quotas',async()=>{
 setup();await named();expect(screen.queryByLabelText('Distribuição entre matérias')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Sortear distribuição'}));
 await screen.findByText('20 / 20 distribuídas · Pronto para criar');
 fireEvent.change(screen.getByLabelText('Ordem da lista'),{target:{value:'grouped'}});
 fireEvent.click(screen.getByRole('button',{name:'Criar lista'}));
 await waitFor(()=>expect(qb.create).toHaveBeenCalledWith('Minha prática',20,null,filters,previewValue.resolved,'grouped'));
});

it('creates exactly four Geometry and five Regency questions, with recursive controls and total validation',async()=>{
 setup();await named();fireEvent.change(screen.getByLabelText('Total de questões'),{target:{value:'9'}});personalize();
 fireEvent.change(screen.getByLabelText('Quantidade de Matemática'),{target:{value:'4'}});
 fireEvent.change(screen.getByLabelText('Quantidade de Português'),{target:{value:'5'}});
 fireEvent.click(screen.getByRole('button',{name:'Expandir Matemática'}));
 fireEvent.change(screen.getByLabelText('Distribuição em Matemática'),{target:{value:'manual'}});
 expect(screen.getByRole('button',{name:'Criar lista'})).toBeDisabled();
 fireEvent.change(screen.getByLabelText('Quantidade de Matemática › Geometria'),{target:{value:'4'}});
 fireEvent.click(screen.getByRole('button',{name:'Expandir Matemática › Geometria'}));
 expect(screen.getByRole('checkbox',{name:'Incluir Matemática › Geometria › Plana'})).toBeChecked();
 fireEvent.click(screen.getByRole('button',{name:'Expandir Português'}));
 fireEvent.change(screen.getByLabelText('Distribuição em Português'),{target:{value:'manual'}});
 fireEvent.change(screen.getByLabelText('Quantidade de Português › Regência'),{target:{value:'5'}});
 expect(screen.getByRole('button',{name:'Criar lista'})).toBeEnabled();
 fireEvent.click(screen.getByRole('checkbox',{name:'Incluir Matemática › Geometria › Plana'}));
 expect(screen.getByRole('button',{name:'Criar lista'})).toBeDisabled();
 fireEvent.click(screen.getByRole('checkbox',{name:'Incluir Matemática › Geometria › Plana'}));
 expect(screen.getByRole('button',{name:'Criar lista'})).toBeEnabled();
 fireEvent.change(screen.getByLabelText('Quantidade de Português'),{target:{value:'4'}});
 expect(screen.getByRole('button',{name:'Criar lista'})).toBeDisabled();
 expect(screen.getByText('5 / 4 distribuídas · 1 excedentes')).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Quantidade de Português'),{target:{value:'5'}});
 fireEvent.click(screen.getByRole('button',{name:'Criar lista'}));
 await waitFor(()=>expect(qb.create).toHaveBeenCalledWith('Minha prática',9,null,filters,expect.objectContaining({distribution:'manual',nodes:expect.arrayContaining([expect.objectContaining({path:['Matemática'],quantity:4}),expect.objectContaining({path:['Português'],quantity:5})])}),'shuffle'));
});

it('supports a fixed subject and an AUTO remainder independently from content distribution',async()=>{
 setup();await named();fireEvent.change(screen.getByLabelText('Total de questões'),{target:{value:'15'}});personalize();
 fireEvent.change(screen.getByLabelText('Quantidade de Português'),{target:{value:'5'}});
 fireEvent.click(screen.getByRole('button',{name:'Usar quantidade automática em Matemática'}));
 expect(screen.getByText('5 fixadas · 10 para distribuição automática')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Criar lista'}));
 await waitFor(()=>expect(qb.create).toHaveBeenCalledWith('Minha prática',15,null,filters,expect.objectContaining({distribution:'manual',nodes:expect.arrayContaining([expect.objectContaining({path:['Matemática'],quantity:null}),expect.objectContaining({path:['Português'],quantity:5})])}),'shuffle'));
});

it('recalculates capacity on filter changes, prevents impossible totals and reports structured backend errors',async()=>{
 const {rerender}=setup();await named();
 vi.mocked(qb.availability).mockResolvedValue({tree:[{...math,available:3,children:[{...geometry,available:3,children:[leaf(['Matemática','Geometria','Plana'],3)]},leaf(['Matemática','Funções'],0)]},{...portuguese,available:0,children:portuguese.children.map(n=>({...n,available:0}))}],total:3});
 const next={...filters,banks:['ITA'],exclude_answered:true};rerender(next);
 await waitFor(()=>expect(qb.availability).toHaveBeenLastCalledWith(next));
 await screen.findByText(/Existem apenas 3 questões elegíveis/);
 expect(screen.getByRole('button',{name:'Criar lista'})).toBeDisabled();
 fireEvent.change(screen.getByLabelText('Total de questões'),{target:{value:'2'}});
 // The former Portuguese selection is now missing from this fake catalog: remove it
 // by refetching a catalog that retains its real zero-capacity branch.
 vi.mocked(qb.availability).mockResolvedValue({tree:[{...math,available:3,children:[{...geometry,available:3,children:[leaf(['Matemática','Geometria','Plana'],3)]},leaf(['Matemática','Funções'],0)]},{...portuguese,available:0,children:portuguese.children.map(n=>({...n,available:0}))}],total:3});
 rerender({...next,difficulties:['FACIL']});
 await waitFor(()=>expect(screen.getByRole('button',{name:'Criar lista'})).toBeEnabled());
 vi.mocked(qb.create).mockRejectedValue(new ApiError('Disponibilidade mudou.',{path:['Matemática','Geometria']}));
 fireEvent.click(screen.getByRole('button',{name:'Criar lista'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Matemática › Geometria: Disponibilidade mudou.');
});

it('does not apply a stale preview after the user changes the requested total',async()=>{
 setup();await named();let finish!:(v:CompositionPreview)=>void;
 vi.mocked(qb.preview).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
 fireEvent.click(screen.getByRole('button',{name:'Sortear distribuição'}));
 await waitFor(()=>expect(qb.preview).toHaveBeenCalled());
 fireEvent.change(screen.getByLabelText('Total de questões'),{target:{value:'9'}});finish(previewValue);
 await waitFor(()=>expect(screen.getByRole('button',{name:'Criar lista'})).toBeEnabled());
 expect(screen.queryByText('20 / 20 distribuídas · Pronto para criar')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Criar lista'}));
 await waitFor(()=>expect(qb.create).toHaveBeenCalledWith('Minha prática',9,null,filters,expect.objectContaining({distribution:'auto'}),'shuffle'));
});
