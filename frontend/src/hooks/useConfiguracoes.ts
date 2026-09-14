import { useQuery } from "@tanstack/react-query";
import { fetchMaterias, fetchAssuntos, fetchAssuntosPorMateria } from "@/lib/api";

export function useMaterias() {
  return useQuery({
    queryKey: ["configuracoes", "materias"],
    queryFn: fetchMaterias,
    staleTime: 1000 * 60 * 10,
  });
}

export function useAssuntos() {
  return useQuery({
    queryKey: ["configuracoes", "assuntos"],
    queryFn: () => fetchAssuntos(),
    staleTime: 1000 * 60 * 10,
  });
}

export function useAssuntosPorMateria(materiaId: string | undefined) {
  return useQuery({
    queryKey: ["configuracoes", "assuntos", materiaId],
    queryFn: () => fetchAssuntosPorMateria(materiaId!),
    enabled: !!materiaId,
    staleTime: 1000 * 60 * 10,
  });
}
