import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { DashboardResumo } from '@/lib/types';

export function strategyText(d:DashboardResumo):string[] {
 if(d.recomendacoes_estudo?.length)return d.recomendacoes_estudo;
 // Compatibility with older APIs: use real aggregate data, never the old goal summary.
 if(!d.total_questoes)return [d.horas_liquidas>0?'Após o próximo trecho de teoria, feche o material, tente algumas questões e confira as soluções. Há tempo registrado, mas ainda não há questões neste período.':'Registre uma sessão e algumas tentativas sem consulta para que o sistema possa orientar seus próximos estudos.'];
 const small=d.total_questoes<20||(d.amostra_blocos??0)<2;
 const assessment=small?`Seus ${d.percentual_medio}% de acertos ainda precisam de mais tentativas para sustentar uma avaliação. Resolva questões do mesmo assunto em dias diferentes antes de reduzir a revisão.`:d.percentual_medio<70?`Com ${d.percentual_medio}% de acertos, priorize corrigir os erros antes de aumentar o volume: refaça sem consulta, confira a solução e tente uma questão semelhante.`:`Com ${d.percentual_medio}% de acertos, retome os erros e os acertos por dúvida em outro dia, sem consultar a solução, para verificar retenção.`;
 return [assessment,`Você registrou ${d.total_questoes} questões neste período. Na próxima sessão, reserve tempo para explicar as correções com suas palavras, além de resolver questões novas.`,d.horas_liquidas>0?'Distribua parte do estudo em outro dia. Comece o retorno tentando lembrar ou resolver, usando a releitura para corrigir as lacunas que aparecerem.':'Registre também o tempo das sessões para acompanhar como você distribui teoria, prática e revisão.'];
}
export default function CardRecomendacao({ d }: { d: DashboardResumo; materia?:string }) {
 const [open,setOpen]=useState(false);
 const rows=strategyText(d);
 return <section className="recommendation-card tac-card" aria-label="Recomendação Estratégica">
  <h2 className="font-semibold mb-4">Recomendação Estratégica</h2>
  <div className="flex items-start gap-3">
   <p className="text-sm leading-relaxed flex-1">{rows[0]}</p>
   {rows.length>1&&<button type="button" className="p-2 rounded-md text-accent hover:bg-accent/10 shrink-0" aria-label={open?'Ocultar outras recomendações':'Mostrar outras recomendações'} aria-expanded={open} onClick={()=>setOpen(!open)}><ChevronDown size={18} className={`transition-transform ${open?'rotate-180':''}`}/></button>}
  </div>
  {open&&<ul className="list-disc pl-5 space-y-3 mt-4 text-sm leading-relaxed text-muted-foreground">{rows.slice(1).map((text,i)=><li key={i}>{text}</li>)}</ul>}
 </section>;
}
