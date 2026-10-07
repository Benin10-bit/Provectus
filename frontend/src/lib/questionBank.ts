import { request } from './api';
const root='/api/v1/question-bank';
const apiBase=import.meta.env.VITE_API_URL || '/api';
export const assetUrl=(url:string)=>`${apiBase}${url}`;
export type AnswerPlacement='after_each'|'end';
export const downloadUrl=(listId:string,placement:AnswerPlacement='end')=>`${apiBase}${root}/lists/${listId}/export.pdf?answer_placement=${placement}`;
export type Node={name:string;path:string[];children:Node[]};
export type Distribution='auto'|'manual';
export type CompositionNode={path:string[];direct?:boolean;quantity:number|null;distribution:Distribution;children:CompositionNode[]};
export type Composition={distribution:Distribution;nodes:CompositionNode[];seed?:string};
export type AvailableNode={name:string;path:string[];direct:boolean;available:number;children:AvailableNode[]};
export type Availability={tree:AvailableNode[];total:number};
export type CompositionPreview={total:number;seed:string;resolved:Composition;groups:{path:string[];direct:boolean;quantity:number}[]};
export type Generation={filters:Filters;requested:Composition;actual:Composition;order:'shuffle'|'grouped'};
export type Filters={paths:string[][];banks:string[];difficulties:string[];search:string;exclude_answered?:boolean;result?:'all'|'correct'|'incorrect'};
export type Asset={hash:string;url:string;type:string;alt:string;mime_type:string};
export type ContentSegment={kind:'text'|'visual';text?:string;bold?:boolean;script?:string|null;line_id?:string;display?:'inline'|'block';role?:string;asset_hash?:string;bbox?:number[];font_size?:number};
export type Alternative={letter:string;ordinal:number;text:string|null;segments?:ContentSegment[];assets:Asset[]};
export type Question={id:string;ordinal:number;enunciado:string;statement_segments?:ContentSegment[];numero_original:number|null;materia:string;banca_normalizada:string|null;dificuldade_normalizada:string|null;content_path:string[];alternatives:Alternative[];assets:Asset[];selected:string|null;answer?:string|null;has_answer?:boolean;answered_at:string|null;correct:boolean|null;eliminated:string[]};
export type Folder={id:string;parent_id:string|null;name:string};
export type StudyList={id:string;folder_id:string|null;name:string;created_at:string;total:number;answered:number;correct:number;wrong:number};
export type Library={folders:Folder[];lists:StudyList[]};
export const qb={
 question:(id:string)=>request<Question>(`${root}/questions/${encodeURIComponent(id)}`),
 check:(id:string,letter:string)=>request<{selected:string;correct:boolean;answer:string}>(`${root}/questions/${encodeURIComponent(id)}/check`,{method:'POST',body:JSON.stringify({letter})}),
 availability:(filters:Filters)=>request<Availability>(`${root}/availability`,{method:'POST',body:JSON.stringify(filters)}),
 preview:(count:number,filters:Filters,composition:Composition)=>request<CompositionPreview>(`${root}/composition/preview`,{method:'POST',body:JSON.stringify({count,filters,composition})}),
 filters:()=>request<{tree:Node[];banks:string[];difficulties:string[]}>(`${root}/filters`),
 search:(filters:Filters,page=1,size=12)=>request<{total:number;items:Question[]}>(`${root}/search?page=${page}&size=${size}`,{method:'POST',body:JSON.stringify(filters)}),
 library:()=>request<Library>(`${root}/library`),
 list:(id:string,page=1)=>request<{id:string;name:string;total:number;items:Question[];generation?:Generation|null}>(`${root}/lists/${id}?page=${page}&size=1`),
 create:(name:string,count:number,folder_id:string|null,filters:Filters,composition?:Composition,order:'shuffle'|'grouped'='shuffle')=>request<{id:string}>(`${root}/lists`,{method:'POST',body:JSON.stringify({name,count,folder_id,filters,composition,order})}),
 folder:(name:string,parent_id:string|null)=>request(`${root}/folders`,{method:'POST',body:JSON.stringify({name,parent_id})}),
 editFolder:(id:string,change:Partial<Folder>)=>request(`${root}/folders/${id}`,{method:'PATCH',body:JSON.stringify(change)}),
 editList:(id:string,change:Partial<StudyList>)=>request(`${root}/lists/${id}`,{method:'PATCH',body:JSON.stringify(change)}),
 remove:(kind:'folders'|'lists',id:string)=>request<void>(`${root}/${kind}/${id}`,{method:'DELETE'}),
 eliminate:(id:string,qid:string,letters:string[])=>request<{eliminated:string[]}>(`${root}/lists/${id}/questions/${encodeURIComponent(qid)}/eliminated`,{method:'PUT',body:JSON.stringify({letters})}),
 answer:(id:string,qid:string,letter:string)=>request<{selected:string;correct:boolean;answer:string}>(`${root}/lists/${id}/questions/${encodeURIComponent(qid)}/answer`,{method:'POST',body:JSON.stringify({letter})}),
};
