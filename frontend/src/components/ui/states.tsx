import { AlertCircle, Inbox, Loader2 } from "lucide-react";

export function LoadingState({ message = "Carregando dados..." }: { message?: string }) {
  return <div className="loading-surface" role="status" aria-busy="true" aria-label={message}>
    <div className="loading-caption"><Loader2 size={15} className="animate-spin"/><span>{message}</span></div>
    <div className="skeleton-layout" aria-hidden><div className="skeleton-line short"/><div className="skeleton-metrics">{[0,1,2].map(n=><div className="skeleton-metric" key={n}><i/><b/><i/></div>)}</div><div className="skeleton-line"/><div className="skeleton-line medium"/></div>
  </div>;
}
export function ErrorState({ message = "Erro ao carregar dados." }: { message?: string }) {
  return <div role="alert" className="feedback-state feedback-error"><div className="feedback-icon"><AlertCircle size={24}/></div><div><h2>Não foi possível carregar</h2><p>{message}</p><p className="feedback-help">Verifique a conexão com a API.</p></div></div>;
}
export function EmptyState({ message = "Nenhum registro encontrado." }: { message?: string }) {
  return <div role="status" className="feedback-state feedback-empty"><div className="feedback-icon"><Inbox size={25}/></div><div><h2>Espaço para o seu progresso</h2><p>{message}</p></div></div>;
}
