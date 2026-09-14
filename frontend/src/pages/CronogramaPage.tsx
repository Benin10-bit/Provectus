import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { CRONOGRAMA, DIAS_ORDEM, DIAS_LABEL, getDiaAtual, isHorarioAtual, type DiaSemana } from "@/lib/cronograma";
import { Clock } from "lucide-react";

export default function CronogramaPage() {
  const [now, setNow] = useState(new Date());
  const diaHoje = getDiaAtual(now);
  const [diaSelecionado, setDiaSelecionado] = useState<DiaSemana>(diaHoje);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(t);
  }, []);

  const horaAtualStr = now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  return (
    <AppLayout>
      <div className="page-header flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="page-title">Cronograma Semanal</h1>
          <p className="page-subtitle">Plano tático de execução por dia.</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-card text-xs font-mono">
          <Clock className="h-3.5 w-3.5 text-accent" />
          <span className="uppercase tracking-wider text-muted-foreground">{DIAS_LABEL[diaHoje].full}</span>
          <span className="text-foreground font-semibold">{horaAtualStr}</span>
        </div>
      </div>

      {/* MOBILE/TABLET: seletor de dias em chips */}
      <div className="xl:hidden flex gap-1.5 mb-4 overflow-x-auto pb-2 -mx-1 px-1">
        {DIAS_ORDEM.map((d) => {
          const isToday = d === diaHoje;
          const isActive = d === diaSelecionado;
          return (
            <button
              key={d}
              onClick={() => setDiaSelecionado(d)}
              className={`relative shrink-0 px-3 py-2 rounded-lg text-[11px] font-bold tracking-wider uppercase transition-all duration-200 active:scale-95 ${
                isActive
                  ? "bg-primary text-primary-foreground hud-glow"
                  : "bg-card border border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {DIAS_LABEL[d].short}
              {isToday && (
                <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-accent animate-pulse-glow" />
              )}
            </button>
          );
        })}
      </div>

      {/* MOBILE/TABLET: lista do dia selecionado */}
      <div className="xl:hidden space-y-2 animate-fade-in">
        <DayList dia={diaSelecionado} now={now} isToday={diaSelecionado === diaHoje} />
      </div>

      {/* DESKTOP (xl+): grid semanal */}
      <div className="hidden xl:grid grid-cols-7 gap-3">
        {DIAS_ORDEM.map((d) => {
          const isToday = d === diaHoje;
          const items = CRONOGRAMA[d];
          return (
            <div
              key={d}
              className={`tac-card flex flex-col rounded-lg border bg-card overflow-hidden transition-all ${
                isToday ? "border-accent/60 shadow-[0_0_20px_-5px_hsl(var(--accent)/0.4)]" : "border-border"
              }`}
            >
              <div
                className={`px-3 py-2.5 border-b text-center ${
                  isToday ? "border-accent/40 bg-accent/10" : "border-border bg-muted/30"
                }`}
              >
                <p className={`text-[10px] tracking-[0.2em] font-bold uppercase ${isToday ? "text-accent" : "text-muted-foreground"}`}>
                  {DIAS_LABEL[d].short}
                </p>
                {isToday && (
                  <span className="inline-block mt-1 text-[8px] font-mono tracking-widest text-accent uppercase">
                    ● Hoje
                  </span>
                )}
              </div>

              <div className="flex-1 p-2 space-y-1.5">
                {items.length === 0 ? (
                  <p className="text-center text-[10px] text-muted-foreground/60 italic py-4">Livre</p>
                ) : (
                  items.map((it, i) => {
                    const ativo = isToday && isHorarioAtual(it.horario, now);
                    return (
                      <div
                        key={i}
                        className={`relative rounded-md px-2 py-1.5 border transition-all duration-300 ${
                          ativo
                            ? "border-accent bg-accent/15 shadow-[0_0_15px_-3px_hsl(var(--accent)/0.6)] animate-pulse-glow"
                            : "border-border/60 bg-background/40 hover:border-border"
                        }`}
                      >
                        {ativo && (
                          <span className="absolute -left-px top-1/2 -translate-y-1/2 h-3/5 w-0.5 bg-accent rounded-r" />
                        )}
                        <p className={`text-[10px] font-mono tracking-tight ${ativo ? "text-accent font-bold" : "text-muted-foreground"}`}>
                          {it.horario}
                        </p>
                        <p className={`text-xs leading-tight mt-0.5 ${ativo ? "text-foreground font-semibold" : "text-foreground/85"}`}>
                          {it.atividade}
                        </p>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </AppLayout>
  );
}

function DayList({ dia, now, isToday }: { dia: DiaSemana; now: Date; isToday: boolean }) {
  const items = CRONOGRAMA[dia];
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-center">
        <p className="text-sm text-muted-foreground italic">Sem atividades programadas.</p>
      </div>
    );
  }
  return (
    <>
      {items.map((it, i) => {
        const ativo = isToday && isHorarioAtual(it.horario, now);
        return (
          <div
            key={i}
            className={`relative flex items-center gap-3 rounded-lg border p-3 transition-all duration-300 ${
              ativo
                ? "border-accent bg-accent/10 shadow-[0_0_18px_-4px_hsl(var(--accent)/0.5)]"
                : "border-border bg-card"
            }`}
          >
            {ativo && <span className="absolute left-0 top-2 bottom-2 w-1 bg-accent rounded-r" />}
            <div className={`shrink-0 px-2.5 py-1.5 rounded-md font-mono text-xs tracking-tight ${
              ativo ? "bg-accent/20 text-accent font-bold" : "bg-muted/40 text-muted-foreground"
            }`}>
              {it.horario}
            </div>
            <p className={`text-sm flex-1 ${ativo ? "text-foreground font-semibold" : "text-foreground/85"}`}>
              {it.atividade}
            </p>
            {ativo && (
              <span className="shrink-0 text-[9px] font-bold tracking-widest text-accent uppercase animate-pulse-glow">
                ● Agora
              </span>
            )}
          </div>
        );
      })}
    </>
  );
}
