import { Loader2, AlertCircle, Inbox } from "lucide-react";

export function LoadingState({ message = "Carregando dados..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 animate-fade-in">
      <div className="relative">
        <Loader2 className="h-7 w-7 animate-spin text-accent" />
        <span className="absolute inset-0 rounded-full bg-accent/20 blur-md animate-pulse" />
      </div>
      <p className="text-xs text-muted-foreground tracking-[0.25em] uppercase font-mono">{message}</p>
    </div>
  );
}

export function ErrorState({ message = "Erro ao carregar dados." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 animate-fade-in">
      <div className="p-3 rounded-full bg-critical/10 border border-critical/30">
        <AlertCircle className="h-6 w-6 text-critical" />
      </div>
      <p className="text-xs text-critical tracking-[0.25em] uppercase font-bold">{message}</p>
      <p className="text-xs text-muted-foreground">Verifique a conexão com a API.</p>
    </div>
  );
}

export function EmptyState({ message = "Nenhum registro encontrado." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 animate-fade-in">
      <div className="p-3 rounded-full bg-muted/50 border border-border">
        <Inbox className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-xs text-muted-foreground tracking-[0.25em] uppercase font-mono">{message}</p>
    </div>
  );
}
