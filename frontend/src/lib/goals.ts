import {request} from './api';
export interface Source {titulo:string;url:string;limite:string}
export interface Guidance {titulo:string;passos:string[];fonte:Source}
export interface Advice extends Guidance {motivo:string;destino:string}
export interface Day {dia:number;inicio:string|null;fim:string|null;pausas:number;minutos:number}
export interface Profile {dias:Day[];percentual_pratica:number;minutos_por_questao:number;redacoes:number;meta_questoes?:number|null}
export interface Week {
 base_questoes:number;origem_questoes:'manual'|'automatica';
 inicio:string;fim:string;fuso:string;parcial:boolean;meta_minutos:number;meta_questoes:number;meta_redacoes:number;percentual:number;
 realizado:{minutos:number;questoes:number;acertos:number;redacoes:number};status:{horas:string;questoes:string;redacoes:string};status_missao:string;diagnostico_missao?:string;
 esperado_minutos:number;capacidade_restante_minutos:number;percentual_pratica:number;
 dias:(Day & {nome:string;data:string;meta_minutos:number;realizado_minutos:number;janela_minutos:number;capacidade_minutos:number})[];
 calibracao:{minutos_por_questao:number;blocos:number;questoes:number;origem:string};
 materias:{materia_id:string;nome:string;peso:number;meta_minutos:number;realizado_minutos:number}[];
}
export const goalsKey=['performance','metas'];
export const getWeek=()=>request<Week>('/api/v1/metas/semana');
export const getProfile=()=>request<Profile>('/api/v1/metas/configuracao');
export const duration=(minutes:number)=>{const n=Math.round(minutes);return `${Math.floor(n/60)}h${String(n%60).padStart(2,'0')}`;};
export const goalVariant=(status:string)=>status==='META ATINGIDA'?'success':status==='REAJUSTAR RITMO'?'warning':'default';
/** Planning convention: four weeks per month, twelve months per year. */
export function periodGoals(week: Pick<Week, 'meta_minutos' | 'meta_questoes' | 'meta_redacoes'>, period: 'mes' | 'ano') {
 const factor = period === 'mes' ? 4 : 4 * 12;
 return { minutos: week.meta_minutos * factor, questoes: week.meta_questoes * factor, redacoes: week.meta_redacoes * factor };
}
