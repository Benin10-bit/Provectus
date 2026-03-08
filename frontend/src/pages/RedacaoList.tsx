import { Link } from "react-router-dom";
import { PenTool, Plus } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import { useRedacoes } from "@/hooks/useRedacoes";
import { getCompetenciaNome } from "@/lib/types";
import { format } from "date-fns";

export default function RedacaoList() {
  const { data: redacoes, isLoading, isError } = useRedacoes();

  if (isLoading) return <AppLayout><LoadingState message="Carregando redações..." /></AppLayout>;
  if (isError) return <AppLayout><ErrorState message="Falha ao carregar redações." /></AppLayout>;

  const statusColor = (status: string) =>
    status.includes("Excelente") || status.includes("Bom") ? "text-success"
    : status.includes("Regular") ? "text-warning"
    : "text-critical";

  return (
    <AppLayout>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-wider text-foreground uppercase">
            Redações
          </h1>
          <p className="text-sm text-muted-foreground">Registro e acompanhamento de redações ENEM</p>
        </div>
        <Link
          to="/redacoes/nova"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Nova Redação
        </Link>
      </div>

      {(!redacoes || redacoes.length === 0) ? (
        <EmptyState message="Nenhuma redação registrada." />
      ) : (
        <div className="space-y-3">
          {redacoes.map((r) => (
            <Link
              key={r.id}
              to={`/redacoes/${r.id}`}
              className="block rounded-md border border-border bg-card p-5 hover:hud-glow transition-all duration-200"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-start gap-3">
                  <PenTool className="h-5 w-5 text-accent mt-0.5" />
                  <div>
                    <p className="text-sm font-bold text-foreground">{r.tema}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {format(new Date(r.data_escrita), "dd/MM/yyyy")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-right">
                  <div>
                    <p className="text-2xl font-bold font-mono text-foreground">{r.nota_total}</p>
                    <p className={`text-xs font-medium ${statusColor(r.status)}`}>{r.status}</p>
                  </div>
                  <div className="text-left">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Comp. mais fraca</p>
                    <p className="text-xs text-warning">
                      C{r.competencia_mais_fraca} — {getCompetenciaNome(r.competencia_mais_fraca)}
                    </p>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </AppLayout>
  );
}
