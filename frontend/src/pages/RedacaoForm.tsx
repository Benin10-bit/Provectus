import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import { useCreateRedacao } from "@/hooks/useRedacoes";
import { COMPETENCIAS_MAP } from "@/lib/types";

export default function RedacaoForm() {
  const navigate = useNavigate();
  const { mutate, isPending } = useCreateRedacao((id) => navigate(`/redacoes/${id}`));

  const [tema, setTema] = useState("");
  const [eixoTematico, setEixoTematico] = useState("");
  const [tempoEscrita, setTempoEscrita] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [repertorios, setRepertorios] = useState("");
  const [notas, setNotas] = useState<Record<string, number>>({
    competencia1: 0, competencia2: 0, competencia3: 0, competencia4: 0, competencia5: 0,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutate({
      tema,
      eixo_tematico: eixoTematico || null,
      tempo_escrita_min: tempoEscrita ? Number(tempoEscrita) : null,
      observacoes: observacoes || null,
      repertorios: repertorios || null,
      competencia1: notas.competencia1,
      competencia2: notas.competencia2,
      competencia3: notas.competencia3,
      competencia4: notas.competencia4,
      competencia5: notas.competencia5,
    });
  };

  const compEntries = Object.entries(COMPETENCIAS_MAP);

  return (
    <AppLayout>
      <div className="page-header">
        <h1 className="page-title">Nova Redação</h1>
        <p className="page-subtitle">Registre uma redação para avaliação</p>
      </div>

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-5 sm:space-y-6">
        <FieldGroup label="Tema da Redação *">
          <input
            type="text"
            value={tema}
            onChange={(e) => setTema(e.target.value)}
            required
            maxLength={300}
            className="form-input w-full"
            placeholder="Ex: A persistência da violência contra a mulher no Brasil"
          />
        </FieldGroup>

        <FieldGroup label="Eixo Temático">
          <input
            type="text"
            value={eixoTematico}
            onChange={(e) => setEixoTematico(e.target.value)}
            className="form-input w-full"
            placeholder="Ex: Direitos Humanos"
          />
        </FieldGroup>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FieldGroup label="Tempo de Escrita (min)">
            <input
              type="number"
              value={tempoEscrita}
              onChange={(e) => setTempoEscrita(e.target.value)}
              min={1}
              className="form-input w-full"
              placeholder="Ex: 90"
            />
          </FieldGroup>
          <FieldGroup label="Repertórios Utilizados">
            <input
              type="text"
              value={repertorios}
              onChange={(e) => setRepertorios(e.target.value)}
              className="form-input w-full"
              placeholder="Ex: Constituição, Hannah Arendt"
            />
          </FieldGroup>
        </div>

        <FieldGroup label="Observações">
          <textarea
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            className="form-input w-full min-h-[80px] resize-y"
            placeholder="Observações gerais sobre a redação"
          />
        </FieldGroup>

        <div className="rounded-lg border border-border bg-card p-4 sm:p-5">
          <p className="text-[10px] sm:text-xs font-medium tracking-wider text-muted-foreground uppercase mb-4">
            Notas por Competência (0–200)
          </p>
          <div className="space-y-4">
            {compEntries.map(([code, name], i) => (
              <div key={code}>
                <label className="block text-sm text-foreground mb-1.5">
                  <span className="font-bold text-accent">{code}</span> — {name}
                </label>
                <input
                  type="number"
                  min={0}
                  max={200}
                  step={20}
                  value={notas[`competencia${i + 1}`]}
                  onChange={(e) =>
                    setNotas((prev) => ({
                      ...prev,
                      [`competencia${i + 1}`]: Math.min(200, Math.max(0, Number(e.target.value))),
                    }))
                  }
                  className="form-input w-full"
                  required
                />
              </div>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={isPending || !tema}
          className="btn-tactical"
        >
          {isPending ? "Enviando..." : "Enviar Redação"}
        </button>
      </form>
    </AppLayout>
  );
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[10px] sm:text-xs font-medium tracking-wider text-muted-foreground uppercase mb-1.5 sm:mb-2">{label}</label>
      {children}
    </div>
  );
}
