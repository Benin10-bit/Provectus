import { useMaterias, useAssuntosPorMateria } from "@/hooks/useConfiguracoes";

interface MateriaSelectProps {
  value: string;
  onChange: (id: string) => void;
  className?: string;
}

export function MateriaSelect({ value, onChange, className = "form-select" }: MateriaSelectProps) {
  const { data: materias, isLoading } = useMaterias();

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
      disabled={isLoading}
    >
      <option value="">{isLoading ? "Carregando..." : "Selecione..."}</option>
      {(materias || []).map((m) => (
        <option key={m.id} value={m.id}>{m.nome}</option>
      ))}
    </select>
  );
}

interface AssuntoSelectProps {
  materiaId: string;
  value: string;
  onChange: (id: string) => void;
  className?: string;
}

export function AssuntoSelect({ materiaId, value, onChange, className = "form-select" }: AssuntoSelectProps) {
  const { data: assuntos, isLoading } = useAssuntosPorMateria(materiaId || undefined);

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
      disabled={!materiaId || isLoading}
    >
      <option value="">{!materiaId ? "Selecione matéria primeiro" : isLoading ? "Carregando..." : "Selecione..."}</option>
      {(assuntos || []).map((a) => (
        <option key={a.id} value={a.id}>{a.nome}</option>
      ))}
    </select>
  );
}
