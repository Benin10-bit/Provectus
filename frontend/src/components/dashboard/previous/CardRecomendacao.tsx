import { useState } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";

export default function CardRecomendacao({ d }: { d: any }) {
  const [open, setOpen] = useState(false);
  const isCumprida = d.variante_missao === "success";

  const recs: string[] = d.recomendacao || [];

  return (
    <div
      className={`relative rounded-lg border p-5 sm:p-6 mb-6 transition-all duration-300 overflow-hidden
        ${isCumprida ? "border-success/40 bg-success/5" : d.variante_missao==='warning' ? "border-warning/40 bg-warning/5" : "border-accent/30 bg-accent/5"}`}
    >
      {/* Side gradient bar */}
      <span className={`absolute top-0 left-0 bottom-0 w-1 ${isCumprida ? "bg-success" : "bg-accent"}`} />
      {/* Soft glow */}
      <div className={`absolute -top-20 -right-20 w-48 h-48 rounded-full blur-3xl opacity-40
        ${isCumprida ? "bg-success/20" : "bg-accent/20"}`} />

      <div className="relative flex items-start gap-3">
        <div className={`p-2.5 rounded-lg shrink-0 ${isCumprida ? "bg-success/15" : "bg-accent/15"}`}>
          <Lightbulb className={`h-5 w-5 ${isCumprida ? "text-success" : "text-accent"}`} />
        </div>

        <div className="w-full min-w-0">
          <p className="text-[10px] tracking-[0.2em] text-muted-foreground uppercase mb-2">
            Recomendação Estratégica
          </p>

          {recs.length > 0 && (
            <div className="flex items-start justify-between gap-3 mb-2">
              <p className={`text-base sm:text-lg font-bold leading-snug ${isCumprida ? "text-success" : "text-accent"}`}>
                ▸ {recs[0]}
              </p>

              {recs.length > 1 && (
                <button aria-label="Expandir ou recolher recomendação"
                  onClick={() => setOpen(!open)}
                  className="flex items-center gap-1 text-xs font-semibold transition text-muted-foreground hover:text-foreground shrink-0 mt-1"
                >
                  <ChevronDown className={`h-4 w-4 transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
                  <span className="hidden sm:inline">{open ? "Ocultar" : `+${recs.length - 1}`}</span>
                </button>
              )}
            </div>
          )}

          <div
            className={`grid transition-all duration-300 ease-in-out ${
              open ? "grid-rows-[1fr] opacity-100 mb-2" : "grid-rows-[0fr] opacity-0 mb-0"
            }`}
          >
            <div className="overflow-hidden">
              <ul className={`text-sm font-medium space-y-1 pb-1 ${isCumprida ? "text-success/80" : "text-accent/80"}`}>
                {recs.slice(1).map((rec, index) => (
                  <li key={index} className="flex gap-2"><span>▸</span><span>{rec}</span></li>
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
