import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ActiveStudyIndicator from '@/components/layout/ActiveStudyIndicator';
import { DRAFT_KEY } from '@/lib/study';
afterEach(()=>{cleanup();localStorage.removeItem(DRAFT_KEY)});
it('keeps the study timer visible on the question bank while a session runs',()=>{
 localStorage.setItem(DRAFT_KEY,JSON.stringify({id:'draft',atividade:'QUESTOES',elapsed:0,runningSince:Date.now()-65000}));
 render(<MemoryRouter initialEntries={['/banco-questoes']}><ActiveStudyIndicator/></MemoryRouter>);
 expect(screen.getByRole('link',{name:/Voltar à sessão de Questões, em andamento/})).toHaveAttribute('href','/estudar');
 expect(screen.getByRole('timer')).toHaveTextContent('01:05');
});
