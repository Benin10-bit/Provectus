import { SectionHeading, ActionArrow } from "@/components/experience/StudyUI";
import { Link } from "react-router-dom";
import { PenTool, Plus } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import { useRedacoes } from "@/hooks/useRedacoes";
import { getCompetenciaNome } from "@/lib/types";
import { getRedacaoStatusInfo } from "@/lib/redacaoStatus";
import { format } from "date-fns";

export default function RedacaoList() {
  const { data: redacoes, isLoading, isError } = useRedacoes();

  if (isLoading) return <AppLayout><LoadingState message="Carregando redações..." /></AppLayout>;
  if (isError) return <AppLayout><ErrorState message="Falha ao carregar redações." /></AppLayout>;

  return (
    <AppLayout>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 sm:mb-8">
        <div>
          <h1 className="page-title">Redações</h1>
          
        </div>
        <Link
          to="/redacoes/nova"
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all duration-200 active:scale-[0.98] w-full sm:w-auto"
        >
          <Plus className="h-4 w-4" />
          Nova Redação
        </Link>
      </div>

      <SectionHeading title="Seu histórico de escrita" description="Abra uma redação para rever a correção e as competências."/>
      {(!redacoes || redacoes.length === 0) ? (
        <EmptyState message="Nenhuma redação registrada." />
      ) : (
        <div className="essay-list grid grid-cols-1 gap-4">
          {redacoes.map((r) => {
            const s = getRedacaoStatusInfo(r.status);
            return (
            <Link
              key={r.id}
              to={`/redacoes/${r.id}`}
              className="essay-card block rounded-lg border border-border bg-card p-4 sm:p-5 hover:border-border/80 transition-all duration-200 hover:shadow-[0_0_15px_-5px_hsl(var(--olive)/0.2)]"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <div className="p-1.5 rounded-lg bg-muted/50 shrink-0 mt-0.5">
                    <PenTool className="h-4 w-4 text-accent" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-lg font-semibold text-foreground">{r.tema}</h3>
                    <p className="text-[10px] sm:text-xs text-muted-foreground mt-0.5">
                      {format(new Date(r.data_escrita), "dd/MM/yyyy")}
                    </p>
                  </div>
                </div>
                <div className="essay-card-score flex items-center gap-4 sm:gap-6">
                  <div className="text-right">
                    <p className="text-xl sm:text-2xl font-bold font-mono text-foreground">{r.nota_total}</p>
                    <span className={`inline-flex items-center gap-1.5 mt-1 px-2 py-0.5 rounded-full border text-[10px] sm:text-xs font-semibold ${s.textClass} ${s.bgClass} ${s.borderClass}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${s.dotClass}`} />
                      {s.label}
                    </span>
                  </div>
                  <div className="text-left">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Comp. mais fraca</p>
                    <p className="text-xs text-warning">
                      C{r.competencia_mais_fraca} — {getCompetenciaNome(r.competencia_mais_fraca)}
                    </p>
                  </div>
                </div>
              </div>
              <span className="essay-open">Ver análise <ActionArrow/></span>
            </Link>
            );
          })}
        </div>
      )}
    </AppLayout>
  );
}
