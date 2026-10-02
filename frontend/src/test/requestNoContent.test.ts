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
