import { useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import { useSessoes, useBlocos, useSimulados } from "@/hooks/usePerformance";
import { useMaterias, useAssuntos } from "@/hooks/useConfiguracoes";

type Tab = "sessoes" | "blocos" | "simulados";

export default function HistoryPage() {
  const [tab, setTab] = useState<Tab>("sessoes");

  const { data: materias } = useMaterias();
  const { data: assuntos } = useAssuntos();
  const { data: sessoes, isLoading: lS, isError: eS } = useSessoes();
  const { data: blocos, isLoading: lB, isError: eB } = useBlocos();
  const { data: simulados, isLoading: lSim, isError: eSim } = useSimulados();

  const getMateriaNome = (id: string) => materias?.find((m) => m.id === id)?.nome ?? id;
  const getAssuntoNome = (id: string) => assuntos?.find((a) => a.id === id)?.nome ?? id;

  const tabs: { key: Tab; label: string }[] = [
    { key: "sessoes", label: "Sessões" },
    { key: "blocos", label: "Blocos" },
    { key: "simulados", label: "Simulados" },
  ];

  return (
    <AppLayout>
      <div className="page-header">
        <h1 className="page-title">Histórico</h1>
        <p className="page-subtitle">Registros completos de execução.</p>
      </div>

      <div className="flex gap-1 mb-6 border-b border-border overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-xs font-medium tracking-wider uppercase transition-all duration-200 whitespace-nowrap ${
              tab === t.key
                ? "text-accent border-b-2 border-accent"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "sessoes" && (
        lS ? <LoadingState /> : eS ? <ErrorState /> : (!sessoes || sessoes.length === 0) ? <EmptyState /> : (
          <div className="space-y-2">
            {sessoes.map((s) => (
              <div key={s.id} className="rounded-lg border border-border bg-card/80 hover:bg-card p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 transition-all hover:border-accent/40 hover:translate-x-0.5">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-foreground truncate">
                    {getMateriaNome(s.materia_id)}{" "}
                    <span className="font-normal text-muted-foreground">— {getAssuntoNome(s.assunto_id)}</span>
                  </p>
                  <p className="text-[10px] sm:text-xs text-muted-foreground truncate">
                    {s.tipo_sessao} • {s.minutos_liquidos} min • Foco: {s.nivel_foco ?? "—"} • Energia: {s.nivel_energia ?? "—"}
                  </p>
                </div>
                <p className="text-[10px] sm:text-xs text-muted-foreground font-mono shrink-0">{new Date(s.criado_em).toLocaleDateString("pt-BR")}</p>
              </div>
            ))}
          </div>
        )
      )}

      {tab === "blocos" && (
        lB ? <LoadingState /> : eB ? <ErrorState /> : (!blocos || blocos.length === 0) ? <EmptyState /> : (
          <div className="space-y-2">
            {blocos.map((b) => (
              <div key={b.id} className="rounded-lg border border-border bg-card/80 hover:bg-card p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 transition-all hover:border-accent/40 hover:translate-x-0.5">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-foreground truncate">
                    {getMateriaNome(b.materia_id)}{" "}
                    <span className="font-normal text-muted-foreground">— {getAssuntoNome(b.assunto_id)}</span>
                  </p>
                  <p className="text-[10px] sm:text-xs text-muted-foreground truncate">
                    {b.total_acertos}/{b.total_questoes} • Dif: {b.dificuldade} • {Math.round(b.tempo_total_segundos / 60)}min • Tempo/Q: {b.tempo_medio_por_questao}s
                  </p>
                </div>
                <div className="flex items-center gap-3 sm:text-right shrink-0">
                  <p className={`text-sm font-bold font-mono ${b.percentual_acerto >= 70 ? "text-success" : "text-critical"}`}>
                    {b.percentual_acerto}%
                  </p>
                  <p className="text-[10px] text-muted-foreground font-mono">{new Date(b.criado_em).toLocaleDateString("pt-BR")}</p>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {tab === "simulados" && (
        lSim ? <LoadingState /> : eSim ? <ErrorState /> : (!simulados || simulados.length === 0) ? <EmptyState /> : (
          <div className="space-y-2">
            {simulados.map((s) => (
              <div key={s.id} className="rounded-lg border border-border bg-card/80 hover:bg-card p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 transition-all hover:border-accent/40 hover:translate-x-0.5">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-foreground truncate">Ciclo {s.numero_ciclo} — Semana {s.numero_semana}</p>
                  <p className="text-[10px] sm:text-xs text-muted-foreground truncate">
                    {s.total_acertos}/{s.total_questoes} • {Math.round(s.tempo_total_segundos / 60)}min • Ans: {s.nivel_ansiedade ?? "—"} • Fad: {s.nivel_fadiga ?? "—"} • Sono: {s.qualidade_sono ?? "—"}
                  </p>
                </div>
                <div className="flex items-center gap-3 sm:text-right shrink-0">
                  <p className={`text-sm font-bold font-mono ${s.percentual_acerto >= 70 ? "text-success" : "text-critical"}`}>
                    {s.percentual_acerto}%
                  </p>
                  <p className="text-[10px] text-muted-foreground font-mono">{new Date(s.criado_em).toLocaleDateString("pt-BR")}</p>
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </AppLayout>
  );
}
