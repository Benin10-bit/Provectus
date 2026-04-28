import AppLayout from "@/components/layout/AppLayout";
import { ErrorState } from "@/components/ui/states";
import { useRelatorioMensal } from "@/hooks/useRelatorioMensal";
import { mesAnterior, NOMES_MES } from "@/lib/relatorio";
import { formatarHoras } from "@/lib/utils";
import {
  Activity, AlertTriangle, Award, BarChart3, Brain, CalendarRange,
  CheckCircle2, Clock, Database, FileText, Flame, GitCompareArrows,
  ListChecks, Loader2, Minus, PenTool, Percent, Radio, Scale,
  Target, TrendingDown, TrendingUp, Trophy, Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";

/* =========================================================================
 * LOADING ESPECIAL — "Juntando informações"
 * ========================================================================= */

const LOADING_STEPS = [
  "Conectando ao núcleo de dados",
  "Coletando sessões de estudo",
  "Processando blocos de questões",
  "Cruzando simulados e provas",
  "Calculando IPR consolidado",
  "Analisando redações",
  "Gerando recomendações estratégicas",
  "Compilando relatório final",
];

function GatheringLoader() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setStep(s => (s + 1) % LOADING_STEPS.length), 900);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="min-h-[60vh] flex items-center justify-center animate-fade-in">
      <div className="w-full max-w-md mx-auto text-center px-4">
        <div className="relative inline-flex mb-6">
          <div className="absolute inset-0 rounded-full bg-accent/20 blur-2xl animate-pulse" />
          <div className="relative p-5 rounded-full border border-accent/40 bg-card">
            <Database className="h-8 w-8 text-accent animate-pulse-glow" />
          </div>
        </div>

        <h2 className="text-lg font-bold tracking-[0.2em] uppercase text-foreground mb-1">
          Juntando informações
        </h2>
        <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground font-mono mb-6">
          Compilando relatório mensal
        </p>

        <div className="space-y-2 text-left bg-card/60 border border-border rounded-lg p-4 mb-4">
          {LOADING_STEPS.map((s, i) => {
            const done = i < step;
            const active = i === step;
            return (
              <div
                key={s}
                className={`flex items-center gap-2 text-xs transition-all duration-300
                  ${active ? "text-accent" : done ? "text-muted-foreground/70" : "text-muted-foreground/40"}`}
              >
                {done ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                ) : active ? (
                  <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-current shrink-0 mx-1" />
                )}
                <span className="truncate font-mono">{s}</span>
              </div>
            );
          })}
        </div>

        <div className="h-1 w-full bg-muted/40 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent/40 via-accent to-accent/40 transition-all duration-500"
            style={{ width: `${((step + 1) / LOADING_STEPS.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}

/* =========================================================================
 * WAITING LOOP — exibido até virar o mês (1º dia do próximo mês)
 * ========================================================================= */

const WAITING_MESSAGES = [
  "Juntando mais informações",
  "Coletando sessões em tempo real",
  "Monitorando blocos de questões",
  "Acumulando dados de simulados",
  "Registrando redações enviadas",
  "Calculando padrões de consistência",
  "Aguardando fechamento do mês",
  "Preparando o relatório consolidado",
];

function diasAteProximoMes(now = new Date()) {
  const proximo = new Date(now.getFullYear(), now.getMonth() + 1, 1, 0, 0, 0, 0);
  const ms = proximo.getTime() - now.getTime();
  const dias = Math.ceil(ms / (1000 * 60 * 60 * 24));
  return { dias, dataAlvo: proximo };
}

function WaitingNextMonthLoader() {
  const [idx, setIdx] = useState(0);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx(i => (i + 1) % WAITING_MESSAGES.length), 1800);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    const t = setInterval(() => setTick(x => x + 1), 60_000);
    return () => clearInterval(t);
  }, []);

  const { dias, dataAlvo } = diasAteProximoMes();
  void tick; // força re-render periódico
  const proxMesNome = NOMES_MES[dataAlvo.getMonth()];

  return (
    <div className="min-h-[70vh] flex items-center justify-center animate-fade-in">
      <div className="w-full max-w-lg mx-auto text-center px-4">
        {/* Orbital animation */}
        <div className="relative inline-flex mb-8 h-28 w-28 items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-accent/20 blur-3xl animate-pulse" />
          <div className="absolute inset-0 rounded-full border border-accent/20 animate-[spin_8s_linear_infinite]" />
          <div className="absolute inset-2 rounded-full border border-accent/30 border-dashed animate-[spin_12s_linear_infinite_reverse]" />
          <div className="absolute inset-5 rounded-full border border-accent/40 animate-[spin_5s_linear_infinite]" />
          <div className="relative p-4 rounded-full border border-accent/60 bg-card shadow-[0_0_30px_hsl(var(--accent)/0.3)]">
            <Database className="h-7 w-7 text-accent animate-pulse-glow" />
          </div>
          {/* Satellite dot */}
          <span className="absolute top-0 left-1/2 -translate-x-1/2 h-2 w-2 rounded-full bg-accent shadow-[0_0_10px_hsl(var(--accent))] animate-[spin_3s_linear_infinite] origin-[50%_56px]" />
        </div>

        <p className="text-[10px] tracking-[0.35em] uppercase text-accent font-mono mb-2 flex items-center justify-center gap-2">
          <Radio className="h-3 w-3 animate-pulse" /> Coletando dados em tempo real
        </p>

        <h2 className="text-xl sm:text-2xl font-bold tracking-[0.15em] uppercase text-foreground mb-2 min-h-[2em] flex items-center justify-center">
          <span key={idx} className="animate-fade-in inline-flex items-center gap-1">
            {WAITING_MESSAGES[idx]}
            <span className="inline-flex w-6 justify-start">
              <span className="animate-[blink_1.4s_infinite]">.</span>
              <span className="animate-[blink_1.4s_infinite_0.2s]">.</span>
              <span className="animate-[blink_1.4s_infinite_0.4s]">.</span>
            </span>
          </span>
        </h2>

        <p className="text-xs text-muted-foreground font-mono mb-6">
          O primeiro relatório mensal será liberado em{" "}
          <span className="text-accent font-bold">
            01/{String(dataAlvo.getMonth() + 1).padStart(2, "0")}/{dataAlvo.getFullYear()}
          </span>
        </p>

        {/* Countdown */}
        <div className="grid grid-cols-3 gap-3 mb-6 max-w-xs mx-auto">
          <div className="p-3 rounded-lg border border-accent/30 bg-card/80 backdrop-blur-sm">
            <p className="text-2xl font-bold font-mono text-accent">{dias}</p>
            <p className="text-[9px] tracking-[0.2em] uppercase text-muted-foreground font-mono mt-1">
              {dias === 1 ? "Dia" : "Dias"}
            </p>
          </div>
          <div className="p-3 rounded-lg border border-border bg-card/80 backdrop-blur-sm">
            <p className="text-2xl font-bold font-mono text-foreground capitalize">{proxMesNome.slice(0, 3)}</p>
            <p className="text-[9px] tracking-[0.2em] uppercase text-muted-foreground font-mono mt-1">Mês alvo</p>
          </div>
          <div className="p-3 rounded-lg border border-border bg-card/80 backdrop-blur-sm">
            <p className="text-2xl font-bold font-mono text-foreground">{dataAlvo.getFullYear()}</p>
            <p className="text-[9px] tracking-[0.2em] uppercase text-muted-foreground font-mono mt-1">Ano</p>
          </div>
        </div>

        {/* Linha de progresso indeterminada */}
        <div className="relative h-1 w-full bg-muted/30 rounded-full overflow-hidden mb-3">
          <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-accent to-transparent animate-[shimmer_2s_linear_infinite]" />
        </div>

        <p className="text-[10px] tracking-[0.25em] uppercase text-muted-foreground/70 font-mono">
          Sistema ativo · Aguardando virada do mês
        </p>
      </div>
    </div>
  );
}

/* =========================================================================
 * UI HELPERS
 * ========================================================================= */

function Section({
  title, icon: Icon, children, subtitle,
}: { title: string; icon: any; children: React.ReactNode; subtitle?: string }) {
  return (
    <section className="mb-6 animate-fade-in">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="h-4 w-4 text-accent" />
        <h2 className="text-sm font-bold tracking-[0.2em] uppercase text-foreground">{title}</h2>
        {subtitle && <span className="text-[10px] font-mono text-muted-foreground tracking-wider">· {subtitle}</span>}
      </div>
      {children}
    </section>
  );
}

function MetricCard({
  label, value, icon: Icon, hint, variant = "default",
}: {
  label: string; value: React.ReactNode; icon?: any; hint?: React.ReactNode;
  variant?: "default" | "success" | "warning" | "critical";
}) {
  const variantClass = {
    default: "border-border",
    success: "border-success/40",
    warning: "border-warning/40",
    critical: "border-critical/40",
  }[variant];
  const valueColor = {
    default: "text-foreground",
    success: "text-success",
    warning: "text-warning",
    critical: "text-critical",
  }[variant];

  return (
    <div className={`relative p-3 sm:p-4 rounded-lg border bg-card/80 backdrop-blur-sm hover:border-accent/40 transition-all ${variantClass}`}>
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono">{label}</p>
        {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground/70 shrink-0" />}
      </div>
      <p className={`text-xl sm:text-2xl font-bold font-mono ${valueColor}`}>{value}</p>
      {hint && <div className="mt-1 text-[10px] text-muted-foreground">{hint}</div>}
    </div>
  );
}

function TrendPill({ delta, suffix = "" }: { delta?: number | null; suffix?: string }) {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return null;
  const Icon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
  const color = delta > 0 ? "text-success" : delta < 0 ? "text-critical" : "text-muted-foreground";
  const sign = delta > 0 ? "+" : "";
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-mono ${color}`}>
      <Icon className="h-3 w-3" /> {sign}{typeof delta === "number" ? delta.toFixed(1) : delta}{suffix}
    </span>
  );
}

