// Tipo permissivo: o backend pode evoluir, então usamos `any` controlado.
export type RelatorioMensal = Record<string, any>;

const API_BASE = import.meta.env.VITE_API_URL || "";

export async function fetchRelatorioMensal(mes?: number, ano?: number): Promise<RelatorioMensal> {
  const params = new URLSearchParams();
  if (mes) params.set("mes", String(mes));
  if (ano) params.set("ano", String(ano));
  const qs = params.toString();
  const res = await fetch(`${API_BASE}/api/v1/performance/relatorio/mensal${qs ? `?${qs}` : ""}`, {
    headers: { "Content-Type": "application/json" },
  });
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    throw new Error("API indisponível — resposta não é JSON.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.[0]?.msg || `Erro ${res.status}`);
  }
  return res.json();
}

/**
 * Retorna { mes, ano } do mês ANTERIOR ao atual.
 * Ex: hoje é abril/2026 → retorna { mes: 3, ano: 2026 }.
 */
export function mesAnterior(ref = new Date()): { mes: number; ano: number } {
  const d = new Date(ref.getFullYear(), ref.getMonth() - 1, 1);
  return { mes: d.getMonth() + 1, ano: d.getFullYear() };
}

export const NOMES_MES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];
