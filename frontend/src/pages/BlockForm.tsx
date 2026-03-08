import { useState } from "react";
import { toast } from "sonner";
import AppLayout from "@/components/layout/AppLayout";
import { MateriaSelect, AssuntoSelect } from "@/components/form/Selectors";
import { LoadingState, EmptyState } from "@/components/ui/states";
import { useCreateBloco, useBlocos } from "@/hooks/usePerformance";
import { useMaterias } from "@/hooks/useConfiguracoes";
import type { BlocoQuestoesCreate } from "@/lib/types";

export default function BlockPage() {
  const [materiaId, setMateriaId] = useState("");
  const [assuntoId, setAssuntoId] = useState("");
  const [dificuldade, setDificuldade] = useState(3);
  const [totalQ, setTotalQ] = useState("");
  const [totalA, setTotalA] = useState("");
  const [tempo, setTempo] = useState("");
  const [confianca, setConfianca] = useState(3);
  const [resultado, setResultado] = useState<{ pct: number; critico: boolean } | null>(null);

  const { data: materias } = useMaterias();
  const { data: blocos, isLoading: loadingBlocos } = useBlocos();

  const resetForm = () => {
    setMateriaId(""); setAssuntoId(""); setTotalQ(""); setTotalA(""); setTempo(""); setDificuldade(3); setConfianca(3);
  };

  const mutation = useCreateBloco((pct) => {
    setResultado({ pct, critico: pct < 70 });
    resetForm();
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setResultado(null);
    if (!materiaId || !assuntoId || !totalQ || !totalA || !tempo) {
      toast.error("Preencha todos os campos obrigatórios.");
      return;
    }
    const tq = parseInt(totalQ);
    const ta = parseInt(totalA);
    if (ta > tq) { toast.error("Acertos não podem ser maiores que o total."); return; }

    const data: BlocoQuestoesCreate = {
      materia_id: materiaId,
      assunto_id: assuntoId,
      dificuldade,
      total_questoes: tq,
      total_acertos: ta,
      tempo_total_segundos: parseInt(tempo) * 60,
      nivel_confianca_medio: confianca,
    };
    mutation.mutate(data);
  };

  const getMateriaNome = (id: string) => materias?.find((m) => m.id === id)?.nome ?? id;

  return (
    <AppLayout>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Formulário */}
        <div>
          <h1 className="text-2xl font-bold tracking-wider text-foreground uppercase mb-1">
            Bloco de Questões
          </h1>
          <p className="text-sm text-muted-foreground mb-8">Controle seu volume e precisão por assunto.</p>

          {resultado && (
            <div className={`mb-6 p-4 rounded-md border ${resultado.critico ? "border-critical/50 bg-critical/10" : "border-success/50 bg-success/10"}`}>
              <p className={`text-lg font-bold font-mono ${resultado.critico ? "text-critical" : "text-success"}`}>
                {resultado.pct}% de acerto
              </p>
              <p className="text-xs text-muted-foreground">
                {resultado.critico ? "Assunto marcado como CRÍTICO" : "Performance dentro do esperado"}
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <FieldGroup label="Matéria">
              <MateriaSelect value={materiaId} onChange={(v) => { setMateriaId(v); setAssuntoId(""); }} />
            </FieldGroup>
            <FieldGroup label="Assunto">
              <AssuntoSelect materiaId={materiaId} value={assuntoId} onChange={setAssuntoId} />
            </FieldGroup>
            <FieldGroup label={`Dificuldade: ${dificuldade}`}>
              <input type="range" min={1} max={5} value={dificuldade} onChange={(e) => setDificuldade(+e.target.value)} className="w-full accent-accent" />
            </FieldGroup>
            <div className="grid grid-cols-2 gap-4">
              <FieldGroup label="Total de Questões">
                <input type="number" min={1} value={totalQ} onChange={(e) => setTotalQ(e.target.value)} className="form-input" placeholder="Ex: 20" />
              </FieldGroup>
              <FieldGroup label="Total de Acertos">
                <input type="number" min={0} value={totalA} onChange={(e) => setTotalA(e.target.value)} className="form-input" placeholder="Ex: 15" />
              </FieldGroup>
            </div>
            <FieldGroup label="Tempo Total (minutos)">
              <input type="number" min={1} value={tempo} onChange={(e) => setTempo(e.target.value)} className="form-input" placeholder="Ex: 30" />
            </FieldGroup>
            <FieldGroup label={`Confiança Média: ${confianca}`}>
              <input type="range" min={1} max={5} value={confianca} onChange={(e) => setConfianca(+e.target.value)} className="w-full accent-accent" />
            </FieldGroup>
            <button type="submit" disabled={mutation.isPending}
              className="w-full py-3 rounded-md bg-primary text-primary-foreground font-semibold tracking-wider uppercase text-sm hover:bg-olive-light transition-colors disabled:opacity-50">
              {mutation.isPending ? "Registrando..." : "Registrar Bloco"}
            </button>
          </form>
        </div>

        {/* Listagem */}
        <div>
          <h2 className="text-lg font-bold tracking-wider text-foreground uppercase mb-4">Histórico de Blocos</h2>
          {loadingBlocos ? <LoadingState /> : (!blocos || blocos.length === 0) ? <EmptyState /> : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {blocos.map((b) => (
                <div key={b.id} className="rounded-md border border-border bg-card p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{getMateriaNome(b.materia_id)}</p>
                    <p className="text-xs text-muted-foreground">
                      {b.total_acertos}/{b.total_questoes} • Dif: {b.dificuldade} • {Math.round(b.tempo_total_segundos / 60)}min
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-bold font-mono ${b.percentual_acerto >= 70 ? "text-success" : "text-critical"}`}>
                      {b.percentual_acerto}%
                    </p>
                    <p className="text-xs text-muted-foreground font-mono">{new Date(b.criado_em).toLocaleDateString("pt-BR")}</p>
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
