import FieldGroup from "@/components/experience/FieldGroup";
import { FormSection } from "@/components/experience/StudyUI";
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
  const [focoSet, setFocoSet] = useState(false);
  const [foco, setFoco] = useState(3);
  const [energiaSet, setEnergiaSet] = useState(false);
  const [energia, setEnergia] = useState(3);

  const { data: materias } = useMaterias();
  const { data: sessoes, isLoading: loadingSessoes } = useSessoes();

  const resetForm = () => {
    setEnergiaSet(false);
    setFocoSet(false);
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
      nivel_foco: focoSet ? foco : null,
      nivel_energia: energiaSet ? energia : null,
    };
    mutation.mutate(data);
  };

  const getMateriaNome = (id: string) => materias?.find((m) => m.id === id)?.nome ?? id;

  return (
    <AppLayout>
      <div className="record-workspace grid grid-cols-1 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] gap-6 lg:gap-8">
        {/* Formulário */}
        <div>
          <div className="page-header">
            <h1 className="page-title">Sessão de Estudo</h1>
            
          </div>

          <form onSubmit={handleSubmit} className="record-form guided-form" aria-busy={mutation.isPending}>
<FormSection number="01" title="Conteúdo estudado" description="Escolha a matéria e o assunto da sessão." complete={Boolean(materiaId && assuntoId)}>

            <FieldGroup label="Matéria">
              <MateriaSelect value={materiaId} onChange={(v) => { setMateriaId(v); setAssuntoId(""); }} />
            </FieldGroup>

            <FieldGroup label="Assunto">
              <AssuntoSelect materiaId={materiaId} value={assuntoId} onChange={setAssuntoId} />
            </FieldGroup>


</FormSection>
<FormSection number="02" title="Atividade e duração" description="Registre apenas o tempo líquido." complete={Boolean(minutos)}>
            <FieldGroup label="Tipo de Sessão">
              <div className="flex gap-2">
                {(["TEORIA", "REVISAO"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    aria-pressed={tipo === t}
                    onClick={() => setTipo(t)}
                    className={`flex-1 sm:flex-none px-4 py-2.5 rounded-lg text-xs font-medium border transition-all duration-200 ${
                      tipo === t
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-secondary text-secondary-foreground border-border hover:bg-muted hover:border-muted-foreground/30"
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


</FormSection>
<FormSection number="03" title="Como foi a sessão" description="Foco e energia são opcionais." complete={focoSet || energiaSet}>
            <div className="grid grid-cols-2 gap-3 sm:gap-4">
              <FieldGroup label={`Foco: ${focoSet ? foco : "não informado (opcional)"}`}>
                <input type="range" min={1} max={5} value={foco} onChange={(e) => {setFocoSet(true); setFoco(+e.target.value);}} className="w-full accent-accent" />
              </FieldGroup>
              <FieldGroup label={`Energia: ${energiaSet ? energia : "não informado (opcional)"}`}>
                <input type="range" min={1} max={5} value={energia} onChange={(e) => {setEnergiaSet(true); setEnergia(+e.target.value);}} className="w-full accent-accent" />
              </FieldGroup>
            </div>


</FormSection>
<div className="form-submit-zone"><p>Confira os dados antes de registrar.</p>            <button
              type="submit"
              disabled={mutation.isPending}
              className="btn-tactical"
            >
              {mutation.isPending ? "Registrando..." : "Registrar Sessão"}
            </button>
          </div></form>
        </div>

        {/* Listagem */}
        <div>
          <h2 className="text-base sm:text-lg font-bold tracking-wider text-foreground uppercase mb-4">Histórico de Sessões</h2>
          {loadingSessoes ? <LoadingState /> : (!sessoes || sessoes.length === 0) ? <EmptyState /> : (
            <div className="space-y-2 max-h-[500px] lg:max-h-[600px] overflow-y-auto pr-1">
              {sessoes.map((s) => (
                <div key={s.id} className="rounded-lg border border-border bg-card/80 hover:bg-card p-3 sm:p-4 flex items-center justify-between gap-3 transition-all hover:border-accent/40 hover:translate-x-0.5">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-foreground truncate">{getMateriaNome(s.materia_id)}</p>
                    <p className="text-[10px] sm:text-xs text-muted-foreground truncate">{s.tipo_sessao} • {s.minutos_liquidos} min • Foco: {s.nivel_foco ?? "—"} • Energia: {s.nivel_energia ?? "—"}</p>
                  </div>
                  <p className="text-[10px] sm:text-xs text-muted-foreground font-mono shrink-0">{new Date(s.criado_em).toLocaleDateString("pt-BR")}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

