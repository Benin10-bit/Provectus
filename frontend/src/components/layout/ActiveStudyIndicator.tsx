import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Clock3, PauseCircle } from 'lucide-react';
import { activityNames, elapsedMs, loadDraft, DRAFT_KEY, type Draft } from '@/lib/study';

export default function ActiveStudyIndicator(){
 const [draft,setDraft]=useState<Draft|null>(loadDraft);
 const [now,setNow]=useState(Date.now());
 const {pathname}=useLocation();
 useEffect(()=>{
  const sync=()=>{setDraft(loadDraft());setNow(Date.now())};
  const storage=(e:StorageEvent)=>{if(e.key===DRAFT_KEY)sync()};
  window.addEventListener('storage',storage);
  window.addEventListener('provectus:study-draft',sync);
  return ()=>{window.removeEventListener('storage',storage);window.removeEventListener('provectus:study-draft',sync)};
 },[]);
 useEffect(()=>{
  if(!draft?.runningSince)return;
  const timer=window.setInterval(()=>setNow(Date.now()),1000);
  return ()=>window.clearInterval(timer);
 },[draft?.runningSince]);
 if(!draft||pathname==='/estudar')return null;
 const seconds=Math.floor(elapsedMs(draft,now)/1000);
 const time=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;
 return <Link to="/estudar" className="active-study-indicator" aria-label={`Voltar à sessão de ${activityNames[draft.atividade]}, ${draft.runningSince?'em andamento':'pausada'}, ${time}`}>
  {draft.runningSince?<Clock3 size={17} aria-hidden/>:<PauseCircle size={17} aria-hidden/>}
  <span className="active-study-indicator-label">{draft.runningSince?'Sessão em andamento':'Sessão pausada'}<small>{activityNames[draft.atividade]}</small></span>
  <strong role="timer">{time}</strong>
 </Link>;
}
