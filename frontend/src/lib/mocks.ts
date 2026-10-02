// =============================================================================
// 🟢 MOCK DATA LAYER — para análise visual do front-end.
// -----------------------------------------------------------------------------
// COMO REMOVER:
//   1) Em src/lib/api.ts mude:  export const USE_MOCKS = true   ->  false
//   2) (Opcional) delete este arquivo.
// =============================================================================

import type {
  AssuntoResponse,
  BlocoQuestoesResponse,
  DashboardResumo,
  MateriaPerformance,
  MateriaResponse,
  Periodo,
  RedacaoResponse,
  SessaoEstudoResponse,
  SimuladoSemanalResponse,
} from "./types";

// ---------- 8 matérias (antes eram 7) ----------
export const MOCK_MATERIAS: MateriaResponse[] = [
  { id: "m1", nome: "Matemática" },
  { id: "m2", nome: "Português" },
  { id: "m3", nome: "Física" },
  { id: "m4", nome: "Química" },
  { id: "m5", nome: "História" },
  { id: "m6", nome: "Geografia" },
  { id: "m7", nome: "Inglês" },
  { id: "m8", nome: "Redação" },
];

export const MOCK_ASSUNTOS: AssuntoResponse[] = [
  { id: "a1", nome: "Funções", materia_id: "m1" },
  { id: "a2", nome: "Geometria Analítica", materia_id: "m1" },
  { id: "a3", nome: "Trigonometria", materia_id: "m1" },
  { id: "a4", nome: "Sintaxe", materia_id: "m2" },
  { id: "a5", nome: "Interpretação", materia_id: "m2" },
  { id: "a6", nome: "Cinemática", materia_id: "m3" },
  { id: "a7", nome: "Eletrodinâmica", materia_id: "m3" },
  { id: "a8", nome: "Estequiometria", materia_id: "m4" },
  { id: "a9", nome: "Orgânica", materia_id: "m4" },
  { id: "a10", nome: "Brasil Império", materia_id: "m5" },
  { id: "a11", nome: "Era Vargas", materia_id: "m5" },
  { id: "a12", nome: "Geopolítica", materia_id: "m6" },
  { id: "a13", nome: "Reading", materia_id: "m7" },
  { id: "a14", nome: "Dissertativa", materia_id: "m8" },
];

const IPR_POR_MATERIA: Record<string, { ipr: number; q: number; a: number; h: number }> = {
  m1: { ipr: 88, q: 240, a: 211, h: 14.5 },
  m2: { ipr: 76, q: 180, a: 137, h: 9.8 },
  m3: { ipr: 82, q: 165, a: 135, h: 11.2 },
  m4: { ipr: 68, q: 142, a: 97, h: 8.4 },
  m5: { ipr: 91, q: 110, a: 100, h: 6.5 },
  m6: { ipr: 73, q: 95, a: 69, h: 5.2 },
  m7: { ipr: 85, q: 70, a: 60, h: 4.0 },
  m8: { ipr: 64, q: 40, a: 26, h: 7.5 },
};

export function mockMateriasPerformance(_periodo: Periodo): MateriaPerformance[] {
  return MOCK_MATERIAS.map((m) => {
    const v = IPR_POR_MATERIA[m.id];
    return {
      materia: m,
      ipr: v.ipr,
      total_questoes: v.q,
      total_acertos: v.a,
      horas_estudo: v.h,
    };
  });
}

export function mockDashboard(periodo: Periodo, materiaId?: string): DashboardResumo {
  if (materiaId && IPR_POR_MATERIA[materiaId]) {
    const v = IPR_POR_MATERIA[materiaId];
    return {
      horas_liquidas: v.h,
      total_questoes: v.q,
      percentual_medio: Math.round((v.a / v.q) * 100),
      ipr_geral: v.ipr,
      tendencia: v.ipr >= 80 ? "ASCENDENTE" : v.ipr >= 70 ? "ESTÁVEL" : "DECLÍNIO",
      status_missao: v.ipr >= 70 ? "MISSÃO CUMPRIDA" : "MISSÃO EM RISCO",
      assuntos_criticos: v.ipr < 70 ? ["a8", "a14"] : [],
      status_horas: "DENTRO",
      status_questoes: "ACIMA",
      recomendacao: ["Manter o ritmo de questões diárias.", "Reforçar revisões espaçadas."],
    };
  }
  const fator = periodo === "semana" ? 1 : periodo === "mes" ? 4 : periodo === "ano" ? 48 : 60;
  return {
    horas_liquidas: 18.7 * (fator / 1),
    total_questoes: 312 * fator,
    percentual_medio: 78,
    ipr_geral: 79,
    tendencia: "ASCENDENTE",
    status_missao: "MISSÃO CUMPRIDA",
    assuntos_criticos: ["a8", "a14"],
    status_horas: "DENTRO",
    status_questoes: "ACIMA",
    recomendacao: [
      "Foco em Química Orgânica nesta semana.",
      "Aumentar volume de redação para 2 por semana.",
      "Revisar Era Vargas até quinta.",
    ],
  };
}

