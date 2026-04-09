import { useParams, Link } from "react-router-dom";
import { ArrowLeft, AlertTriangle, Lightbulb } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import { LoadingState, ErrorState } from "@/components/ui/states";
import { useRedacao } from "@/hooks/useRedacoes";
import { getCompetenciaNome } from "@/lib/types";
import { format } from "date-fns";

function competenciaColor(nota: number): string {
  if (nota >= 140) return "bg-success";
  if (nota >= 80) return "bg-warning";
  return "bg-critical";
}

function competenciaTextColor(nota: number): string {
  if (nota >= 140) return "text-success";
  if (nota >= 80) return "text-warning";
  return "text-critical";
}

export default function RedacaoDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: r, isLoading, isError } = useRedacao(id || "");

  if (isLoading) return <AppLayout><LoadingState message="Carregando redação..." /></AppLayout>;
  if (isError || !r) return <AppLayout><ErrorState message="Falha ao carregar redação." /></AppLayout>;

  const competencias = [
    { code: "C1", nota: r.competencia1 },
    { code: "C2", nota: r.competencia2 },
    { code: "C3", nota: r.competencia3 },
    { code: "C4", nota: r.competencia4 },
    { code: "C5", nota: r.competencia5 },
  ];

  const statusColor =
    r.status.includes("Excelente") || r.status.includes("Bom") ? "text-success"
    : r.status.includes("Regular") ? "text-warning"
    : "text-critical";

  return (
    <AppLayout>
      <div className="page-header">
        <Link to="/redacoes" className="inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-3 sm:mb-4 transition-colors">
          <ArrowLeft className="h-3 w-3" />
          Voltar para redações
        </Link>
        <h1 className="page-title">Detalhe da Redação</h1>
        <p className="page-subtitle mt-1">{r.tema}</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4 mb-6 stagger-children">
        <div className="rounded-lg border border-border bg-card p-3 sm:p-4">
          <p className="text-[9px] sm:text-[10px] tracking-wider text-muted-foreground uppercase">Data</p>
          <p className="text-sm sm:text-lg font-bold font-mono text-foreground mt-1">
            {format(new Date(r.data_escrita), "dd/MM/yyyy")}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3 sm:p-4">
          <p className="text-[9px] sm:text-[10px] tracking-wider text-muted-foreground uppercase">Nota Total</p>
          <p className="text-xl sm:text-3xl font-bold font-mono text-foreground mt-1">{r.nota_total}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3 sm:p-4">
          <p className="text-[9px] sm:text-[10px] tracking-wider text-muted-foreground uppercase">Status</p>
          <p className={`text-sm sm:text-lg font-bold mt-1 ${statusColor}`}>{r.status}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3 sm:p-4">
          <p className="text-[9px] sm:text-[10px] tracking-wider text-muted-foreground uppercase">Comp. Mais Fraca</p>
          <p className="text-sm font-bold text-warning mt-1">C{r.competencia_mais_fraca}</p>
          <p className="text-[9px] sm:text-[10px] text-muted-foreground truncate">{getCompetenciaNome(r.competencia_mais_fraca)}</p>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card p-4 sm:p-6 mb-6">
        <p className="text-[10px] sm:text-xs font-medium tracking-wider text-muted-foreground uppercase mb-4 sm:mb-5">
          Competências
        </p>
        <div className="space-y-4 sm:space-y-5">
          {competencias.map((c) => (
            <div key={c.code}>
              <div className="flex items-center justify-between mb-1.5 gap-2">
                <p className="text-xs sm:text-sm text-foreground truncate">
                  <span className="font-bold text-accent">{c.code}</span> — {getCompetenciaNome(c.code)}
                </p>
                <p className={`text-xs sm:text-sm font-bold font-mono shrink-0 ${competenciaTextColor(c.nota)}`}>
                  {c.nota}/200
                </p>
              </div>
              <div className="relative h-2 sm:h-3 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${competenciaColor(c.nota)}`}
                  style={{ width: `${(c.nota / 200) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
        <div className="rounded-lg border border-critical/40 bg-critical/5 p-4 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-critical/15 shrink-0">
              <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-critical" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] sm:text-xs tracking-wider text-muted-foreground uppercase mb-2">Diagnóstico</p>
              <p className="text-xs sm:text-sm text-foreground leading-relaxed">{r.diagnostico}</p>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-accent/40 bg-accent/5 p-4 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-accent/15 shrink-0">
              <Lightbulb className="h-4 w-4 sm:h-5 sm:w-5 text-accent" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] sm:text-xs tracking-wider text-muted-foreground uppercase mb-2">Recomendação</p>
              <p className="text-xs sm:text-sm text-foreground leading-relaxed">{r.recomendacao}</p>
            </div>
          </div>
        </div>
      </div>

      {(r.eixo_tematico || r.tempo_escrita_min || r.repertorios || r.observacoes) && (
        <div className="rounded-lg border border-border bg-card p-4 sm:p-6 mt-4 sm:mt-6">
          <p className="text-[10px] sm:text-xs font-medium tracking-wider text-muted-foreground uppercase mb-3">
            Informações Adicionais
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 text-sm">
            {r.eixo_tematico && (
              <div>
                <p className="text-[9px] sm:text-[10px] text-muted-foreground uppercase tracking-wider">Eixo Temático</p>
                <p className="text-foreground text-xs sm:text-sm">{r.eixo_tematico}</p>
              </div>
            )}
            {r.tempo_escrita_min && (
              <div>
                <p className="text-[9px] sm:text-[10px] text-muted-foreground uppercase tracking-wider">Tempo de Escrita</p>
                <p className="text-foreground text-xs sm:text-sm">{r.tempo_escrita_min} min</p>
              </div>
            )}
            {r.repertorios && (
              <div>
                <p className="text-[9px] sm:text-[10px] text-muted-foreground uppercase tracking-wider">Repertórios</p>
                <p className="text-foreground text-xs sm:text-sm">{r.repertorios}</p>
              </div>
            )}
            {r.observacoes && (
              <div className="sm:col-span-2">
                <p className="text-[9px] sm:text-[10px] text-muted-foreground uppercase tracking-wider">Observações</p>
                <p className="text-foreground text-xs sm:text-sm">{r.observacoes}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </AppLayout>
  );
}
