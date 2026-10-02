import { fetchRelatorioMensal, mesAnterior } from "@/lib/relatorio";
import { useQuery } from "@tanstack/react-query";

export function useRelatorioMensal(mesSelecionado?: number, anoSelecionado?: number) {
  const anterior = mesAnterior();
  const mes = mesSelecionado ?? anterior.mes, ano = anoSelecionado ?? anterior.ano;
  return useQuery({
    queryKey: ["relatorio-mensal", mes, ano],
    queryFn: () => fetchRelatorioMensal(mes, ano),
    staleTime: 1000 * 60 * 60, // 1h — relatório consolidado, muda pouco
  });
}
