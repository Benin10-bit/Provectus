import KpiCard from "@/components/dashboard/KpiCard";
import MissionStatus from "@/components/dashboard/MissionStatus";
import PerformanceChart from "@/components/dashboard/PerformanceChart";
import { MediaRedacoesCard, ProgressoRedacoesChart, UltimaRedacaoCard } from "@/components/dashboard/RedacaoCards";
import { MateriaSelect } from "@/components/form/Selectors";
import AppLayout from "@/components/layout/AppLayout";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useAssuntos } from "@/hooks/useConfiguracoes";
import { useBlocos, useDashboard, useSimulados } from "@/hooks/usePerformance";
import type { Periodo } from "@/lib/types";
import { Clock, Lightbulb, ListChecks, Percent, TrendingUp } from "lucide-react";
import { useState } from "react";

const PERIODOS: { value: Periodo; label: string }[] = [
    { value: "semana", label: "Semana" },
    { value: "mes", label: "Mês" },
    { value: "ano", label: "Ano" },
    { value: "total", label: "Total" },
];

export default function Dashboard() {
    const [periodo, setPeriodo] = useState<Periodo>("semana");
    const [materiaId, setMateriaId] = useState<string>("");

    const { data: dashboard, isLoading, isError } = useDashboard(periodo, materiaId);
    const { data: blocos } = useBlocos();
    const { data: simulados } = useSimulados();
    const { data: assuntos } = useAssuntos();

    const getAssuntoNome = (id: string) => assuntos?.find(a => a.id === id)?.nome ?? id;

    if (isLoading)
        return (
            <AppLayout>
                <LoadingState message="Carregando painel estratégico..." />
            </AppLayout>
        );
    if (isError)
        return (
            <AppLayout>
                <ErrorState message="Falha ao carregar o dashboard." />
            </AppLayout>
        );

    const d = dashboard!;

    // Chart data from API responses (no recalculation)
    let precisionData: { label: string; value: number }[];

    if (materiaId) {
        precisionData = (blocos || [])
            .filter(b => b.materia_id === materiaId)
            .map((b, i) => ({
                label: `B${i + 1}`,
                value: b.percentual_acerto,
            }));
    } else {
        precisionData = (blocos || []).slice(-10).map((b, i) => ({
            label: `B${i + 1}`,
            value: b.percentual_acerto,
        }));
    }

    const simuladoData = (simulados || []).slice(-10).map(s => ({
        label: `C${s.numero_ciclo}S${s.numero_semana}`,
        value: s.percentual_acerto,
    }));

    const statusToVariant = (status: string) =>
        status === "ACIMA" || status === "DENTRO"
            ? ("success" as const)
            : status === "ABAIXO"
              ? ("warning" as const)
              : ("critical" as const);

    const tendenciaVariant =
        d.tendencia === "ASCENDENTE"
            ? ("success" as const)
            : d.tendencia === "DECLÍNIO"
              ? ("critical" as const)
              : ("warning" as const);

    return (
        <AppLayout>
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-2xl font-bold tracking-wider text-foreground uppercase">Painel de Comando</h1>
                    <p className="text-sm text-muted-foreground">Monitoramento de Performance Acadêmica</p>
                </div>

                {/* Filters */}
                <div className="flex gap-2">
                    <select
                        value={periodo}
                        onChange={e => setPeriodo(e.target.value as Periodo)}
                        className="form-select w-auto"
                    >
                        {PERIODOS.map(p => (
                            <option key={p.value} value={p.value}>
                                {p.label}
                            </option>
                        ))}
                    </select>
                    <MateriaSelect value={materiaId} onChange={setMateriaId} className="form-select w-auto" />
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <KpiCard
                    title="Horas Líquidas"
                    value={`${d.horas_liquidas}h`}
                    icon={Clock}
                    variant={statusToVariant(d.status_horas)}
                    subtitle={d.status_horas}
                />
                <KpiCard
                    title="Questões Resolvidas"
                    value={d.total_questoes}
                    icon={ListChecks}
                    variant={statusToVariant(d.status_questoes)}
                    subtitle={d.status_questoes}
                />
                <KpiCard
                    title="IPR Geral"
                    value={`${d.ipr_geral}%`}
                    icon={Percent}
                    variant={d.ipr_geral >= 70 ? "success" : "critical"}
                    subtitle={d.ipr_geral >= 70 ? "Performance operacional" : "Nível crítico (<70%)"}
                />
                <KpiCard title="Tendência" value={d.tendencia} icon={TrendingUp} variant={tendenciaVariant} />
            </div>

            {/* Recomendação Estratégica */}
            <div
                className={`rounded-md border p-6 mb-6 animate-slide-in ${
                    d.status_missao === "MISSÃO CUMPRIDA"
                        ? "border-success/50 bg-success/10"
                        : "border-critical/50 bg-critical/10"
                }`}
            >
                <div className="flex items-start gap-3">
                    <Lightbulb
                        className={`h-6 w-6 mt-0.5 ${
                            d.status_missao === "MISSÃO CUMPRIDA" ? "text-success" : "text-critical"
                        }`}
                    />
                    <div>
                        <p className="text-xs tracking-wider text-muted-foreground uppercase mb-1">
                            Recomendação Estratégica
                        </p>
                        <p
                            className={`text-xl font-bold tracking-wide mb-2 ${
                                d.status_missao === "MISSÃO CUMPRIDA" ? "text-success" : "text-critical"
                            }`}
                        >
                            {d.recomendacao}
                        </p>
                        <p className="text-sm text-muted-foreground leading-relaxed">{d.status_missao}</p>
                    </div>
                </div>
            </div>

            {/* Mission Status + Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
                <MissionStatus
                    status={d.status_missao}
                    tendencia={d.tendencia}
                    assuntosCriticos={d.assuntos_criticos.map(getAssuntoNome)}
                />
                <PerformanceChart
                    title="Precisão por Bloco"
                    data={precisionData}
                    type="line"
                    color="hsl(43, 70%, 50%)"
                    unit="%"
                />
                <PerformanceChart
                    title="Desempenho em Simulados"
                    data={simuladoData}
                    type="bar"
                    color="hsl(90, 40%, 35%)"
                    unit="%"
                />
            </div>

            {/* Redações */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <UltimaRedacaoCard />
                <MediaRedacoesCard />
                <ProgressoRedacoesChart />
            </div>
        </AppLayout>
    );
}
