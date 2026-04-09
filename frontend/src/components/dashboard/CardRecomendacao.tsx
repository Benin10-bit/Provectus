import { useState } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";

export default function CardRecomendacao({ d }: { d: any }) {
  const [open, setOpen] = useState(false);
  const isCumprida = d.status_missao === "MISSÃO CUMPRIDA";

  return (
    <div
      className={`rounded-lg border p-5 sm:p-6 mb-6 transition-all duration-300 ${
        isCumprida
          ? "border-success/40 bg-success/5"
          : "border-critical/40 bg-critical/5"
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg shrink-0 ${isCumprida ? "bg-success/15" : "bg-critical/15"}`}>
          <Lightbulb className={`h-5 w-5 ${isCumprida ? "text-success" : "text-critical"}`} />
        </div>

        <div className="w-full min-w-0">
          <p className="text-[10px] tracking-wider text-muted-foreground uppercase mb-2">
            Recomendação Estratégica
          </p>

          {d.recomendacao && d.recomendacao.length > 0 && (
            <div className="flex items-start justify-between gap-3 mb-2">
              <p className={`text-base sm:text-lg font-bold leading-snug ${isCumprida ? "text-success" : "text-critical"}`}>
                • {d.recomendacao[0]}
              </p>

              {d.recomendacao.length > 1 && (
                <button
                  onClick={() => setOpen(!open)}
                  className="flex items-center gap-1 text-xs font-semibold transition text-muted-foreground hover:opacity-70 shrink-0 mt-1"
                >
                  <ChevronDown
                    className={`h-4 w-4 transition-transform duration-300 ${open ? "rotate-180" : ""}`}
                  />
                  <span className="hidden sm:inline">{open ? "Ocultar" : "Ver mais"}</span>
                </button>
              )}
            </div>
          )}

          <div
            className={`grid transition-all duration-300 ease-in-out ${
              open
                ? "grid-rows-[1fr] opacity-100 mb-2"
                : "grid-rows-[0fr] opacity-0 mb-0"
            }`}
          >
            <div className="overflow-hidden">
              <ul className={`text-sm font-medium space-y-1 pb-1 ${isCumprida ? "text-success/80" : "text-critical/80"}`}>
                {d.recomendacao?.slice(1).map((rec: string, index: number) => (
                  <li key={index}>• {rec}</li>
                ))}
              </ul>
            </div>
          </div>

          <p className="text-xs sm:text-sm text-muted-foreground">{d.status_missao}</p>
        </div>
      </div>
    </div>
  );
}
