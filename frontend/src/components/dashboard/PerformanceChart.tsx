import { useReducedMotion } from "@/hooks/useReducedMotion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Area,
  AreaChart,
} from "recharts";

interface ChartData {
  label: string;
  value: number;
}

interface PerformanceChartProps {
  title: string;
  data: ChartData[];
  type?: "line" | "bar";
  color?: string;
  unit?: string;
}

export default function PerformanceChart({
  title,
  data,
  type = "line",
  color = "hsl(90, 40%, 35%)",
  unit = "",
}: PerformanceChartProps) {
  const reducedMotion = useReducedMotion();
  const gradId = `grad-${title.replace(/\s/g, "").slice(0, 8)}`;
  const hasData = data.length > 0;

  return (
    <div className="tac-card performance-chart h-full flex flex-col">
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <p className="chart-title">
          {title}
        </p>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full animate-pulse-glow" style={{ background: color }} />
          <span className="text-[9px] font-mono tracking-widest text-muted-foreground/70 uppercase">{unit}</span>
        </div>
      </div>

      <div className="h-[220px] sm:h-[250px] min-w-0">
        {!hasData ? (
          <div className="h-full flex items-center justify-center text-xs text-muted-foreground/60 italic">
            Sem dados no período.
          </div>
        ) : (
        <ResponsiveContainer width="100%" height="100%">
          {type === "line" ? (
            <AreaChart data={data}>
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.18} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 6" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={30} />
              <Tooltip
                cursor={{ stroke: color, strokeWidth: 1, strokeDasharray: "4 4" }}
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: 12,
                  color: "hsl(var(--foreground))",
                  boxShadow: "0 4px 14px rgba(0,0,0,0.4)",
                }}
              />
              <Area isAnimationActive={!reducedMotion} animationDuration={350} type="monotone" dataKey="value" stroke="none" fill={`url(#${gradId})`} />
              <Line
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2}
                dot={{ fill: color, r: 2, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: color, stroke: "hsl(var(--card))", strokeWidth: 2 }}
                name={unit}
                isAnimationActive={!reducedMotion}
                animationDuration={350}
              />
            </AreaChart>
          ) : (
            <BarChart data={data}>
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.95} />
                  <stop offset="100%" stopColor={color} stopOpacity={0.5} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 6" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={30} />
              <Tooltip
                cursor={{ fill: "hsl(var(--accent) / 0.06)" }}
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: 12,
                  color: "hsl(var(--foreground))",
                  boxShadow: "0 4px 14px rgba(0,0,0,0.4)",
                }}
              />
              <Bar isAnimationActive={!reducedMotion} dataKey="value" fill={`url(#${gradId})`} maxBarSize={36} radius={[3, 3, 0, 0]} name={unit} animationDuration={350} />
            </BarChart>
          )}
        </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
