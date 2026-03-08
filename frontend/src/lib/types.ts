// Types based on the API OpenAPI spec v2.0

export interface MateriaResponse {
  id: string;
  nome: string;
}

export interface AssuntoResponse {
  id: string;
  nome: string;
  materia_id: string;
}

export interface SessaoEstudoCreate {
  materia_id: string;
  assunto_id: string;
  tipo_sessao: "TEORIA" | "QUESTOES" | "REVISAO";
  minutos_liquidos: number;
  nivel_foco?: number | null;
  nivel_energia?: number | null;
  data?: string;
}

export interface SessaoEstudoResponse extends SessaoEstudoCreate {
  id: string;
  criado_em: string;
}

export interface BlocoQuestoesCreate {
  materia_id: string;
  assunto_id: string;
  dificuldade: number;
  total_questoes: number;
  total_acertos: number;
  tempo_total_segundos: number;
  nivel_confianca_medio?: number | null;
  data?: string;
}

export interface BlocoQuestoesResponse extends BlocoQuestoesCreate {
  id: string;
  percentual_acerto: number;
  tempo_medio_por_questao: number;
  criado_em: string;
}

export interface SimuladoSemanalCreate {
  numero_ciclo: number;
  numero_semana: number;
  total_questoes: number;
  total_acertos: number;
  tempo_total_segundos: number;
  nivel_ansiedade?: number | null;
  nivel_fadiga?: number | null;
  qualidade_sono?: number | null;
}

export interface SimuladoSemanalResponse extends SimuladoSemanalCreate {
  id: string;
  percentual_acerto: number;
  criado_em: string;
}

export interface DashboardResumo {
  horas_liquidas: number;
  total_questoes: number;
  percentual_medio: number;
  ipr_geral: number;
  tendencia: string;
  status_missao: string;
  assuntos_criticos: string[];
  status_horas: string;
  status_questoes: string;
  recomendacao: string;
}

export interface RedacaoRequest {
  tema: string;
  eixo_tematico?: string | null;
  tempo_escrita_min?: number | null;
  observacoes?: string | null;
  repertorios?: string | null;
  competencia1: number;
  competencia2: number;
  competencia3: number;
  competencia4: number;
  competencia5: number;
}

export interface RedacaoResponse {
  id: string;
  tema: string;
  eixo_tematico: string | null;
  data_escrita: string;
  tempo_escrita_min: number | null;
  observacoes: string | null;
  repertorios: string | null;
  competencia1: number;
  competencia2: number;
  competencia3: number;
  competencia4: number;
  competencia5: number;
  nota_total: number;
  status: string;
  competencia_mais_fraca: number;
  diagnostico: string;
  recomendacao: string;
  criado_em: string;
}

export type Periodo = "semana" | "mes" | "ano" | "total";

export const COMPETENCIAS_MAP: Record<string, string> = {
  C1: "Domínio da norma culta da língua portuguesa",
  C2: "Compreensão da proposta de redação",
  C3: "Seleção e organização de argumentos",
  C4: "Conhecimento dos mecanismos linguísticos",
  C5: "Proposta de intervenção",
};

export function getCompetenciaNome(code: string | number): string {
  const key = typeof code === "number" ? `C${code}` : code;
  return COMPETENCIAS_MAP[key] ?? key;
}
