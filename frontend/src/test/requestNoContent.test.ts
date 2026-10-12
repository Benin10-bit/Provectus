import { afterEach, expect, it, vi } from 'vitest';
import { request } from '@/lib/api';

afterEach(() => vi.unstubAllGlobals());

it('accepts the empty 204 response returned when a list is deleted', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
  await expect(request<void>('/api/v1/question-bank/lists/example', { method: 'DELETE' })).resolves.toBeUndefined();
});

it('shows the API reason when deletion is rejected', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Esvazie a pasta antes de excluir.' }), {
    status: 409, headers: { 'content-type': 'application/json' },
  })));
  await expect(request<void>('/api/v1/question-bank/folders/example', { method: 'DELETE' }))
    .rejects.toThrow('Esvazie a pasta antes de excluir.');
});

it('keeps the exact hierarchy path from a structured composition error', async()=>{
  const detail={code:'quota',message:'Existem apenas 3 questões.',path:['Matemática','Geometria']};
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail}),{status:422,headers:{'content-type':'application/json'}})));
  await expect(request('/api/v1/question-bank/composition/preview')).rejects.toMatchObject({message:detail.message,detail});
});

it('shows the readable 422 name validation returned by the question bank', async () => {
  const message = 'Value error, Informe um nome que não seja vazio ou apenas espaços.';
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: [
    { type: 'value_error', loc: ['body', 'name'], msg: message },
  ] }), { status: 422, headers: { 'content-type': 'application/json' } })));
  await expect(request('/api/v1/question-bank/folders', {
    method: 'POST', body: JSON.stringify({ name: '  ' }),
  })).rejects.toThrow(message);
});
