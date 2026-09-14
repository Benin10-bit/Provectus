import {
    createBloco,
    createSessao,
    createSimulado,
    fetchBlocos,
    fetchDashboard,
    fetchMateriasPerformance,
    fetchSessoes,
    fetchSimulados,
} from "@/lib/api";
import type { BlocoQuestoesCreate, Periodo, SessaoEstudoCreate, SimuladoSemanalCreate } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

// ---- Dashboard ----
export function useDashboard(periodo: Periodo, materiaId?: string) {
    return useQuery({
        queryKey: ["performance", "dashboard", periodo, materiaId],
        queryFn: () => fetchDashboard(periodo, materiaId || undefined),
    });
}

// ---- Materias Performance ----
export function useMateriasPerformance(periodo: Periodo) {
    return useQuery({
        queryKey: ["performance", "materiasPerformance", periodo],
        queryFn: () => fetchMateriasPerformance(periodo),
    });
}

// ---- Sessões ----
export function useSessoes(skip = 0, limit = 100) {
    return useQuery({
        queryKey: ["performance", "sessoes", skip, limit],
        queryFn: () => fetchSessoes(skip, limit),
    });
}

export function useCreateSessao(onSuccess?: () => void) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (data: SessaoEstudoCreate) => createSessao(data),
        onSuccess: () => {
            toast.success("Sessão registrada com sucesso!", { description: "Dashboard atualizado." });
            qc.invalidateQueries({ queryKey: ["performance"] });
            onSuccess?.();
        },
        onError: () => toast.error("Erro ao registrar sessão."),
    });
}

// ---- Blocos ----
export function useBlocos(skip = 0, limit = 100) {
    return useQuery({
        queryKey: ["performance", "blocos", skip, limit],
        queryFn: () => fetchBlocos(skip, limit),
    });
}

export function useCreateBloco(onSuccess?: (pct: number) => void) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (data: BlocoQuestoesCreate) => createBloco(data),
        onSuccess: data => {
            const critico = data.percentual_acerto < 70;
            toast.success(`Bloco registrado: ${data.percentual_acerto}%`, {
                description: critico ? "⚠️ ASSUNTO CRÍTICO — IPR abaixo de 70%" : "Performance operacional.",
            });
            qc.invalidateQueries({ queryKey: ["performance"] });
            onSuccess?.(data.percentual_acerto);
        },
        onError: () => toast.error("Erro ao registrar bloco."),
    });
}

// ---- Simulados ----
export function useSimulados(skip = 0, limit = 100) {
    return useQuery({
        queryKey: ["performance", "simulados", skip, limit],
        queryFn: () => fetchSimulados(skip, limit),
    });
}

export function useCreateSimulado(onSuccess?: (pct: number) => void) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (data: SimuladoSemanalCreate) => createSimulado(data),
        onSuccess: data => {
            toast.success(`Simulado registrado: ${data.percentual_acerto}%`);
            qc.invalidateQueries({ queryKey: ["performance"] });
            onSuccess?.(data.percentual_acerto);
        },
        onError: () => toast.error("Erro ao registrar simulado."),
    });
}
