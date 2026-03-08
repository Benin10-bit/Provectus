import { useState } from "react";
import { toast } from "sonner";
import AppLayout from "@/components/layout/AppLayout";
import { MateriaSelect, AssuntoSelect } from "@/components/form/Selectors";
import { LoadingState, EmptyState } from "@/components/ui/states";
import { useCreateSessao, useSessoes } from "@/hooks/usePerformance";
import { useMaterias } from "@/hooks/useConfiguracoes";
import type { SessaoEstudoCreate } from "@/lib/types";

export default function SessionPage() {
  const [materiaId, setMateriaId] = useState("");
  const [assuntoId, setAssuntoId] = useState("");
  const [tipo, setTipo] = useState<"TEORIA" | "REVISAO">("TEORIA");
  const [minutos, setMinutos] = useState("");
  const [foco, setFoco] = useState(3);
  const [energia, setEnergia] = useState(3);

  const { data: materias } = useMaterias();
  const { data: sessoes, isLoading: loadingSessoes } = useSessoes();

  const resetForm = () => {
    setMateriaId(""); setAssuntoId(""); setMinutos(""); setFoco(3); setEnergia(3);
  };

  const mutation = useCreateSessao(resetForm);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!materiaId || !assuntoId || !minutos) {
      toast.error("Preencha todos os campos obrigatórios.");
      return;
    }
    const data: SessaoEstudoCreate = {
      materia_id: materiaId,
      assunto_id: assuntoId,
      tipo_sessao: tipo,
      minutos_liquidos: parseInt(minutos),
      nivel_foco: foco,
      nivel_energia: energia,
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
            Sessão de Estudo
          </h1>
          <p className="text-sm text-muted-foreground mb-8">Registre cada sessão para monitoramento estratégico.</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <FieldGroup label="Matéria">
              <MateriaSelect value={materiaId} onChange={(v) => { setMateriaId(v); setAssuntoId(""); }} />
            </FieldGroup>

            <FieldGroup label="Assunto">
              <AssuntoSelect materiaId={materiaId} value={assuntoId} onChange={setAssuntoId} />
            </FieldGroup>

            <FieldGroup label="Tipo de Sessão">
              <div className="flex gap-2">
                {(["TEORIA", "REVISAO"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTipo(t)}
                    className={`px-4 py-2 rounded-md text-xs font-medium border transition-all ${
                      tipo === t ? "bg-primary text-primary-foreground border-primary" : "bg-secondary text-secondary-foreground border-border hover:bg-muted"
                    }`}
                  >
                    {t === "REVISAO" ? "Revisão" : "Teoria"}
                  </button>
                ))}
              </div>
            </FieldGroup>

            <FieldGroup label="Minutos Líquidos">
              <input type="number" min={1} value={minutos} onChange={(e) => setMinutos(e.target.value)} className="form-input" placeholder="Ex: 45" />
            </FieldGroup>

            <div className="grid grid-cols-2 gap-4">
              <FieldGroup label={`Nível de Foco: ${foco}`}>
                <input type="range" min={1} max={5} value={foco} onChange={(e) => setFoco(+e.target.value)} className="w-full accent-accent" />
              </FieldGroup>
              <FieldGroup label={`Nível de Energia: ${energia}`}>
                <input type="range" min={1} max={5} value={energia} onChange={(e) => setEnergia(+e.target.value)} className="w-full accent-accent" />
              </FieldGroup>
            </div>

            <button
              type="submit"
              disabled={mutation.isPending}
              className="w-full py-3 rounded-md bg-primary text-primary-foreground font-semibold tracking-wider uppercase text-sm hover:bg-olive-light transition-colors disabled:opacity-50"
            >
              {mutation.isPending ? "Registrando..." : "Registrar Sessão"}
            </button>
          </form>
        </div>

        {/* Listagem */}
        <div>
          <h2 className="text-lg font-bold tracking-wider text-foreground uppercase mb-4">Histórico de Sessões</h2>
          {loadingSessoes ? <LoadingState /> : (!sessoes || sessoes.length === 0) ? <EmptyState /> : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {sessoes.map((s) => (
                <div key={s.id} className="rounded-md border border-border bg-card p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{getMateriaNome(s.materia_id)}</p>
                    <p className="text-xs text-muted-foreground">{s.tipo_sessao} • {s.minutos_liquidos} min • Foco: {s.nivel_foco ?? "—"} • Energia: {s.nivel_energia ?? "—"}</p>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono">{new Date(s.criado_em).toLocaleDateString("pt-BR")}</p>
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
