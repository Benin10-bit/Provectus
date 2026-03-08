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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Formulário */}
        <div>
          <h1 className="text-2xl font-bold tracking-wider text-foreground uppercase mb-1">
            Simulado Semanal
          </h1>
          <p className="text-sm text-muted-foreground mb-8">Simule ambiente de pressão e monitore evolução.</p>

          {resultado !== null && (
            <div className={`mb-6 p-4 rounded-md border ${resultado >= 70 ? "border-success/50 bg-success/10" : "border-critical/50 bg-critical/10"}`}>
              <p className={`text-lg font-bold font-mono ${resultado >= 70 ? "text-success" : "text-critical"}`}>
                {resultado}% de acerto
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
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
            <div className="grid grid-cols-2 gap-4">
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
            <div className="grid grid-cols-3 gap-4">
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
              className="w-full py-3 rounded-md bg-primary text-primary-foreground font-semibold tracking-wider uppercase text-sm hover:bg-olive-light transition-colors disabled:opacity-50">
              {mutation.isPending ? "Registrando..." : "Registrar Simulado"}
            </button>
          </form>
        </div>

        {/* Listagem */}
        <div>
          <h2 className="text-lg font-bold tracking-wider text-foreground uppercase mb-4">Histórico de Simulados</h2>
          {loadingSimulados ? <LoadingState /> : (!simulados || simulados.length === 0) ? <EmptyState /> : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {simulados.map((s) => (
                <div key={s.id} className="rounded-md border border-border bg-card p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-foreground">Ciclo {s.numero_ciclo} — Semana {s.numero_semana}</p>
                    <p className="text-xs text-muted-foreground">
                      {s.total_acertos}/{s.total_questoes} • {Math.round(s.tempo_total_segundos / 60)}min • Ans: {s.nivel_ansiedade ?? "—"} • Fad: {s.nivel_fadiga ?? "—"} • Sono: {s.qualidade_sono ?? "—"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-bold font-mono ${s.percentual_acerto >= 70 ? "text-success" : "text-critical"}`}>
                      {s.percentual_acerto}%
                    </p>
                    <p className="text-xs text-muted-foreground font-mono">{new Date(s.criado_em).toLocaleDateString("pt-BR")}</p>
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
      <label className="block text-xs font-medium tracking-wider text-muted-foreground uppercase mb-1.5">{label}</label>
      {children}
    </div>
  );
}