function dataPassada(diasAtras: number): string {
  const d = new Date();
  d.setDate(d.getDate() - diasAtras);
  return d.toISOString();
}

export const MOCK_SESSOES: SessaoEstudoResponse[] = Array.from({ length: 14 }, (_, i) => ({
  id: `s${i + 1}`,
  materia_id: MOCK_MATERIAS[i % MOCK_MATERIAS.length].id,
  assunto_id: MOCK_ASSUNTOS[i % MOCK_ASSUNTOS.length].id,
  tipo_sessao: i % 3 === 0 ? "TEORIA" : i % 3 === 1 ? "QUESTOES" : "REVISAO",
  minutos_liquidos: 30 + (i * 7) % 60,
  nivel_foco: 2 + (i % 4),
  nivel_energia: 2 + ((i + 1) % 4),
  criado_em: dataPassada(i),
}));

export const MOCK_BLOCOS: BlocoQuestoesResponse[] = Array.from({ length: 12 }, (_, i) => {
  const tq = 15 + (i % 10);
  const ta = Math.max(0, tq - (i % 6));
  return {
    id: `b${i + 1}`,
    materia_id: MOCK_MATERIAS[i % MOCK_MATERIAS.length].id,
    assunto_id: MOCK_ASSUNTOS[i % MOCK_ASSUNTOS.length].id,
    dificuldade: 2 + (i % 4),
    total_questoes: tq,
    total_acertos: ta,
    tempo_total_segundos: 60 * (15 + i * 2),
    nivel_confianca_medio: 3,
    percentual_acerto: Math.round((ta / tq) * 100),
    tempo_medio_por_questao: Math.round((60 * (15 + i * 2)) / tq),
    criado_em: dataPassada(i),
  };
});

export const MOCK_SIMULADOS: SimuladoSemanalResponse[] = Array.from({ length: 8 }, (_, i) => {
  const tq = 90;
  const ta = 55 + (i * 3) % 30;
  return {
    id: `sim${i + 1}`,
    numero_ciclo: 1 + Math.floor(i / 4),
    numero_semana: (i % 4) + 1,
    total_questoes: tq,
    total_acertos: ta,
    tempo_total_segundos: 60 * 240,
    nivel_ansiedade: 3,
    nivel_fadiga: 3,
    qualidade_sono: 4,
    percentual_acerto: Math.round((ta / tq) * 100),
    criado_em: dataPassada(i * 7),
  };
});

export const MOCK_REDACOES: RedacaoResponse[] = Array.from({ length: 6 }, (_, i) => {
  const c1 = 120 + (i * 13) % 80;
  const c2 = 140 + (i * 7) % 60;
  const c3 = 130 + (i * 11) % 70;
  const c4 = 150 + (i * 5) % 50;
  const c5 = 110 + (i * 17) % 90;
  const total = c1 + c2 + c3 + c4 + c5;
  return {
    id: `r${i + 1}`,
    tema: [
      "Desafios da educação digital no Brasil",
      "Saúde mental na juventude contemporânea",
      "Mobilidade urbana e sustentabilidade",
      "Combate à desinformação",
      "Acesso à cultura nas periferias",
      "Reforma agrária no século XXI",
    ][i],
    eixo_tematico: "Sociedade",
    data_escrita: dataPassada(i * 5),
    tempo_escrita_min: 60 + (i * 5) % 30,
    observacoes: null,
    repertorios: "ENEM 2023, BNCC",
    competencia1: c1,
    competencia2: c2,
    competencia3: c3,
    competencia4: c4,
    competencia5: c5,
    nota_total: total,
    status: total >= 800 ? "Excelente" : total >= 600 ? "Bom" : total >= 400 ? "Regular" : "Insuficiente",
    competencia_mais_fraca: [c1, c2, c3, c4, c5].indexOf(Math.min(c1, c2, c3, c4, c5)) + 1,
    diagnostico: "Argumentação consistente, mas faltou repertório sociocultural sólido.",
    recomendacao: "Estudar 3 repertórios novos por semana e praticar conclusão.",
    criado_em: dataPassada(i * 5),
  };
});
