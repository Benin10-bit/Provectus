import { Loader2, AlertCircle, Inbox } from "lucide-react";

export function LoadingState({ message = "Carregando dados..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <Loader2 className="h-6 w-6 animate-spin text-accent" />
      <p className="text-xs text-muted-foreground tracking-wider uppercase">{message}</p>
    </div>
  );
}

export function ErrorState({ message = "Erro ao carregar dados." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <AlertCircle className="h-6 w-6 text-critical" />
      <p className="text-xs text-critical tracking-wider uppercase">{message}</p>
      <p className="text-xs text-muted-foreground">Verifique a conexão com a API.</p>
    </div>
  );
}

export function EmptyState({ message = "Nenhum registro encontrado." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <Inbox className="h-6 w-6 text-muted-foreground" />
      <p className="text-xs text-muted-foreground tracking-wider uppercase">{message}</p>
    </div>
  );
}
