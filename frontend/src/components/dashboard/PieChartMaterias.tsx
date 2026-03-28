import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MateriaPerformance } from "@/lib/types";
import { useMemo } from "react";

const COLORS = [
  "hsl(var(--success))",
  "hsl(var(--accent))",
  "hsl(90, 40%, 35%)",
  "hsl(var(--critical))",
  "hsl(200, 60%, 50%)",
  "hsl(280, 45%, 55%)",
  "hsl(170, 50%, 40%)",
  "hsl(330, 50%, 50%)",
];

function getIprColor(ipr: number): string {
  if (ipr >= 80) return "hsl(var(--success))";
  if (ipr >= 70) return "hsl(var(--warning))";
  return "hsl(var(--critical))";
}

interface PieChartMateriasProps {
  data: MateriaPerformance[];
}

interface RadialBarProps {
  materia: string;
  ipr: number;
  color: string;
  index: number;
  total: number;
}

function RadialBar({ materia, ipr, color, index, total }: RadialBarProps) {
  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(ipr, 0), 100);
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2 p-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Progress arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={getIprColor(ipr)}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
            style={{
              filter: ipr >= 80 ? `drop-shadow(0 0 6px ${getIprColor(ipr)})` : "none",
            }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-mono font-bold text-foreground">
            {ipr.toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="flex flex-col items-center gap-0.5 max-w-[120px]">
        <span className="text-xs font-semibold text-foreground truncate max-w-full text-center">
          {materia}
        </span>
        <span
          className="text-[10px] font-mono uppercase tracking-wider"
          style={{ color: getIprColor(ipr) }}
        >
          {ipr >= 80 ? "Excelente" : ipr >= 70 ? "Operacional" : "Crítico"}
        </span>
      </div>
    </div>
  );
}

export default function PieChartMaterias({ data }: PieChartMateriasProps) {
  const pieData = useMemo(
    () =>
      data.map((item, index) => ({
        materia: item.materia.nome,
        ipr: Math.max(item.ipr, 0),
        color: COLORS[index % COLORS.length],
      })),
    [data]
  );

  const avgIpr = useMemo(() => {
    if (!pieData.length) return 0;
    return pieData.reduce((sum, d) => sum + d.ipr, 0) / pieData.length;
  }, [pieData]);

  if (!pieData.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium tracking-wider uppercase text-muted-foreground">
            IPR por Matéria
          </CardTitle>
        </CardHeader>
        <CardContent className="p-8 text-center text-muted-foreground">
          Nenhuma matéria disponível
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="col-span-full">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-xl font-bold tracking-tight text-foreground">
            IPR por Matéria
          </CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Índice de Performance por matéria · Média:{" "}
            <span
              className="font-mono font-semibold"
              style={{ color: getIprColor(avgIpr) }}
            >
              {avgIpr.toFixed(0)}%
            </span>
          </p>
        </div>
        <div className="flex items-center gap-4 text-[10px] uppercase tracking-wider text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "hsl(var(--success))" }} />
            <span>≥80%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "hsl(var(--warning))" }} />
            <span>70-79%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "hsl(var(--critical))" }} />
            <span>&lt;70%</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4 pb-6">
        <div className="flex flex-wrap justify-center gap-2 sm:gap-4">
          {pieData.map((entry, index) => (
            <RadialBar
              key={entry.materia}
              materia={entry.materia}
              ipr={entry.ipr}
              color={entry.color}
              index={index}
              total={pieData.length}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
