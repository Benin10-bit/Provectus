import { request } from './api';
export type Activity = 'TEORIA'|'QUESTOES'|'REVISAO'|'ANALISE_ERROS';
export const activityNames: Record<Activity,string> = {TEORIA:'Teoria',QUESTOES:'Questões',REVISAO:'Revisão',ANALISE_ERROS:'Análise de erros'};
export interface Goal {materia_id:string;nome:string;minutos:number;segundos_consumidos:number;proporcao:number;ultima_sessao:string|null;ordem:number;ativa:boolean}
export interface Cycle {id:string;nome:string;iniciado_em:string;metas:Goal[];completo:boolean}
export interface Action {id:string;assunto_id:string;descricao:string;causa:string|null;prevista_em:string;concluida_em:string|null;resultado:string|null}
export interface Coverage {id:string;materia_id:string;nome:string;ordem:number;referencia:string|null;estado:string;ultimo_contato:string|null;total_questoes:number;questoes_recentes:number;blocos_recentes:number;precisao:number|null;teoria_registrada:boolean;proximo_passo:string|null;pendencias:Action[]}
export interface Suggestion {materia_id:string;materia:string;assunto_id:string;assunto:string;atividade:Activity;tarefa:string;referencia:string|null;acao_id:string|null;explicacao:string;duracao_sugerida_minutos?:number;aviso?:string}
export interface Now {ciclo:Cycle|null;recomendacao:Suggestion|null;motivo:string|null;materia_id?:string}
export interface Draft {id:string;materia_id:string;assunto_id:string;atividade:Activity;data:string;elapsed:number;runningSince:number|null;acao_id:string|null;tarefa:string;total:string;acertos:string;proximo:string;retomar:string;causa:string;resultado:'CONSEGUI'|'REPETIR';}
export const DRAFT_KEY='provectus:study-draft:v1';
export const getNow=()=>request<Now>('/api/v1/estudos/agora');
export const getCoverage=(materia?:string)=>request<Coverage[]>(`/api/v1/estudos/cobertura${materia?`?materia_id=${materia}`:''}`);
export const studyPost=<T,>(path:string,data:unknown,method='POST')=>request<T>(`/api/v1/estudos/${path}`,{method,body:JSON.stringify(data)});
export function elapsedMs(d:Draft,now=Date.now()){return Math.max(0,d.elapsed+(d.runningSince?now-d.runningSince:0));}
export function loadDraft():Draft|null{
 try {const d=JSON.parse(localStorage.getItem(DRAFT_KEY)||'null');return d&&typeof d.id==='string'&&Number.isFinite(d.elapsed)?d:null;} catch{return null;}
}
