import type { ReactNode } from 'react';
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import RelatorioMensalPage from '@/pages/RelatorioMensalPage';
import { useRelatorioMensal } from '@/hooks/useRelatorioMensal';

vi.mock('@/hooks/useRelatorioMensal', () => ({ useRelatorioMensal: vi.fn() }));
vi.mock('@/components/layout/AppLayout', () => ({ default: ({ children }: { children: ReactNode }) => <>{children}</> }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

function show(erros: Record<string, unknown>) {
  vi.mocked(useRelatorioMensal).mockReturnValue({
    data: { periodo: { mes: 9, ano: 2026 }, erros }, isLoading: false, isError: false, error: null,
  } as unknown as ReturnType<typeof useRelatorioMensal>);
  render(<RelatorioMensalPage />);
}

it('shows actual wrong answers even when no causes were classified', () => {
  show({ total_erros_observados: 4, total_erros_registrados: 0, total_questoes_observadas: 20,
    taxa_erro_observada_atual: 20, cobertura_classificacao_percentual: 0,
    tendencia_erro: 'ESTÁVEL', tendencia_erro_contexto: 'Classificação das causas não determina a tendência.' });
  const card = screen.getByText('Erros observados').parentElement!;
  expect(within(card).getByText('4')).toBeInTheDocument();
  expect(within(card).getByText(/Classificados: 0/)).toBeInTheDocument();
  expect(within(card).getByText(/Taxa observada: 20.0%/)).toBeInTheDocument();
  expect(within(card).getByText(/0.0% dos erros observados/)).toBeInTheDocument();
  expect(screen.queryByText('MELHORANDO')).toBeNull();
});

it('renders insufficient evidence as a neutral state', () => {
  show({ total_erros_observados: 1, total_erros_registrados: 0, tendencia_erro: 'AMOSTRA_INSUFICIENTE' });
  expect(screen.getByText('AMOSTRA INSUFICIENTE')).toHaveClass('text-muted-foreground');
});

it('distinguishes zero observed errors from absent classification and omits undefined coverage', () => {
  show({ total_erros_observados: 0, total_erros_registrados: 0, total_questoes_observadas: 20,
    taxa_erro_observada_atual: 0, cobertura_classificacao_percentual: null, tendencia_erro: 'ESTÁVEL' });
  const card = screen.getByText('Erros observados').parentElement!;
  expect(within(card).getByText(/Taxa observada: 0.0%/)).toBeInTheDocument();
  expect(within(card).getByText(/Classificados: 0/)).toBeInTheDocument();
  expect(within(card).queryByText(/% dos erros observados/)).toBeNull();
});

it('keeps compatibility with reports that only expose classified counts', () => {
  show({ total_erros_registrados: 2, tendencia_erro: 'SEM_DADOS_ANTERIORES' });
  const card = screen.getByText('Erros classificados').parentElement!;
  expect(within(card).getByText('2')).toBeInTheDocument();
  expect(screen.queryByText('Erros observados')).toBeNull();
});
