import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { MateriaPerformance } from "@/lib/types";
import { formatarHoras } from "@/lib/utils";
import { useEffect, useMemo, useRef, useState } from "react";

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

interface RadialBarProps {
  materia: string;
  ipr: number;
  color: string;
  totalQuestoes?: number;
  totalAcertos?: number;
  horasEstudo?: number;
}

function RadialBar({ materia, ipr, totalQuestoes, totalAcertos, horasEstudo }: RadialBarProps) {
  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(ipr, 0), 100);
  const targetOffset = circumference - (progress / 100) * circumference;

  const [animatedOffset, setAnimatedOffset] = useState(circumference);
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (isVisible) {
      const timeout = setTimeout(() => setAnimatedOffset(targetOffset), 100);
      return () => clearTimeout(timeout);
    }
  }, [isVisible, targetOffset]);

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div ref={ref} className="flex flex-col items-center gap-2 p-3 cursor-pointer" style={{ opacity: isVisible ? 1 : 0, transform: isVisible ? 'translateY(0)' : 'translateY(16px)', transition: 'opacity 0.6s ease-out, transform 0.6s ease-out' }}>
            <div className="relative" style={{ width: size, height: size }}>
              <svg width={size} height={size} className="-rotate-90" overflow="visible">
                <circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  fill="none"
                  stroke="hsl(var(--muted))"
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                />
                <circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  fill="none"
                  stroke={getIprColor(ipr)}
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={animatedOffset}
                  style={{
                    transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)',
                    filter: ipr >= 80 && isVisible ? `drop-shadow(0 0 6px ${getIprColor(ipr)})` : "none",
                  }}
                />
              </svg>
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
        </TooltipTrigger>
        <TooltipContent
          side="bottom"
          className="bg-card border border-border p-3 shadow-lg"
        >
          <div className="flex flex-col gap-1.5 min-w-[160px]">
            <p className="text-xs font-semibold text-foreground tracking-wide uppercase border-b border-border pb-1.5 mb-0.5">
              {materia}
            </p>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Acertos</span>
              <span className="font-mono font-semibold text-foreground">
                {totalAcertos ?? "—"}<span className="text-muted-foreground/60"> / {totalQuestoes ?? "—"}</span>
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Tempo de estudo</span>
              <span className="font-mono font-semibold text-foreground">
                {horasEstudo != null ? `${formatarHoras(horasEstudo)}` : "—"}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">IPR</span>
              <span className="font-mono font-bold" style={{ color: getIprColor(ipr) }}>
                {ipr.toFixed(1)}%
              </span>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface PieChartMateriasProps {
  data: MateriaPerformance[];
}

export default function PieChartMaterias({ data }: PieChartMateriasProps) {
  const pieData = useMemo(
    () =>
      data.map((item, index) => ({
        materia: item.materia.nome,
        ipr: Math.max(item.ipr, 0),
        color: COLORS[index % COLORS.length],
        totalQuestoes: item.total_questoes,
        totalAcertos: item.total_acertos,
        horasEstudo: item.horas_estudo,
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
          {pieData.map((entry) => (
            <RadialBar
              key={entry.materia}
              materia={entry.materia}
              ipr={entry.ipr}
              color={entry.color}
              totalQuestoes={entry.totalQuestoes}
              totalAcertos={entry.totalAcertos}
              horasEstudo={entry.horasEstudo}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
