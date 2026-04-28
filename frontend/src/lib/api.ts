import {
  MOCK_ASSUNTOS,
  MOCK_BLOCOS,
  MOCK_MATERIAS,
  MOCK_REDACOES,
  MOCK_SESSOES,
  MOCK_SIMULADOS,
  mockDashboard,
  mockMateriasPerformance,
} from "./mocks";
import type {
    AssuntoResponse,
    BlocoQuestoesCreate,
    BlocoQuestoesResponse,
    DashboardResumo,
    MateriaPerformance,
    MateriaResponse,
    Periodo,
    RedacaoRequest,
    RedacaoResponse,
    SessaoEstudoCreate,
    SessaoEstudoResponse,
    SimuladoSemanalCreate,
    SimuladoSemanalResponse,
} from "./types";

export const USE_MOCKS = false;

const API_BASE = import.meta.env.VITE_API_URL || "";

// Latência simulada para que loading states apareçam.
function mockResponse<T>(data: T, ms = 250): Promise<T> {
    return new Promise(resolve => setTimeout(() => resolve(data), ms));
}

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
    if (USE_MOCKS) return mockResponse(MOCK_MATERIAS);
    return request("/configuracoes/materias");
}

export async function fetchAssuntos(materiaId?: string): Promise<AssuntoResponse[]> {
    if (USE_MOCKS) {
      return mockResponse(materiaId ? MOCK_ASSUNTOS.filter(a => a.materia_id === materiaId) : MOCK_ASSUNTOS);
    }
    if (materiaId) {
        return request(`/configuracoes/materias/${materiaId}/assuntos`);
    }
    return request("/configuracoes/assuntos");
}

export async function fetchAssuntosPorMateria(materiaId: string): Promise<AssuntoResponse[]> {
    if (USE_MOCKS) return mockResponse(MOCK_ASSUNTOS.filter(a => a.materia_id === materiaId));
    return request(`/configuracoes/materias/${materiaId}/assuntos`);
}

// ======== PERFORMANCE ========

export async function fetchDashboard(periodo: Periodo, materiaId?: string): Promise<DashboardResumo> {
    if (USE_MOCKS) return mockResponse(mockDashboard(periodo, materiaId));
    const params = new URLSearchParams({ periodo });
    if (materiaId) params.set("materia_id", materiaId);
    return request(`/api/v1/performance/dashboard?${params}`);
}

export async function fetchMateriasPerformance(periodo: Periodo): Promise<MateriaPerformance[]> {
    if (USE_MOCKS) return mockResponse(mockMateriasPerformance(periodo));
    const materias = await fetchMaterias();
    const performances = await Promise.all(
        materias.map(async materia => {
            const dash = await fetchDashboard(periodo, materia.id);
            return {
                materia,
                ipr: dash.ipr_geral,
                total_questoes: dash.total_questoes,
                total_acertos: Math.round(dash.total_questoes * (dash.percentual_medio / 100)),
                horas_estudo: dash.horas_liquidas,
            };
        }),
    );
    return performances;
}

export async function fetchAnalytics(periodo: Periodo, materiaId?: string): Promise<Record<string, unknown>> {
    const params = new URLSearchParams({ periodo });
    if (materiaId) params.set("materia_id", materiaId);
    return request(`/api/v1/performance/analytics?${params}`);
}

// Sessões
export async function createSessao(data: SessaoEstudoCreate): Promise<SessaoEstudoResponse> {
    if (USE_MOCKS) return mockResponse({ ...data, id: `s_new_${Date.now()}`, criado_em: new Date().toISOString() } as SessaoEstudoResponse);
    return request("/api/v1/performance/sessoes", { method: "POST", body: JSON.stringify(data) });
}

export async function fetchSessoes(skip = 0, limit = 100): Promise<SessaoEstudoResponse[]> {
    if (USE_MOCKS) return mockResponse(MOCK_SESSOES.slice(skip, skip + limit));
    return request(`/api/v1/performance/sessoes?skip=${skip}&limit=${limit}`);
}

