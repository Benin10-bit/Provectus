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
    <div className="rounded-md border border-border bg-card p-5 animate-slide-in">
      <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase mb-4">
        {title}
      </p>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          {type === "line" ? (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(150, 10%, 18%)" />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: "hsl(120, 5%, 50%)" }} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(120, 5%, 50%)" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(150, 12%, 9%)",
                  border: "1px solid hsl(150, 10%, 18%)",
                  borderRadius: "4px",
                  fontSize: 12,
                  color: "hsl(120, 5%, 85%)",
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2}
                dot={{ fill: color, r: 3 }}
                name={unit}
              />
            </LineChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(150, 10%, 18%)" />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: "hsl(120, 5%, 50%)" }} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(120, 5%, 50%)" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(150, 12%, 9%)",
                  border: "1px solid hsl(150, 10%, 18%)",
                  borderRadius: "4px",
                  fontSize: 12,
                  color: "hsl(120, 5%, 85%)",
                }}
              />
              <Bar dataKey="value" fill={color} radius={[2, 2, 0, 0]} name={unit} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
