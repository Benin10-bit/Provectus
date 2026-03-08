import type {
  MateriaResponse,
  AssuntoResponse,
  DashboardResumo,
  SessaoEstudoCreate,
  SessaoEstudoResponse,
  BlocoQuestoesCreate,
  BlocoQuestoesResponse,
  SimuladoSemanalCreate,
  SimuladoSemanalResponse,
  RedacaoRequest,
  RedacaoResponse,
  Periodo,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error("API indisponível — resposta não é JSON. Verifique VITE_API_URL.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.[0]?.msg || `Erro ${res.status}`);
  }
  return res.json();
}

// ======== CONFIGURAÇÕES ========

export async function fetchMaterias(): Promise<MateriaResponse[]> {
  return request("/configuracoes/materias");
}

export async function fetchAssuntos(materiaId?: string): Promise<AssuntoResponse[]> {
  if (materiaId) {
    return request(`/configuracoes/materias/${materiaId}/assuntos`);
  }
  return request("/configuracoes/assuntos");
}

export async function fetchAssuntosPorMateria(materiaId: string): Promise<AssuntoResponse[]> {
  return request(`/configuracoes/materias/${materiaId}/assuntos`);
}

// ======== PERFORMANCE ========

// Dashboard
export async function fetchDashboard(periodo: Periodo, materiaId?: string): Promise<DashboardResumo> {
  const params = new URLSearchParams({ periodo });
  if (materiaId) params.set("materia_id", materiaId);
  return request(`/api/v1/performance/dashboard?${params}`);
}

// Analytics
export async function fetchAnalytics(periodo: Periodo, materiaId?: string): Promise<Record<string, unknown>> {
  const params = new URLSearchParams({ periodo });
  if (materiaId) params.set("materia_id", materiaId);
  return request(`/api/v1/performance/analytics?${params}`);
}

// Sessões
export async function createSessao(data: SessaoEstudoCreate): Promise<SessaoEstudoResponse> {
  return request("/api/v1/performance/sessoes", { method: "POST", body: JSON.stringify(data) });
}

export async function fetchSessoes(skip = 0, limit = 100): Promise<SessaoEstudoResponse[]> {
  return request(`/api/v1/performance/sessoes?skip=${skip}&limit=${limit}`);
}

// Blocos
export async function createBloco(data: BlocoQuestoesCreate): Promise<BlocoQuestoesResponse> {
  return request("/api/v1/performance/blocos", { method: "POST", body: JSON.stringify(data) });
}

export async function fetchBlocos(skip = 0, limit = 100): Promise<BlocoQuestoesResponse[]> {
  return request(`/api/v1/performance/blocos?skip=${skip}&limit=${limit}`);
}

// Simulados
export async function createSimulado(data: SimuladoSemanalCreate): Promise<SimuladoSemanalResponse> {
  return request("/api/v1/performance/simulados", { method: "POST", body: JSON.stringify(data) });
}

export async function fetchSimulados(skip = 0, limit = 100): Promise<SimuladoSemanalResponse[]> {
  return request(`/api/v1/performance/simulados?skip=${skip}&limit=${limit}`);
}

// Redações
export async function fetchRedacoes(): Promise<RedacaoResponse[]> {
  return request("/api/v1/performance/redacoes");
}

export async function fetchRedacao(id: string): Promise<RedacaoResponse> {
  return request(`/api/v1/performance/redacoes/${id}`);
}

export async function createRedacao(data: RedacaoRequest): Promise<RedacaoResponse> {
  return request("/api/v1/performance/redacoes", { method: "POST", body: JSON.stringify(data) });
}
