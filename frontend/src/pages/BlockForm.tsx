import FieldGroup from "@/components/experience/FieldGroup";
import { FormSection } from "@/components/experience/StudyUI";
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
  const [confiancaSet, setConfiancaSet] = useState(false);
  const [confianca, setConfianca] = useState(3);
  const [resultado, setResultado] = useState<{ pct: number; critico: boolean } | null>(null);

  const { data: materias } = useMaterias();
  const { data: blocos, isLoading: loadingBlocos } = useBlocos();

  const resetForm = () => {
    setConfiancaSet(false);
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
      nivel_confianca_medio: confiancaSet ? confianca : null,
    };
    mutation.mutate(data);
  };

  const getMateriaNome = (id: string) => materias?.find((m) => m.id === id)?.nome ?? id;

  return (
    <AppLayout>
      <div className="record-workspace grid grid-cols-1 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] gap-6 lg:gap-8">
        <div>
          <div className="page-header">
            <h1 className="page-title">Bloco de Questões</h1>
            
          </div>

          {resultado && (
            <div role="status" className={`saved-result mb-6 p-4 rounded-lg border transition-all duration-300 ${resultado.critico ? "border-critical/40 bg-critical/10" : "border-success/40 bg-success/10"}`}>
              <p className={`text-lg font-bold font-mono ${resultado.critico ? "text-critical" : "text-success"}`}>
                {resultado.pct}% de acerto
              </p>
              <p className="text-xs text-muted-foreground">
                {resultado.critico ? "Confira os erros deste bloco; a amostra isolada não define domínio" : "Resultado registrado; continue acompanhando a amostra"}
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="record-form guided-form" aria-busy={mutation.isPending}>
<FormSection number="01" title="Conteúdo praticado" description="Identifique a matéria e o assunto." complete={Boolean(materiaId && assuntoId)}>

            <FieldGroup label="Matéria">
              <MateriaSelect value={materiaId} onChange={(v) => { setMateriaId(v); setAssuntoId(""); }} />
            </FieldGroup>
            <FieldGroup label="Assunto">
              <AssuntoSelect materiaId={materiaId} value={assuntoId} onChange={setAssuntoId} />
            </FieldGroup>

</FormSection>
<FormSection number="02" title="Resultado do bloco" description="Dificuldade, acertos e tempo da prática." complete={Boolean(totalQ && totalA && tempo)}>
            <FieldGroup label={`Dificuldade: ${dificuldade}`}>
              <input type="range" min={1} max={5} value={dificuldade} onChange={(e) => setDificuldade(+e.target.value)} className="w-full accent-accent" />
            </FieldGroup>
            <div className="grid grid-cols-2 gap-3 sm:gap-4">
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

</FormSection>
<FormSection number="03" title="Sua percepção" description="A confiança é opcional." complete={confiancaSet}>
            <FieldGroup label={`Confiança Média: ${confiancaSet ? confianca : "não informado (opcional)"}`}>
              <input type="range" min={1} max={5} value={confianca} onChange={(e) => {setConfiancaSet(true); setConfianca(+e.target.value);}} className="w-full accent-accent" />
            </FieldGroup>

</FormSection>
<div className="form-submit-zone"><p>Confira os dados antes de registrar.</p>            <button type="submit" disabled={mutation.isPending}
              className="btn-tactical">
              {mutation.isPending ? "Registrando..." : "Registrar Bloco"}
            </button>
          </div></form>
        </div>

        <div>
          <h2 className="text-base sm:text-lg font-bold tracking-wider text-foreground uppercase mb-4">Histórico de Blocos</h2>
          {loadingBlocos ? <LoadingState /> : (!blocos || blocos.length === 0) ? <EmptyState /> : (
            <div className="space-y-2 max-h-[500px] lg:max-h-[600px] overflow-y-auto pr-1">
              {blocos.map((b) => (
                <div key={b.id} className="rounded-lg border border-border bg-card/80 hover:bg-card p-3 sm:p-4 flex items-center justify-between gap-3 transition-all hover:border-accent/40 hover:translate-x-0.5">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-foreground truncate">{getMateriaNome(b.materia_id)}</p>
                    <p className="text-[10px] sm:text-xs text-muted-foreground truncate">
                      {b.total_acertos}/{b.total_questoes} • Dif: {b.dificuldade} • {Math.round(b.tempo_total_segundos / 60)}min
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className={`text-sm font-bold font-mono ${b.percentual_acerto >= 70 ? "text-success" : "text-critical"}`}>
                      {b.percentual_acerto}%
                    </p>
                    <p className="text-[10px] text-muted-foreground font-mono">{new Date(b.criado_em).toLocaleDateString("pt-BR")}</p>
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

