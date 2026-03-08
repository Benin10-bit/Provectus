import { Shield, AlertTriangle } from "lucide-react";

interface MissionStatusProps {
  status: string;
  tendencia: string;
  assuntosCriticos: string[];
}

export default function MissionStatus({ status, tendencia, assuntosCriticos }: MissionStatusProps) {
  const isCumprida = status === "MISSÃO CUMPRIDA";

  return (
    <div className="rounded-md border border-border bg-card p-5 animate-slide-in">
      {/* Status */}
      <div className="flex items-center gap-3 mb-4">
        <Shield className={`h-6 w-6 ${isCumprida ? "text-success" : "text-critical"}`} />
        <div>
          <p className="text-xs tracking-wider text-muted-foreground uppercase">Status da Missão</p>
          <p className={`text-lg font-bold tracking-wide ${isCumprida ? "text-success" : "text-critical"}`}>
            {status}
          </p>
        </div>
      </div>

      {/* Tendência */}
      <div className="mb-4 px-3 py-2 rounded bg-secondary">
        <p className="text-xs text-muted-foreground uppercase tracking-wider">Tendência</p>
        <p className={`text-sm font-semibold ${
          tendencia === "ASCENDENTE" ? "text-success" : tendencia === "DECLÍNIO" ? "text-critical" : "text-warning"
        }`}>
          ▸ {tendencia}
        </p>
      </div>

      {/* Assuntos Críticos */}
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3 text-critical" />
          Assuntos Críticos
        </p>
        {assuntosCriticos.length === 0 ? (
          <p className="text-xs text-success">Nenhum assunto crítico identificado.</p>
        ) : (
          <ul className="space-y-1">
            {assuntosCriticos.map((a, i) => (
              <li key={i} className="text-xs text-critical flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-critical inline-block" />
                {a}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
