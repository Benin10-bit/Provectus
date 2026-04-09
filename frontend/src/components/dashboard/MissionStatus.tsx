import { Shield, AlertTriangle } from "lucide-react";

interface MissionStatusProps {
  status: string;
  tendencia: string;
  assuntosCriticos: string[];
}

export default function MissionStatus({ status, tendencia, assuntosCriticos }: MissionStatusProps) {
  const isCumprida = status === "MISSÃO CUMPRIDA";

  return (
    <div className="rounded-lg border border-border bg-card p-5 h-full flex flex-col">
      {/* Status */}
      <div className="flex items-center gap-3 mb-4">
        <div className={`p-2 rounded-lg ${isCumprida ? "bg-success/10" : "bg-critical/10"}`}>
          <Shield className={`h-5 w-5 ${isCumprida ? "text-success" : "text-critical"}`} />
        </div>
        <div>
          <p className="text-[10px] tracking-wider text-muted-foreground uppercase">Status da Missão</p>
          <p className={`text-base sm:text-lg font-bold tracking-wide ${isCumprida ? "text-success" : "text-critical"}`}>
            {status}
          </p>
        </div>
      </div>

      {/* Tendência */}
      <div className="mb-4 px-3 py-2.5 rounded-lg bg-secondary/60 border border-border/50">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Tendência</p>
        <p className={`text-sm font-semibold ${
          tendencia === "ASCENDENTE" ? "text-success" : tendencia === "DECLÍNIO" ? "text-critical" : "text-warning"
        }`}>
          ▸ {tendencia}
        </p>
      </div>

      {/* Assuntos Críticos */}
      <div className="flex-1">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <AlertTriangle className="h-3 w-3 text-critical" />
          Assuntos Críticos
        </p>
        {assuntosCriticos.length === 0 ? (
          <p className="text-xs text-success/80">Nenhum assunto crítico identificado.</p>
        ) : (
          <ul className="space-y-1.5">
            {assuntosCriticos.map((a, i) => (
              <li key={i} className="text-xs text-critical/90 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-critical/70 inline-block shrink-0" />
                <span className="truncate">{a}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