// Blocos
export async function createBloco(data: BlocoQuestoesCreate): Promise<BlocoQuestoesResponse> {
    if (USE_MOCKS) {
      const pct = Math.round((data.total_acertos / data.total_questoes) * 100);
      return mockResponse({
        ...data,
        id: `b_new_${Date.now()}`,
        percentual_acerto: pct,
        tempo_medio_por_questao: Math.round(data.tempo_total_segundos / data.total_questoes),
        criado_em: new Date().toISOString(),
      } as BlocoQuestoesResponse);
    }
    return request("/api/v1/performance/blocos", { method: "POST", body: JSON.stringify(data) });
}

export async function fetchBlocos(skip = 0, limit = 100): Promise<BlocoQuestoesResponse[]> {
    if (USE_MOCKS) return mockResponse(MOCK_BLOCOS.slice(skip, skip + limit));
    return request(`/api/v1/performance/blocos?skip=${skip}&limit=${limit}`);
}

// Simulados
export async function createSimulado(data: SimuladoSemanalCreate): Promise<SimuladoSemanalResponse> {
    if (USE_MOCKS) {
      const pct = Math.round((data.total_acertos / data.total_questoes) * 100);
      return mockResponse({
        ...data,
        id: `sim_new_${Date.now()}`,
        percentual_acerto: pct,
        criado_em: new Date().toISOString(),
      } as SimuladoSemanalResponse);
    }
    return request("/api/v1/performance/simulados", { method: "POST", body: JSON.stringify(data) });
}

export async function fetchSimulados(skip = 0, limit = 100): Promise<SimuladoSemanalResponse[]> {
    if (USE_MOCKS) return mockResponse(MOCK_SIMULADOS.slice(skip, skip + limit));
    return request(`/api/v1/performance/simulados?skip=${skip}&limit=${limit}`);
}

// Redações
export async function fetchRedacoes(): Promise<RedacaoResponse[]> {
    if (USE_MOCKS) return mockResponse(MOCK_REDACOES);
    return request("/api/v1/performance/redacoes");
}

export async function fetchRedacao(id: string): Promise<RedacaoResponse> {
    if (USE_MOCKS) {
      const found = MOCK_REDACOES.find(r => r.id === id) || MOCK_REDACOES[0];
      return mockResponse(found);
    }
    return request(`/api/v1/performance/redacoes/${id}`);
}

export async function createRedacao(data: RedacaoRequest): Promise<RedacaoResponse> {
    if (USE_MOCKS) {
      const total = data.competencia1 + data.competencia2 + data.competencia3 + data.competencia4 + data.competencia5;
      const notas = [data.competencia1, data.competencia2, data.competencia3, data.competencia4, data.competencia5];
      return mockResponse({
        id: `r_new_${Date.now()}`,
        tema: data.tema,
        eixo_tematico: data.eixo_tematico ?? null,
        data_escrita: new Date().toISOString(),
        tempo_escrita_min: data.tempo_escrita_min ?? null,
        observacoes: data.observacoes ?? null,
        repertorios: data.repertorios ?? null,
        competencia1: data.competencia1,
        competencia2: data.competencia2,
        competencia3: data.competencia3,
        competencia4: data.competencia4,
        competencia5: data.competencia5,
        nota_total: total,
        status: total >= 800 ? "Excelente" : total >= 600 ? "Bom" : total >= 400 ? "Regular" : "Insuficiente",
        competencia_mais_fraca: notas.indexOf(Math.min(...notas)) + 1,
        diagnostico: "Análise simulada (mock).",
        recomendacao: "Continue praticando.",
        criado_em: new Date().toISOString(),
      } as RedacaoResponse);
    }
    return request("/api/v1/performance/redacoes", { method: "POST", body: JSON.stringify(data) });
}
