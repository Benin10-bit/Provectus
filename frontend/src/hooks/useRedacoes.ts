import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { fetchRedacoes, fetchRedacao, createRedacao } from "@/lib/api";
import type { RedacaoRequest } from "@/lib/types";

export function useRedacoes() {
  return useQuery({
    queryKey: ["performance", "redacoes"],
    queryFn: fetchRedacoes,
  });
}

export function useRedacao(id: string) {
  return useQuery({
    queryKey: ["performance", "redacoes", id],
    queryFn: () => fetchRedacao(id),
    enabled: !!id,
  });
}

export function useCreateRedacao(onSuccess?: (id: string) => void) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RedacaoRequest) => createRedacao(data),
    onSuccess: (data) => {
      toast.success(`Redação registrada: ${data.nota_total} pontos`, {
        description: `Status: ${data.status}`,
      });
      qc.invalidateQueries({ queryKey: ["performance"] });
      onSuccess?.(data.id);
    },
    onError: () => toast.error("Erro ao registrar redação."),
  });
}
