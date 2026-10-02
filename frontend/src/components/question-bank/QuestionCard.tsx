import type { ReactNode } from 'react';
import { RotateCcw, Scissors } from 'lucide-react';
import type { Question } from '@/lib/questionBank';
import RichContent, { Images, remainingAssets } from './RichContent';

const subjects: Record<string,string> = { portugues:'Português', ingles:'Inglês', matematica:'Matemática', fisica:'Física', quimica:'Química', historia:'História', geografia:'Geografia', biologia:'Biologia' };
const difficulties: Record<string,string> = { FACIL:'Fácil', MEDIA:'Média', DIFICIL:'Difícil', MUITO_DIFICIL:'Muito difícil' };
export const displaySubject = (name:string) => subjects[name.trim().toLocaleLowerCase('pt-BR')] || name.replace(/^./u,c=>c.toLocaleUpperCase('pt-BR'));

/** Shared by list practice and search preview. Rendering never writes user state. */
export default function QuestionCard({question:q,title,selected=null,eliminated=[],cutting=false,onSelect,onCut,children}:{
 question:Question; title:string; selected?:string|null; eliminated?:string[]; cutting?:boolean;
 onSelect?:(letter:string)=>void; onCut?:(letter:string)=>void; children?:ReactNode;
}) {
 return <article className="tac-card qb-question">
  <div className="qb-question-meta"><span>{displaySubject(q.materia)}</span>{q.banca_normalizada&&<span>{q.banca_normalizada}</span>}{q.dificuldade_normalizada&&<span>{difficulties[q.dificuldade_normalizada]||q.dificuldade_normalizada}</span>}</div>
  {!!q.content_path?.length&&<p className="qb-content-path">{q.content_path.join(' › ')}</p>}
  <h2>{title}</h2>
  <div className="qb-statement"><RichContent segments={q.statement_segments} fallback={q.enunciado}/></div>
  <Images items={remainingAssets(q.assets,q.statement_segments)}/>
  <div className="qb-alternatives">{q.alternatives.map(alt=>{
   const marked=selected===alt.letter,discarded=eliminated.includes(alt.letter),answered=!!q.answered_at;
   const right=answered&&q.answer?.trim().toUpperCase()===alt.letter.toUpperCase();
   const contents=<><span className="qb-letter">{alt.letter}</span><span className="qb-choice-content"><RichContent segments={alt.segments} fallback={alt.text}/><Images items={remainingAssets(alt.assets,alt.segments)}/></span></>;
   return <div className={`qb-alternative ${discarded?'discarded':''} ${right?'right':''} ${answered&&marked&&!right?'wrong':''} ${marked&&!answered?'chosen':''}`} key={alt.ordinal}>
    {onSelect?<button className="qb-choice" disabled={answered||discarded} onClick={()=>onSelect(alt.letter)} aria-label={`Selecionar alternativa ${alt.letter}`} aria-pressed={marked}>{contents}</button>:<div className="qb-choice">{contents}</div>}
    {onCut&&<button className="qb-cut" onClick={()=>onCut(alt.letter)} disabled={answered||cutting} aria-label={`${discarded?'Restaurar':'Cortar'} alternativa ${alt.letter}`} title={discarded?'Restaurar alternativa':'Cortar alternativa'}>{discarded?<RotateCcw size={17}/>:<Scissors size={17}/>}</button>}
   </div>;
  })}</div>
  {!q.alternatives.length&&<p role="alert" className="text-warning">Esta questão não possui alternativas importadas.</p>}
  {children}
 </article>;
}
