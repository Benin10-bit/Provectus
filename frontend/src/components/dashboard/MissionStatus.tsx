import type { CriticalTopic } from "@/lib/types";
import { Link } from "react-router-dom";
import { Shield, AlertTriangle, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MissionStatusProps {
  status: string;
  academic?: string;
  academicVariant?: string;
  details?: CriticalTopic[];
  context?: string;
  variant?: string;
  tendencia: string;
  assuntosCriticos: string[];
}

export default function MissionStatus({ status, variant, tendencia, assuntosCriticos, academic, academicVariant, details, context }: MissionStatusProps) {
  variant = academic ? academicVariant : variant;
  const isCumprida = variant === "success";
  const TendIcon = tendencia === "ASCENDENTE" ? TrendingUp : tendencia === "DECLÍNIO" ? TrendingDown : Minus;
  const tendColor = tendencia === "ASCENDENTE" ? "text-success" : tendencia === "DECLÍNIO" ? "text-critical" : "text-muted-foreground";
  const tendBg = tendencia === "ASCENDENTE" ? "bg-success/10 border-success/30" : tendencia === "DECLÍNIO" ? "bg-critical/10 border-critical/30" : "bg-secondary border-border";

  return (
    <div className="tac-card mission-status h-full flex flex-col" data-tone={variant === "success" || variant === "warning" || variant === "critical" ? variant : "default"}>
      {/* Status header */}
      <div className="flex items-center gap-3 mb-4">
        <div className={`relative p-2.5 rounded-lg ${isCumprida ? "bg-success/10" : "bg-accent/10"}`}>
          <Shield className={`h-5 w-5 ${isCumprida ? "text-success" : "text-accent"}`} />
          <span className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full animate-pulse-glow ${isCumprida ? "bg-success" : "bg-accent"}`} />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] tracking-[0.2em] text-muted-foreground uppercase">Situação acadêmica</p>
          <p className={`text-base sm:text-lg font-bold tracking-wide ${isCumprida ? "text-success" : "text-accent"}`}>
            {academic || (assuntosCriticos.length ? 'ASSUNTOS EXIGEM ATENÇÃO' : 'CONSULTE SEUS RESULTADOS')}
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
          Assuntos críticos
          {assuntosCriticos.length > 0 && (
            <span className="ml-auto px-1.5 py-0.5 rounded-md bg-critical/15 text-critical text-[9px] font-mono">
              {assuntosCriticos.length}
            </span>
          )}
        </p>
        {details && details.length > 0 ? <ul className="space-y-3">{details.map(t => <li key={t.assunto_id} className="rounded-lg border border-critical/20 p-3">
          <p className="text-xs text-muted-foreground">{t.materia}</p><p className="text-sm font-semibold text-critical">{t.assunto}</p>
          <p className="text-xs text-muted-foreground mt-1">{t.precisao}% · {t.questoes} questões · {t.registros} registros</p>
          <Link to={t.destino} className="text-xs text-accent inline-block mt-2">Preparar revisão ↗</Link>
        </li>)}</ul> : assuntosCriticos.length === 0 ? (
          <p className="text-xs text-muted-foreground">{context || "Nenhum alerta com a amostra mínima neste período. Isso não comprova domínio."}</p>
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
                <span className="break-words">{a}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <Link to="/revisao" className="mission-review-link">Consultar lista de revisão <span aria-hidden>↗</span></Link>
    </div>
  );
}
