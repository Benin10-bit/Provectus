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
    competencia1: 0,
    competencia2: 0,
    competencia3: 0,
    competencia4: 0,
    competencia5: 0,
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
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-wider text-foreground uppercase">
          Nova Redação
        </h1>
        <p className="text-sm text-muted-foreground">Registre uma redação para avaliação</p>
      </div>

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
        {/* Tema */}
        <div>
          <label className="block text-xs font-medium tracking-wider text-muted-foreground uppercase mb-2">
            Tema da Redação *
          </label>
          <input
            type="text"
            value={tema}
            onChange={(e) => setTema(e.target.value)}
            required
            maxLength={300}
            className="form-input w-full"
            placeholder="Ex: A persistência da violência contra a mulher no Brasil"
          />
        </div>

        {/* Eixo temático */}
        <div>
          <label className="block text-xs font-medium tracking-wider text-muted-foreground uppercase mb-2">
            Eixo Temático
          </label>
          <input
            type="text"
            value={eixoTematico}
            onChange={(e) => setEixoTematico(e.target.value)}
            className="form-input w-full"
            placeholder="Ex: Direitos Humanos"
          />
        </div>

        {/* Tempo e observações */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium tracking-wider text-muted-foreground uppercase mb-2">
              Tempo de Escrita (min)
            </label>
            <input
              type="number"
              value={tempoEscrita}
              onChange={(e) => setTempoEscrita(e.target.value)}
              min={1}
              className="form-input w-full"
              placeholder="Ex: 90"
            />
          </div>
          <div>
            <label className="block text-xs font-medium tracking-wider text-muted-foreground uppercase mb-2">
              Repertórios Utilizados
            </label>
            <input
              type="text"
              value={repertorios}
              onChange={(e) => setRepertorios(e.target.value)}
              className="form-input w-full"
              placeholder="Ex: Constituição, Hannah Arendt"
            />
          </div>
        </div>

        {/* Observações */}
        <div>
          <label className="block text-xs font-medium tracking-wider text-muted-foreground uppercase mb-2">
            Observações
          </label>
          <textarea
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            className="form-input w-full min-h-[80px] resize-y"
            placeholder="Observações gerais sobre a redação"
          />
        </div>

        {/* Competências */}
        <div className="rounded-md border border-border bg-card p-5">
          <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase mb-4">
            Notas por Competência (0–200)
          </p>
          <div className="space-y-4">
            {compEntries.map(([code, name], i) => (
              <div key={code}>
                <label className="block text-sm text-foreground mb-1">
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
          className="w-full py-3 rounded-md bg-primary text-primary-foreground font-bold tracking-wider uppercase text-sm hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {isPending ? "Enviando..." : "Enviar Redação"}
        </button>
      </form>
    </AppLayout>
  );
}
