import { Link } from "react-router-dom";
import { PenTool, BarChart3 } from "lucide-react";
import { useRedacoes } from "@/hooks/useRedacoes";
import { getCompetenciaNome } from "@/lib/types";
import { format } from "date-fns";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

export function UltimaRedacaoCard() {
  const { data: redacoes } = useRedacoes();
  const r = redacoes?.[0];

  if (!r) return null;

  const statusColor =
    r.status.includes("Excelente") || r.status.includes("Bom") ? "text-success"
    : r.status.includes("Regular") ? "text-warning"
    : "text-critical";

  return (
    <div className="rounded-md border border-border bg-card p-5 animate-slide-in">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Última Redação
        </p>
        <PenTool className="h-4 w-4 text-accent" />
      </div>
      <p className="text-3xl font-bold font-mono text-foreground">{r.nota_total}</p>
      <p className={`text-xs font-medium mt-1 ${statusColor}`}>{r.status}</p>
      <p className="text-[10px] text-muted-foreground mt-2">
        {format(new Date(r.data_escrita), "dd/MM/yyyy")}
      </p>
      <p className="text-[10px] text-warning mt-1">
        C{r.competencia_mais_fraca} — {getCompetenciaNome(r.competencia_mais_fraca)}
      </p>
      <Link
        to={`/redacoes/${r.id}`}
        className="inline-block mt-3 text-xs text-accent hover:text-accent/80 tracking-wider uppercase transition-colors"
      >
        Ver detalhes →
      </Link>
    </div>
  );
}

function getNivel(media: number): string {
  if (media >= 900) return "Elite";
  if (media >= 800) return "Avançado";
  if (media >= 600) return "Intermediário";
  if (media >= 400) return "Básico";
  return "Iniciante";
}

export function MediaRedacoesCard() {
  const { data: redacoes } = useRedacoes();

  if (!redacoes || redacoes.length === 0) return null;

  const media = Math.round(
    redacoes.reduce((sum, r) => sum + r.nota_total, 0) / redacoes.length
  );

  // Variação: média anterior (sem a última) vs última nota
  const ultima = redacoes[0]?.nota_total ?? 0;
  const mediaAnterior =
    redacoes.length > 1
      ? Math.round(redacoes.slice(1).reduce((s, r) => s + r.nota_total, 0) / (redacoes.length - 1))
      : media;
  const variacao = ultima - mediaAnterior;

  const META = 900;
  const progresso = Math.min(Math.round((media / META) * 100), 100);
  const nivel = getNivel(media);

  return (
    <div className="rounded-md border border-border bg-card p-5 animate-slide-in">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Média de Redações
        </p>
        <BarChart3 className="h-4 w-4 text-accent" />
      </div>

      <p className="text-3xl font-bold font-mono text-foreground">{media}</p>

      {/* Variação */}
      <p className={`text-xs font-medium mt-1 ${
        variacao > 0 ? "text-success" : variacao < 0 ? "text-critical" : "text-muted-foreground"
      }`}>
        {variacao > 0 ? `↑ +${variacao}` : variacao < 0 ? `↓ ${variacao}` : "0"}{" "}
        <span className="font-normal">desde a última redação</span>
      </p>

      {/* Meta + Progresso */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
          <span>Meta: {META}</span>
          <span>{progresso}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
          <div
            className="h-full rounded-full bg-accent transition-all duration-700 ease-out"
            style={{ width: `${progresso}%` }}
          />
        </div>
      </div>

      {/* Nível */}
      <p className="text-[10px] text-muted-foreground mt-2">
        Nível: <span className="text-accent font-medium">{nivel}</span>
      </p>

      <p className="text-xs text-muted-foreground mt-2">
        Total: {redacoes.length} {redacoes.length === 1 ? "redação" : "redações"}
      </p>
    </div>
  );
}

export function ProgressoRedacoesChart() {
  const { data: redacoes } = useRedacoes();

  if (!redacoes || redacoes.length < 1) return null;

  const chartData = [...redacoes]
    .reverse()
    .slice(-10)
    .map((r, i) => ({
      label: `R${i + 1}`,
      value: r.nota_total,
    }));

  return (
    <div className="rounded-md border border-border bg-card p-5 animate-slide-in">
      <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase mb-4">
        Evolução de Redações
      </p>
      <div className="h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              axisLine={{ stroke: "hsl(var(--border))" }}
            />
            <YAxis
              domain={[0, 1000]}
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              axisLine={{ stroke: "hsl(var(--border))" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "4px",
                fontSize: "12px",
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="hsl(var(--accent))"
              strokeWidth={2}
              dot={{ r: 3, fill: "hsl(var(--accent))" }}
              name="Nota"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
