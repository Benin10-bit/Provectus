import { Shield, AlertTriangle, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MissionStatusProps {
  status: string;
  tendencia: string;
  assuntosCriticos: string[];
}

export default function MissionStatus({ status, tendencia, assuntosCriticos }: MissionStatusProps) {
  const isCumprida = status === "MISSÃO CUMPRIDA";
  const TendIcon = tendencia === "ASCENDENTE" ? TrendingUp : tendencia === "DECLÍNIO" ? TrendingDown : Minus;
  const tendColor = tendencia === "ASCENDENTE" ? "text-success" : tendencia === "DECLÍNIO" ? "text-critical" : "text-warning";
  const tendBg = tendencia === "ASCENDENTE" ? "bg-success/10 border-success/30" : tendencia === "DECLÍNIO" ? "bg-critical/10 border-critical/30" : "bg-warning/10 border-warning/30";

  return (
    <div className="tac-card h-full flex flex-col">
      {/* Status header */}
      <div className="flex items-center gap-3 mb-4">
        <div className={`relative p-2.5 rounded-lg ${isCumprida ? "bg-success/10" : "bg-critical/10"}`}>
          <Shield className={`h-5 w-5 ${isCumprida ? "text-success" : "text-critical"}`} />
          <span className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full animate-pulse-glow ${isCumprida ? "bg-success" : "bg-critical"}`} />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] tracking-[0.2em] text-muted-foreground uppercase">Status da Missão</p>
          <p className={`text-base sm:text-lg font-bold tracking-wide ${isCumprida ? "text-success" : "text-critical"}`}>
            {status}
          </p>
        </div>
      </div>

      {/* Tendência */}
      <div className={`mb-4 px-3 py-2.5 rounded-lg border ${tendBg} flex items-center gap-2.5`}>
        <TendIcon className={`h-4 w-4 ${tendColor}`} />
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Tendência</p>
          <p className={`text-sm font-bold ${tendColor}`}>{tendencia}</p>
        </div>
      </div>

      {/* Assuntos críticos */}
      <div className="flex-1">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <AlertTriangle className="h-3 w-3 text-critical" />
          Assuntos Críticos
          {assuntosCriticos.length > 0 && (
            <span className="ml-auto px-1.5 py-0.5 rounded-md bg-critical/15 text-critical text-[9px] font-mono">
              {assuntosCriticos.length}
            </span>
          )}
        </p>
        {assuntosCriticos.length === 0 ? (
          <p className="text-xs text-success/80">Nenhum assunto crítico identificado.</p>
        ) : (
          <ul className="space-y-1.5">
            {assuntosCriticos.map((a, i) => (
              <li
                key={i}
                style={{ animationDelay: `${i * 50}ms` }}
                className="text-xs text-critical/95 flex items-center gap-2 px-2 py-1 rounded-md
                           bg-critical/5 border border-critical/15 animate-slide-in-left"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-critical inline-block shrink-0 animate-pulse-glow" />
                <span className="truncate">{a}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
