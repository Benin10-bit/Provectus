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
  blocos?: number;
}

function RadialBar({ materia, ipr, totalQuestoes, totalAcertos, horasEstudo, blocos=0 }: RadialBarProps) {
  const enough=(totalQuestoes||0)>=20&&blocos>=2;
  const tone=enough?getIprColor(ipr):'hsl(var(--muted-foreground))';
  const size = 120;
  const strokeWidth = 6;
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
          <div ref={ref} tabIndex={0} className="flex flex-col items-center gap-2 rounded-lg border border-border/60 bg-secondary/20 p-3 cursor-pointer transition-colors hover:border-olive/50 hover:bg-secondary/40" style={{ opacity: isVisible ? 1 : 0, transform: isVisible ? 'translateY(0)' : 'translateY(16px)', transition: 'opacity 0.25s ease-out, transform 0.25s ease-out' }}>
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
                  stroke={tone}
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={animatedOffset}
                  style={{
                    transition: 'stroke-dashoffset 350ms ease-out',
                    filter: "none",
                  }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-lg font-mono font-bold text-foreground">
                  {totalQuestoes?`${ipr.toFixed(0)}%`:'—'}
                </span>
              </div>
            </div>
            <div className="flex flex-col items-center gap-0.5 max-w-[120px]">
              <span className="text-xs font-semibold text-foreground break-words max-w-full text-center">
                {materia}
              </span>
              <span
                className="text-[10px] font-mono uppercase tracking-wider"
                style={{ color: tone }}
              >
                {!totalQuestoes?'Sem prática':!enough?'Amostra pequena':ipr >= 80 ? 'Bom' : ipr >= 70 ? 'Regular' : 'Conferir erros'}
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
              <span className="text-muted-foreground">Precisão</span>
              <span className="font-mono font-bold" style={{ color: getIprColor(ipr) }}>
                {totalQuestoes?`${ipr.toFixed(1)}%`:'Sem questões'}
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
        blocos: item.amostra_blocos,
      })),
    [data]
  );

  const avgIpr = useMemo(() => {
    const total=pieData.reduce((n,d)=>n+(d.totalQuestoes||0),0);
    return total?pieData.reduce((n,d)=>n+(d.totalAcertos||0),0)/total*100:null;
  }, [pieData]);

  if (!pieData.length) {
    return (
      <div className="tac-card">
        <p className="module-title">Precisão por Matéria</p>
        <p className="py-8 text-center text-sm text-muted-foreground">
          Nenhuma matéria disponível
        </p>
      </div>
    );
  }

  return (
    <div className="tac-card">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
        <div>
          <p className="module-title mb-1.5">Precisão por Matéria</p>
          <p className="text-xs text-muted-foreground">
            Acertos / questões · Precisão conjunta:{" "}
            <span className="num font-semibold text-foreground">
              {avgIpr === null ? "—" : `${avgIpr.toFixed(0)}%`}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
          {[
            { c: "hsl(var(--success))", l: "≥80%" },
            { c: "hsl(var(--warning))", l: "70-79%" },
            { c: "hsl(var(--critical))", l: "<70%" },
          ].map((i) => (
            <span key={i.l} className="flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: i.c }}
              />
              {i.l}
            </span>
          ))}
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground/80 mb-4 max-w-2xl">
        Cores de desempenho só aparecem com pelo menos 20 questões em 2 blocos.
        Limite operacional, não diagnóstico de domínio.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 sm:gap-3">
        {pieData.map((entry) => (
          <RadialBar
            key={entry.materia}
            materia={entry.materia}
            ipr={entry.ipr}
            color={entry.color}
            totalQuestoes={entry.totalQuestoes}
            totalAcertos={entry.totalAcertos}
            horasEstudo={entry.horasEstudo}
            blocos={entry.blocos}
          />
        ))}
      </div>
    </div>
  );
}