/* helpers seguros (o backend pode não preencher tudo) */
const num = (v: any, def = 0): number => (typeof v === "number" && !Number.isNaN(v) ? v : def);
const arr = <T,>(v: any): T[] => (Array.isArray(v) ? v : []);
const obj = (v: any): Record<string, any> => (v && typeof v === "object" && !Array.isArray(v) ? v : {});

const STATUS_COLORS: Record<string, string> = {
  CRITICO: "hsl(var(--critical))",
  CRÍTICO: "hsl(var(--critical))",
  FRACO: "hsl(var(--warning))",
  REGULAR: "hsl(var(--warning))",
  BOM: "hsl(var(--success))",
  EXCELENTE: "hsl(var(--success))",
};
const PRIO_COLORS: Record<string, string> = {
  CRITICA: "border-critical/50 bg-critical/5 text-critical",
  CRÍTICA: "border-critical/50 bg-critical/5 text-critical",
  ALTA: "border-warning/50 bg-warning/5 text-warning",
  MEDIA: "border-accent/50 bg-accent/5 text-accent",
  MÉDIA: "border-accent/50 bg-accent/5 text-accent",
  BAIXA: "border-border bg-muted/20 text-muted-foreground",
};

const CHART_COLORS = [
  "hsl(90, 40%, 45%)",
  "hsl(43, 70%, 55%)",
  "hsl(180, 50%, 45%)",
  "hsl(0, 60%, 55%)",
  "hsl(270, 40%, 55%)",
  "hsl(30, 70%, 55%)",
  "hsl(200, 50%, 50%)",
  "hsl(140, 40%, 45%)",
];

