import { useState } from "react";
import { toast } from "sonner";
import AppLayout from "@/components/layout/AppLayout";
import { LoadingState, EmptyState } from "@/components/ui/states";
import { useCreateSimulado, useSimulados } from "@/hooks/usePerformance";
import type { SimuladoSemanalCreate } from "@/lib/types";

export default function ExamPage() {
  const [ciclo, setCiclo] = useState("");
  const [semana, setSemana] = useState("");
  const [totalQ, setTotalQ] = useState("");
  const [totalA, setTotalA] = useState("");
  const [tempo, setTempo] = useState("");
  const [ansiedade, setAnsiedade] = useState(3);
  const [fadiga, setFadiga] = useState(3);
  const [sono, setSono] = useState(3);
  const [resultado, setResultado] = useState<number | null>(null);

  const { data: simulados, isLoading: loadingSimulados } = useSimulados();

  const resetForm = () => {
    setCiclo(""); setSemana(""); setTotalQ(""); setTotalA(""); setTempo("");
    setAnsiedade(3); setFadiga(3); setSono(3);
  };

  const mutation = useCreateSimulado((pct) => {
    setResultado(pct);
    resetForm();
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setResultado(null);
    if (!ciclo || !semana || !totalQ || !totalA || !tempo) {
      toast.error("Preencha todos os campos obrigatórios.");
      return;
    }
    const tq = parseInt(totalQ);
    const ta = parseInt(totalA);
    if (ta > tq) { toast.error("Acertos não podem ser maiores que o total."); return; }

    const data: SimuladoSemanalCreate = {
      numero_ciclo: parseInt(ciclo),
      numero_semana: parseInt(semana),
      total_questoes: tq,
      total_acertos: ta,
      tempo_total_segundos: parseInt(tempo) * 60,
      nivel_ansiedade: ansiedade,
      nivel_fadiga: fadiga,
      qualidade_sono: sono,
    };
    mutation.mutate(data);
  };

  return (
    <AppLayout>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
        <div>
          <div className="page-header">
            <h1 className="page-title">Simulado Semanal</h1>
            <p className="page-subtitle">Simule ambiente de pressão e monitore evolução.</p>
          </div>

          {resultado !== null && (
            <div className={`mb-6 p-4 rounded-lg border transition-all duration-300 ${resultado >= 70 ? "border-success/40 bg-success/10" : "border-critical/40 bg-critical/10"}`}>
              <p className={`text-lg font-bold font-mono ${resultado >= 70 ? "text-success" : "text-critical"}`}>
                {resultado}% de acerto
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
            <div className="grid grid-cols-2 gap-3 sm:gap-4">
              <FieldGroup label="Número do Ciclo">
                <input type="number" min={1} value={ciclo} onChange={(e) => setCiclo(e.target.value)} className="form-input" placeholder="Ex: 1" />
              </FieldGroup>
              <FieldGroup label="Número da Semana">
                <select value={semana} onChange={(e) => setSemana(e.target.value)} className="form-select">
                  <option value="">Selecione...</option>
                  {[1, 2, 3, 4].map((n) => <option key={n} value={n}>Semana {n}</option>)}
                </select>
              </FieldGroup>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:gap-4">
              <FieldGroup label="Total de Questões">
                <input type="number" min={1} value={totalQ} onChange={(e) => setTotalQ(e.target.value)} className="form-input" placeholder="Ex: 60" />
              </FieldGroup>
              <FieldGroup label="Total de Acertos">
                <input type="number" min={0} value={totalA} onChange={(e) => setTotalA(e.target.value)} className="form-input" placeholder="Ex: 45" />
              </FieldGroup>
            </div>
            <FieldGroup label="Tempo Total (minutos)">
              <input type="number" min={1} value={tempo} onChange={(e) => setTempo(e.target.value)} className="form-input" placeholder="Ex: 180" />
            </FieldGroup>
            <div className="grid grid-cols-3 gap-2 sm:gap-4">
              <FieldGroup label={`Ansiedade: ${ansiedade}`}>
                <input type="range" min={1} max={5} value={ansiedade} onChange={(e) => setAnsiedade(+e.target.value)} className="w-full accent-accent" />
              </FieldGroup>
              <FieldGroup label={`Fadiga: ${fadiga}`}>
                <input type="range" min={1} max={5} value={fadiga} onChange={(e) => setFadiga(+e.target.value)} className="w-full accent-accent" />
              </FieldGroup>
              <FieldGroup label={`Sono: ${sono}`}>
                <input type="range" min={1} max={5} value={sono} onChange={(e) => setSono(+e.target.value)} className="w-full accent-accent" />
              </FieldGroup>
            </div>
            <button type="submit" disabled={mutation.isPending}
              className="btn-tactical">
              {mutation.isPending ? "Registrando..." : "Registrar Simulado"}
            </button>
          </form>
        </div>

        <div>
          <h2 className="text-base sm:text-lg font-bold tracking-wider text-foreground uppercase mb-4">Histórico de Simulados</h2>
          {loadingSimulados ? <LoadingState /> : (!simulados || simulados.length === 0) ? <EmptyState /> : (
            <div className="space-y-2 max-h-[500px] lg:max-h-[600px] overflow-y-auto pr-1">
              {simulados.map((s) => (
                <div key={s.id} className="rounded-lg border border-border bg-card/80 hover:bg-card p-3 sm:p-4 flex items-center justify-between gap-3 transition-all hover:border-accent/40 hover:translate-x-0.5">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-foreground truncate">Ciclo {s.numero_ciclo} — Semana {s.numero_semana}</p>
                    <p className="text-[10px] sm:text-xs text-muted-foreground truncate">
                      {s.total_acertos}/{s.total_questoes} • {Math.round(s.tempo_total_segundos / 60)}min • Ans: {s.nivel_ansiedade ?? "—"} • Fad: {s.nivel_fadiga ?? "—"}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className={`text-sm font-bold font-mono ${s.percentual_acerto >= 70 ? "text-success" : "text-critical"}`}>
                      {s.percentual_acerto}%
                    </p>
                    <p className="text-[10px] text-muted-foreground font-mono">{new Date(s.criado_em).toLocaleDateString("pt-BR")}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[10px] sm:text-xs font-medium tracking-wider text-muted-foreground uppercase mb-1.5">{label}</label>
      {children}
    </div>
  );
}
