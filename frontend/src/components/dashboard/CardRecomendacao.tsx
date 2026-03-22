import { useState } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";

export default function CardRecomendacao({ d }) {
    const [open, setOpen] = useState(false);

    return (
        <div
            className={`rounded-md border p-6 mb-6 animate-slide-in transition-colors duration-300 ${
                d.status_missao === "MISSÃO CUMPRIDA"
                    ? "border-success/50 bg-success/10"
                    : "border-critical/50 bg-critical/10"
            }`}
        >
            <div className="flex items-start gap-3">
                <Lightbulb
                    className={`h-6 w-6 mt-0.5 ${
                        d.status_missao === "MISSÃO CUMPRIDA"
                            ? "text-success"
                            : "text-critical"
                    }`}
                />

                <div className="w-full">
                    <p className="text-xs tracking-wider text-muted-foreground uppercase mb-2">
                        Recomendação Estratégica
                    </p>

                    {/* PRIMEIRO ITEM + BOTÃO */}
                    {d.recomendacao && d.recomendacao.length > 0 && (
                        <div className="flex items-start justify-between gap-4 mb-2">
                            <p
                                className={`text-xl font-bold ${
                                    d.status_missao === "MISSÃO CUMPRIDA"
                                        ? "text-success"
                                        : "text-critical"
                                }`}
                            >
                                • {d.recomendacao[0]}
                            </p>

                            {d.recomendacao.length > 1 && (
                                <button
                                    onClick={() => setOpen(!open)}
                                    className="flex items-center gap-1 text-xs font-semibold transition text-muted-foreground hover:opacity-70"
                                >
                                    <ChevronDown
                                        className={`h-4 w-4 transition-transform duration-300 ${
                                            open ? "rotate-180" : ""
                                        }`}
                                    />
                                    {open ? "Ocultar" : "Ver mais"}
                                </button>
                            )}
                        </div>
                    )}

                    {/* CONTEÚDO ANIMADO (RESTAANTE DA LISTA) */}
                    <div
                        className={`grid transition-all duration-300 ease-in-out ${
                            open 
                                ? "grid-rows-[1fr] opacity-100 mb-2" 
                                : "grid-rows-[0fr] opacity-0 mb-0"
                        }`}
                    >
                        <div className="overflow-hidden">
                            <ul
                                className={`text-sm font-medium space-y-1 pb-1 ${
                                    d.status_missao === "MISSÃO CUMPRIDA"
                                        ? "text-success/80"
                                        : "text-critical/80"
                                }`}
                            >
                                {d.recomendacao.slice(1).map((rec, index) => (
                                    <li key={index}>• {rec}</li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* STATUS */}
                    <p className="text-sm text-muted-foreground">
                        {d.status_missao}
                    </p>
                </div>
            </div>
        </div>
    );
}