/* =========================================================================
 * PÁGINA
 * ========================================================================= */

export default function RelatorioMensalPage() {
  // Enquanto o mês corrente não fechar (ou seja, antes do próximo dia 1º),
  // mostramos o loader em loop com a mensagem "Juntando mais informações".
  // A consulta à API só é habilitada após a virada do mês.
  const hoje = new Date();
  const aguardandoFechamento = hoje.getDate() !== 1 ? false : false; // sempre aguarda até virar o mês
  // Regra: como este é o PRIMEIRO mês de uso, o relatório só existe a partir do próximo dia 1º.
  // Comportamento: sempre renderizar o WaitingNextMonthLoader até a data virar.
  // Para destravar quando o mês virar, basta o componente re-renderizar (o setInterval interno cuida disso).
  const { dias } = diasAteProximoMes(hoje);
  const aindaNaoLiberado = dias > 0 && hoje.getDate() !== 1;

  const { data, isLoading, isError, error } = useRelatorioMensal();
  const { mes, ano } = mesAnterior();

  if (aindaNaoLiberado) {
    return (
      <AppLayout>
        <div className="page-header">
          <p className="text-[10px] tracking-[0.3em] uppercase text-accent font-mono mb-1 flex items-center gap-2">
            <Radio className="h-3 w-3 animate-pulse-glow" /> Relatório consolidado
          </p>
          <h1 className="page-title">Relatório Mensal</h1>
          <p className="page-subtitle">Aguardando o fechamento do mês corrente</p>
        </div>
        <WaitingNextMonthLoader />
      </AppLayout>
    );
  }

  if (isLoading) {
    return (
      <AppLayout>
        <GatheringLoader />
      </AppLayout>
    );
  }

  if (isError) {
    return (
      <AppLayout>
        <div className="page-header">
          <h1 className="page-title">Relatório Mensal</h1>
          <p className="page-subtitle">{NOMES_MES[mes - 1]} / {ano}</p>
        </div>
        <ErrorState message={(error as Error)?.message || "Falha ao carregar o relatório."} />
      </AppLayout>
    );
  }

  const r = obj(data);
  const periodo = obj(r.periodo_analise || r.periodo);
  const resumo = obj(r.resumo_geral || r.resumo);
  const sessoes = obj(r.sessoes || r.sessoes_estudo);
  const blocos = obj(r.blocos || r.blocos_questoes);
  const erros = obj(r.analise_erros || r.erros);
  const simulados = obj(r.simulados_semanais || r.simulados);
  const provas = obj(r.provas_oficiais || r.provas);
  const redacoes = obj(r.redacoes);
  const mental = obj(r.estado_mental);
  const comparativo = obj(r.comparativo_mes_anterior || r.comparativo);
  const projecao = obj(r.projecao_fechamento || r.projecao);
  const consistencia = obj(r.score_consistencia || r.consistencia);
  const melhorPior = obj(r.melhor_pior_dia || r);
  const correlacoes = obj(r.correlacoes);
  const balanceamento = arr<any>(r.balanceamento_materias || r.balanceamento);
  const recomendacoes = arr<any>(r.recomendacoes_estrategicas || r.recomendacoes);

  // === Derived charts ===
  const distSessoesData = Object.entries(obj(sessoes.distribuicao_por_tipo || sessoes.por_tipo)).map(([tipo, v]: any) => ({
    tipo,
    minutos: num(v?.minutos ?? v?.tempo_total ?? v?.total_minutos),
    quantidade: num(v?.quantidade ?? v?.total),
    foco: num(v?.foco_medio),
  }));

  const sessoesPorMateria = arr<any>(sessoes.distribuicao_por_materia || sessoes.por_materia).map(m => ({
    materia: m.materia ?? m.nome ?? "—",
    tempo: num(m.tempo_minutos ?? m.minutos ?? m.tempo),
    pct: num(m.percentual ?? m.pct),
  }));

  const blocosPorMateria = arr<any>(blocos.por_materia || blocos.desempenho_por_materia).map(m => ({
    materia: m.materia ?? m.nome ?? "—",
    ipr: num(m.ipr_medio ?? m.ipr),
    questoes: num(m.total_questoes ?? m.questoes),
    acertos: num(m.acertos),
  }));

  const blocosPorAssunto = arr<any>(blocos.por_assunto || blocos.desempenho_por_assunto);
  const distDificuldade = obj(blocos.distribuicao_por_dificuldade || blocos.dificuldade);
  const dificuldadeData = Object.entries(distDificuldade).map(([k, v]) => ({
    dificuldade: `Nível ${k}`,
    total: num(v),
  }));

  const errosPorTipo = obj(erros.por_tipo || erros.tipos);
  const errosData = Object.entries(errosPorTipo).map(([tipo, total]) => ({
    tipo,
    total: num(total),
  }));

  const simuladosLista = arr<any>(simulados.lista || simulados.detalhamento || simulados.itens);
  const evolucaoSimulados = simuladosLista.map((s, i) => ({
    label: s.label ?? `S${i + 1}`,
    pct: num(s.percentual_acerto ?? s.percentual),
    ipr: num(s.ipr),
  }));

  const provasLista = arr<any>(provas.lista || provas.itens);
  const redacoesLista = arr<any>(redacoes.lista || redacoes.itens);
  const evolucaoRedacoes = arr<any>(redacoes.evolucao || redacoes.evolucao_nota).map((p, i) => ({
    label: p.data ? new Date(p.data).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : `R${i + 1}`,
    nota: num(p.nota ?? p.nota_total),
  }));

  const competenciasMedia = obj(redacoes.media_por_competencia || redacoes.competencias);
  const radarComp = Object.entries(competenciasMedia).map(([k, v]) => ({
    comp: `C${String(k).replace(/\D/g, "")}`,
    nota: num(v),
  }));

  const isEmpty = Object.keys(r).length === 0;

  return (
    <AppLayout>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-6">
        <div>
          <p className="text-[10px] tracking-[0.3em] uppercase text-accent font-mono mb-1 flex items-center gap-2">
            <Radio className="h-3 w-3 animate-pulse-glow" /> Relatório consolidado
          </p>
          <h1 className="page-title">Relatório Mensal</h1>
          <p className="page-subtitle">
            {NOMES_MES[mes - 1]} / {ano}
            {periodo.dias_estudados !== undefined && (
              <> · {num(periodo.dias_estudados)} de {num(periodo.dias_no_mes)} dias estudados</>
            )}
          </p>
        </div>
        <div className="px-3 py-2 rounded-md border border-accent/30 bg-accent/5 flex items-center gap-2">
          <CalendarRange className="h-4 w-4 text-accent" />
          <span className="text-[10px] tracking-[0.25em] uppercase text-accent font-bold font-mono">
            Período fechado
          </span>
        </div>
      </div>

      {isEmpty && (
        <div className="rounded-lg border border-border bg-card/60 p-6 text-center mb-6">
          <p className="text-sm text-muted-foreground">
            Nenhum dado retornado pela API para {NOMES_MES[mes - 1]}/{ano}.
          </p>
        </div>
      )}

      {/* RESUMO GERAL */}
      <Section title="Resumo Geral" icon={Activity}>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <MetricCard
            label="Horas líquidas"
            value={formatarHoras(num(resumo.horas_totais_liquidas ?? resumo.horas_liquidas))}
            icon={Clock}
            hint={<TrendPill delta={num(comparativo?.horas?.variacao_pct, NaN)} suffix="%" />}
          />
          <MetricCard
            label="Questões"
            value={num(resumo.total_questoes).toLocaleString("pt-BR")}
            icon={ListChecks}
            hint={<TrendPill delta={num(comparativo?.questoes?.variacao_pct, NaN)} suffix="%" />}
          />
          <MetricCard
            label="Acertos"
            value={`${num(resumo.percentual_medio_acerto ?? resumo.percentual_acerto).toFixed(1)}%`}
            icon={Percent}
            variant={num(resumo.percentual_medio_acerto) >= 70 ? "success" : "warning"}
            hint={<TrendPill delta={num(comparativo?.percentual_acerto?.variacao_pct, NaN)} suffix="%" />}
          />
          <MetricCard
            label="IPR Geral"
            value={`${num(resumo.ipr_geral).toFixed(1)}%`}
            icon={Target}
            variant={num(resumo.ipr_geral) >= 85 ? "success" : num(resumo.ipr_geral) >= 70 ? "warning" : "critical"}
            hint={<TrendPill delta={num(comparativo?.ipr?.variacao_pct, NaN)} suffix="%" />}
          />
          <MetricCard
            label="Questões/dia"
            value={num(resumo.media_questoes_por_dia).toFixed(0)}
            icon={Zap}
          />
          <MetricCard
            label="Dias estudados"
            value={`${num(resumo.percentual_dias_estudo ?? (periodo.dias_estudados / Math.max(1, periodo.dias_no_mes)) * 100).toFixed(0)}%`}
            icon={Flame}
            variant={num(resumo.percentual_dias_estudo) >= 70 ? "success" : "warning"}
          />
        </div>
      </Section>

      {/* CONSISTÊNCIA + MELHOR/PIOR DIA */}
      {(Object.keys(consistencia).length > 0 || melhorPior.melhor_dia || melhorPior.pior_dia) && (
        <Section title="Consistência" icon={Flame}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div className="lg:col-span-1 p-4 rounded-lg border border-border bg-card/80">
              <div className="flex items-center justify-between mb-3">
                <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono">Score</p>
                <span className="text-[10px] font-bold tracking-wider text-accent font-mono">
                  {String(consistencia.classificacao ?? "—").toUpperCase()}
                </span>
              </div>
              <p className="text-4xl font-bold font-mono text-foreground mb-2">
                {num(consistencia.score).toFixed(0)}<span className="text-base text-muted-foreground">/100</span>
              </p>
              <div className="h-1.5 w-full bg-muted/40 rounded-full overflow-hidden mb-3">
                <div
                  className="h-full bg-gradient-to-r from-accent/60 to-accent transition-all"
                  style={{ width: `${Math.min(100, num(consistencia.score))}%` }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <p className="text-muted-foreground">Maior streak</p>
                  <p className="font-mono font-bold text-success">{num(consistencia.maior_streak ?? consistencia.maior_sequencia)}d</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Sem estudo</p>
                  <p className="font-mono font-bold text-critical">{num(consistencia.maior_sequencia_sem_estudo)}d</p>
                </div>
              </div>
            </div>

            {melhorPior.melhor_dia && (
              <div className="p-4 rounded-lg border border-success/40 bg-success/5">
                <div className="flex items-center gap-2 mb-2">
                  <Trophy className="h-4 w-4 text-success" />
                  <p className="text-[10px] tracking-[0.2em] uppercase text-success font-mono font-bold">Melhor dia</p>
                </div>
                <p className="text-lg font-bold font-mono">
                  {melhorPior.melhor_dia.data ? new Date(melhorPior.melhor_dia.data).toLocaleDateString("pt-BR") : "—"}
                </p>
                <p className="text-xs text-muted-foreground capitalize mb-2">{melhorPior.melhor_dia.dia_semana ?? ""}</p>
                <div className="grid grid-cols-3 gap-2 text-[11px]">
                  <div><span className="text-muted-foreground">H </span><span className="font-mono">{formatarHoras(num(melhorPior.melhor_dia.horas))}</span></div>
                  <div><span className="text-muted-foreground">Q </span><span className="font-mono">{num(melhorPior.melhor_dia.questoes)}</span></div>
                  <div><span className="text-muted-foreground">% </span><span className="font-mono">{num(melhorPior.melhor_dia.percentual_acerto).toFixed(0)}</span></div>
                </div>
              </div>
            )}

            {melhorPior.pior_dia && (
              <div className="p-4 rounded-lg border border-critical/40 bg-critical/5">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-critical" />
                  <p className="text-[10px] tracking-[0.2em] uppercase text-critical font-mono font-bold">Pior dia</p>
                </div>
                <p className="text-lg font-bold font-mono">
                  {melhorPior.pior_dia.data ? new Date(melhorPior.pior_dia.data).toLocaleDateString("pt-BR") : "—"}
                </p>
                <p className="text-xs text-muted-foreground capitalize mb-2">{melhorPior.pior_dia.dia_semana ?? ""}</p>
                <div className="grid grid-cols-3 gap-2 text-[11px]">
                  <div><span className="text-muted-foreground">H </span><span className="font-mono">{formatarHoras(num(melhorPior.pior_dia.horas))}</span></div>
                  <div><span className="text-muted-foreground">Q </span><span className="font-mono">{num(melhorPior.pior_dia.questoes)}</span></div>
                  <div><span className="text-muted-foreground">% </span><span className="font-mono">{num(melhorPior.pior_dia.percentual_acerto).toFixed(0)}</span></div>
                </div>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* SESSÕES */}
      {(distSessoesData.length > 0 || sessoesPorMateria.length > 0) && (
        <Section title="Sessões de Estudo" icon={BarChart3}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {distSessoesData.length > 0 && (
              <div className="p-4 rounded-lg border border-border bg-card/80">
                <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-3">
                  Distribuição por tipo (minutos)
                </p>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={distSessoesData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="tipo" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                    <Bar dataKey="minutos" fill="hsl(90, 40%, 45%)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {sessoesPorMateria.length > 0 && (
              <div className="p-4 rounded-lg border border-border bg-card/80">
                <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-3">
                  Tempo por matéria
                </p>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={sessoesPorMateria} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis type="category" dataKey="materia" width={90} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                    <Bar dataKey="tempo" radius={[0, 4, 4, 0]}>
                      {sessoesPorMateria.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* BLOCOS POR MATÉRIA / ASSUNTO */}
      {(blocosPorMateria.length > 0 || blocosPorAssunto.length > 0) && (
        <Section title="Blocos de Questões" icon={ListChecks}>
          {blocosPorMateria.length > 0 && (
            <div className="p-4 rounded-lg border border-border bg-card/80 mb-3">
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-3">IPR por matéria</p>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={blocosPorMateria}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="materia" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} angle={-15} height={50} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                  <Bar dataKey="ipr" radius={[4, 4, 0, 0]}>
                    {blocosPorMateria.map((d, i) => (
                      <Cell key={i} fill={d.ipr >= 85 ? "hsl(var(--success))" : d.ipr >= 70 ? "hsl(var(--warning))" : "hsl(var(--critical))"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {blocosPorAssunto.length > 0 && (
            <div className="p-4 rounded-lg border border-border bg-card/80 overflow-x-auto">
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-3">Desempenho por assunto</p>
              <table className="w-full text-xs">
                <thead className="text-[10px] tracking-wider uppercase text-muted-foreground border-b border-border">
                  <tr>
                    <th className="text-left py-2 pr-3">Assunto</th>
                    <th className="text-right py-2 px-2">IPR</th>
                    <th className="text-center py-2 px-2">Status</th>
                    <th className="text-right py-2 pl-2">Semana</th>
                  </tr>
                </thead>
                <tbody>
                  {blocosPorAssunto.slice(0, 20).map((a: any, i: number) => {
                    const status = String(a.status ?? "—").toUpperCase();
                    return (
                      <tr key={i} className="border-b border-border/40 hover:bg-muted/20">
                        <td className="py-2 pr-3 truncate max-w-[200px]">{a.assunto ?? a.nome ?? "—"}</td>
                        <td className="py-2 px-2 text-right font-mono">{num(a.ipr ?? a.ipr_medio).toFixed(1)}%</td>
                        <td className="py-2 px-2 text-center">
                          <span
                            className="inline-block px-2 py-0.5 rounded text-[9px] font-bold tracking-wider"
                            style={{ background: `${STATUS_COLORS[status] ?? "hsl(var(--muted))"}20`, color: STATUS_COLORS[status] ?? "hsl(var(--muted-foreground))" }}
                          >
                            {status}
                          </span>
                        </td>
                        <td className="py-2 pl-2 text-right font-mono text-muted-foreground">{a.semana_ciclo ?? a.semana ?? "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {dificuldadeData.length > 0 && (
            <div className="p-4 rounded-lg border border-border bg-card/80 mt-3">
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-3">Distribuição por dificuldade</p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={dificuldadeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="dificuldade" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                  <Bar dataKey="total" fill="hsl(43, 70%, 55%)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Section>
      )}

      {/* ANÁLISE DE ERROS */}
      {(errosData.length > 0 || erros.total !== undefined) && (
        <Section title="Análise de Erros" icon={AlertTriangle}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div className="p-4 rounded-lg border border-border bg-card/80">
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-2">Total de erros</p>
              <p className="text-3xl font-bold font-mono text-critical mb-3">{num(erros.total ?? erros.total_erros)}</p>
              {erros.tendencia && (
                <p className="text-[11px] font-mono text-muted-foreground">
                  Tendência:{" "}
                  <span className={`font-bold ${
                    String(erros.tendencia).includes("MELHOR") ? "text-success" :
                    String(erros.tendencia).includes("PIOR") ? "text-critical" : "text-warning"
                  }`}>{erros.tendencia}</span>
                </p>
              )}
            </div>
            {errosData.length > 0 && (
              <div className="lg:col-span-2 p-4 rounded-lg border border-border bg-card/80">
                <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-3">Por tipo</p>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={errosData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis type="category" dataKey="tipo" width={120} tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                    <Bar dataKey="total" fill="hsl(var(--critical))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* SIMULADOS */}
      {evolucaoSimulados.length > 0 && (
        <Section title="Simulados Semanais" icon={Target}>
          <div className="p-4 rounded-lg border border-border bg-card/80">
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={evolucaoSimulados}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="pct" name="% Acerto" stroke="hsl(43, 70%, 55%)" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="ipr" name="IPR" stroke="hsl(90, 40%, 45%)" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      {/* PROVAS */}
      {provasLista.length > 0 && (
        <Section title="Provas Oficiais" icon={Award}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {provasLista.map((p: any, i: number) => (
              <div key={i} className="p-4 rounded-lg border border-border bg-card/80">
                <p className="text-xs font-bold text-foreground truncate">{p.nome ?? p.titulo ?? `Prova ${i + 1}`}</p>
                <p className="text-[10px] text-muted-foreground font-mono mb-2">
                  {p.data ? new Date(p.data).toLocaleDateString("pt-BR") : ""}
                </p>
                <p className="text-2xl font-bold font-mono text-accent">{num(p.nota_total ?? p.nota)}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* REDAÇÕES */}
      {(redacoesLista.length > 0 || radarComp.length > 0 || evolucaoRedacoes.length > 0) && (
        <Section title="Redações" icon={PenTool}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <MetricCard label="Total" value={redacoesLista.length} icon={FileText} />
            <MetricCard label="Média" value={num(redacoes.nota_media ?? redacoes.media).toFixed(0)} variant="default" />
            <MetricCard label="Máxima" value={num(redacoes.nota_max ?? redacoes.maxima)} variant="success" />
            <MetricCard label="Mínima" value={num(redacoes.nota_min ?? redacoes.minima)} variant="warning" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {radarComp.length > 0 && (
              <div className="p-4 rounded-lg border border-border bg-card/80">
                <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-3">Média por competência</p>
                <ResponsiveContainer width="100%" height={240}>
                  <RadarChart data={radarComp}>
                    <PolarGrid stroke="hsl(var(--border))" />
                    <PolarAngleAxis dataKey="comp" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Radar name="Nota" dataKey="nota" stroke="hsl(43, 70%, 55%)" fill="hsl(43, 70%, 55%)" fillOpacity={0.4} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            )}
            {evolucaoRedacoes.length > 0 && (
              <div className="p-4 rounded-lg border border-border bg-card/80">
                <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-3">Evolução das notas</p>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={evolucaoRedacoes}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} domain={[0, 1000]} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                    <Line type="monotone" dataKey="nota" stroke="hsl(43, 70%, 55%)" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
          {redacoes.competencia_mais_fraca !== undefined && (
            <p className="mt-3 text-xs text-muted-foreground">
              Competência mais fraca: <span className="font-bold text-warning">C{redacoes.competencia_mais_fraca}</span>
            </p>
          )}
        </Section>
      )}

      {/* ESTADO MENTAL */}
      {Object.keys(mental).length > 0 && (
        <Section title="Estado Mental" icon={Brain}>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            <MetricCard label="Foco médio" value={num(mental.foco_medio).toFixed(1)} icon={Brain} />
            <MetricCard label="Energia" value={num(mental.energia_media).toFixed(1)} icon={Zap} />
            <MetricCard label="Confiança" value={num(mental.confianca_media).toFixed(1)} icon={CheckCircle2} />
            <MetricCard label="Ansiedade" value={num(mental.ansiedade_media).toFixed(1)} variant="warning" />
            <MetricCard label="Sono" value={num(mental.qualidade_sono_media ?? mental.sono_medio).toFixed(1)} />
          </div>
        </Section>
      )}

      {/* PROJEÇÃO */}
      {Object.keys(projecao).length > 0 && (
        <Section title="Projeção de Fechamento" icon={GitCompareArrows}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-4 rounded-lg border border-border bg-card/80">
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-2">Horas projetadas</p>
              <p className="text-2xl font-bold font-mono">{formatarHoras(num(projecao.horas_projetadas ?? projecao.horas))}</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                Meta 88h ·{" "}
                <span className={projecao.on_track_horas ? "text-success" : "text-critical"}>
                  {projecao.on_track_horas ? "ON TRACK" : "ABAIXO"}
                </span>
              </p>
            </div>
            <div className="p-4 rounded-lg border border-border bg-card/80">
              <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-2">Questões projetadas</p>
              <p className="text-2xl font-bold font-mono">{num(projecao.questoes_projetadas ?? projecao.questoes).toLocaleString("pt-BR")}</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                Meta 1400 ·{" "}
                <span className={projecao.on_track_questoes ? "text-success" : "text-critical"}>
                  {projecao.on_track_questoes ? "ON TRACK" : "ABAIXO"}
                </span>
              </p>
            </div>
          </div>
        </Section>
      )}

      {/* CORRELAÇÕES */}
      {Object.keys(correlacoes).length > 0 && (
        <Section title="Correlações" icon={GitCompareArrows}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {Object.entries(correlacoes).map(([k, v]) => {
              const val = v === null || v === undefined ? null : num(v);
              return (
                <div key={k} className="p-4 rounded-lg border border-border bg-card/80">
                  <p className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground font-mono mb-2">
                    {k.replace(/_/g, " ")}
                  </p>
                  <p className={`text-2xl font-bold font-mono ${
                    val === null ? "text-muted-foreground" :
                    Math.abs(val) >= 0.5 ? "text-accent" : "text-foreground"
                  }`}>
                    {val === null ? "—" : val.toFixed(2)}
                  </p>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* BALANCEAMENTO */}
      {balanceamento.length > 0 && (
        <Section title="Balanceamento de Matérias" icon={Scale}>
          <div className="p-4 rounded-lg border border-border bg-card/80 overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-[10px] tracking-wider uppercase text-muted-foreground border-b border-border">
                <tr>
                  <th className="text-left py-2 pr-3">Matéria</th>
                  <th className="text-right py-2 px-2">Peso</th>
                  <th className="text-right py-2 px-2">% Tempo</th>
                  <th className="text-right py-2 px-2">% Questões</th>
                  <th className="text-right py-2 px-2">IPR</th>
                  <th className="text-center py-2 pl-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {balanceamento.map((b: any, i: number) => {
                  const status = String(b.classificacao ?? b.status ?? "—").toUpperCase();
                  const color =
                    status.includes("EQUI") ? "text-success" :
                    status.includes("SUB") ? "text-critical" :
                    status.includes("SUPER") ? "text-warning" : "text-muted-foreground";
                  return (
                    <tr key={i} className="border-b border-border/40 hover:bg-muted/20">
                      <td className="py-2 pr-3 truncate">{b.materia ?? b.nome}</td>
                      <td className="py-2 px-2 text-right font-mono">{num(b.peso_prova ?? b.peso).toFixed(1)}</td>
                      <td className="py-2 px-2 text-right font-mono">{num(b.percentual_tempo ?? b.pct_tempo).toFixed(1)}%</td>
                      <td className="py-2 px-2 text-right font-mono">{num(b.percentual_questoes ?? b.pct_questoes).toFixed(1)}%</td>
                      <td className="py-2 px-2 text-right font-mono">{num(b.ipr).toFixed(1)}%</td>
                      <td className={`py-2 pl-2 text-center font-bold tracking-wider text-[10px] ${color}`}>{status}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* RECOMENDAÇÕES */}
      {recomendacoes.length > 0 && (
        <Section title="Recomendações Estratégicas" icon={Award}>
          <div className="space-y-2">
            {recomendacoes.map((rec: any, i: number) => {
              const prio = String(rec.prioridade ?? "MEDIA").toUpperCase();
              const cls = PRIO_COLORS[prio] || PRIO_COLORS.MEDIA;
              return (
                <div key={i} className={`p-3 sm:p-4 rounded-lg border ${cls}`}>
                  <div className="flex items-start gap-3">
                    <span className="text-[9px] font-bold tracking-[0.2em] px-2 py-0.5 rounded border border-current font-mono shrink-0">
                      {prio}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-bold text-foreground mb-0.5">
                        {rec.titulo ?? rec.acao ?? rec.recomendacao ?? "Recomendação"}
                      </p>
                      {(rec.descricao ?? rec.detalhe) && (
                        <p className="text-xs text-muted-foreground">{rec.descricao ?? rec.detalhe}</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      )}
    </AppLayout>
  );
}
