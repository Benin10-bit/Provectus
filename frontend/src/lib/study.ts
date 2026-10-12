import { request } from './api';
export type Purpose = 'AVANCO'|'CONSOLIDACAO'|'REVISAO';
export interface RecommendationMeta {finalidade?:Purpose;objetivo_revisao?:string|null;classe_revisao?:'MANUTENCAO'|'RECORRENTE'|'PRIORITARIA'|null}
export type Activity = 'TEORIA'|'QUESTOES'|'REVISAO'|'ANALISE_ERROS';
export const activityNames: Record<Activity,string> = {TEORIA:'Teoria',QUESTOES:'Questões',REVISAO:'Revisão',ANALISE_ERROS:'Análise de erros'};
export interface Goal {materia_id:string;nome:string;minutos:number;segundos_consumidos:number;proporcao:number;ultima_sessao:string|null;ordem:number;ativa:boolean}
export interface Cycle {id:string;nome:string;iniciado_em:string;metas:Goal[];completo:boolean}
export interface Action {id:string;assunto_id:string;descricao:string;causa:string|null;prevista_em:string;concluida_em:string|null;resultado:string|null}
export interface Coverage {familiaridade?:string;familiaridade_declarada?:string|null;id:string;materia_id:string;nome:string;ordem:number;referencia:string|null;estado:string;ultimo_contato:string|null;total_questoes:number;questoes_recentes:number;blocos_recentes:number;precisao:number|null;teoria_registrada:boolean;proximo_passo:string|null;pendencias:Action[]}
export interface Suggestion extends RecommendationMeta {materia_id:string;materia:string;assunto_id:string;assunto:string;atividade:Activity;tarefa:string;referencia:string|null;acao_id:string|null;explicacao:string;duracao_sugerida_minutos?:number|null;aviso?:string}
export interface Now {ciclo:Cycle|null;recomendacao:Suggestion|null;motivo:string|null;materia_id?:string}
export interface Draft extends RecommendationMeta {aceita_em?:string;iniciada_em?:string;id:string;materia_id:string;assunto_id:string;atividade:Activity;data:string;elapsed:number;runningSince:number|null;acao_id:string|null;tarefa:string;total:string;acertos:string;dificuldade?:string;tempoQuestoes?:string;proximo:string;retomar:string;causa:string;resultado:'CONSEGUI'|'REPETIR';}
export const DRAFT_KEY='provectus:study-draft:v1';
export const getNow=(minutes?:number)=>request<Now>('/api/v1/estudos/agora'+(minutes===undefined?'':`?minutos=${minutes}`));
export const getCoverage=(materia?:string)=>request<Coverage[]>(`/api/v1/estudos/cobertura${materia?`?materia_id=${materia}`:''}`);
export const studyPost=<T,>(path:string,data:unknown,method='POST')=>request<T>(`/api/v1/estudos/${path}`,{method,body:JSON.stringify(data)});
export function elapsedMs(d:Draft,now=Date.now()){return Math.max(0,d.elapsed+(d.runningSince?now-d.runningSince:0));}
export function loadDraft():Draft|null{
 try {const d=JSON.parse(localStorage.getItem(DRAFT_KEY)||'null');return d&&typeof d.id==='string'&&Number.isFinite(d.elapsed)?d:null;} catch{return null;}
}

export function completionData(d:Draft, seconds:number) {
 return {...(d.finalidade?{finalidade:d.finalidade,objetivo_revisao:d.objetivo_revisao||null,classe_revisao:d.classe_revisao||null}:{}),chave_registro:d.id,materia_id:d.materia_id,assunto_id:d.assunto_id,atividade:d.atividade,data:d.data,segundos:seconds,proximo_passo:d.proximo||null,
  bloco:d.total?{total_questoes:Number(d.total),total_acertos:Number(d.acertos),dificuldade:d.dificuldade?Number(d.dificuldade):null,
    tempo_total_segundos:d.tempoQuestoes?Math.round(Number(d.tempoQuestoes)*60):null}:null,
  acao_id:d.acao_id,resultado_acao:d.acao_id?d.resultado:null,
  nova_acao:d.retomar?{assunto_id:d.assunto_id,descricao:d.retomar,causa:d.causa||null}:null};
}
