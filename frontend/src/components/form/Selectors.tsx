import { useMaterias, useAssuntosPorMateria } from "@/hooks/useConfiguracoes";
import { ChevronDown } from "lucide-react";

interface MateriaSelectProps {
  value: string;
  onChange: (id: string) => void;
  className?: string;
}

function Caret() {
  return (
    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
  );
}

export function MateriaSelect({ value, onChange, className = "form-select" }: MateriaSelectProps) {
  const { data: materias, isLoading } = useMaterias();

  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`${className} pr-9`}
        disabled={isLoading}
      >
        <option value="">{isLoading ? "Carregando..." : "Todas as matérias"}</option>
        {(materias || []).map((m) => (
          <option key={m.id} value={m.id}>{m.nome}</option>
        ))}
      </select>
      <Caret />
    </div>
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
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`${className} pr-9`}
        disabled={!materiaId || isLoading}
      >
        <option value="">{!materiaId ? "Selecione matéria primeiro" : isLoading ? "Carregando..." : "Selecione..."}</option>
        {(assuntos || []).map((a) => (
          <option key={a.id} value={a.id}>{a.nome}</option>
        ))}
      </select>
      <Caret />
    </div>
  );
}
