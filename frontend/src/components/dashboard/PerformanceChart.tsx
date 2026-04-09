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
  return (
    <div className="rounded-lg border border-border bg-card p-4 sm:p-5 h-full flex flex-col">
      <p className="text-[10px] sm:text-xs font-medium tracking-wider text-muted-foreground uppercase mb-3 sm:mb-4">
        {title}
      </p>
      <div className="flex-1 min-h-[180px] sm:min-h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          {type === "line" ? (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(150, 10%, 18%)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: "hsl(120, 5%, 50%)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(120, 5%, 50%)" }} axisLine={false} tickLine={false} width={30} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(150, 12%, 9%)",
                  border: "1px solid hsl(150, 10%, 18%)",
                  borderRadius: "8px",
                  fontSize: 12,
                  color: "hsl(120, 5%, 85%)",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2}
                dot={{ fill: color, r: 3, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: color, stroke: "hsl(150, 12%, 9%)", strokeWidth: 2 }}
                name={unit}
              />
            </LineChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(150, 10%, 18%)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: "hsl(120, 5%, 50%)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(120, 5%, 50%)" }} axisLine={false} tickLine={false} width={30} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(150, 12%, 9%)",
                  border: "1px solid hsl(150, 10%, 18%)",
                  borderRadius: "8px",
                  fontSize: 12,
                  color: "hsl(120, 5%, 85%)",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                }}
              />
              <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} name={unit} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
