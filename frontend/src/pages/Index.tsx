import CardRecomendacao from "@/components/dashboard/CardRecomendacao";
import KpiCard from "@/components/dashboard/KpiCard";
import MissionStatus from "@/components/dashboard/MissionStatus";
import PerformanceChart from "@/components/dashboard/PerformanceChart";
import PieChartMaterias from "@/components/dashboard/PieChartMaterias";
import { MediaRedacoesCard, ProgressoRedacoesChart, UltimaRedacaoCard } from "@/components/dashboard/RedacaoCards";
import { MateriaSelect } from "@/components/form/Selectors";
import AppLayout from "@/components/layout/AppLayout";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useAssuntos } from "@/hooks/useConfiguracoes";
import { useBlocos, useDashboard, useMateriasPerformance, useSimulados } from "@/hooks/usePerformance";
import type { Periodo } from "@/lib/types";
import { formatarHoras } from "@/lib/utils";
import { Clock, ListChecks, Percent, TrendingUp } from "lucide-react";
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
    const { data: materiasPerformance, isLoading: materiasLoading } = useMateriasPerformance(periodo);
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

    const metas = periodo === "semana"
        ? { horas: 22, questoes: 350 }
        : periodo === "mes"
            ? { horas: 88, questoes: 1400 }
            : { horas: 1056, questoes: 16800 };

    const agora = new Date();
    let inicioPeriodo = new Date(2000, 0, 1);

    if (periodo === "semana") {
        const dia = agora.getDay();
        const diff = dia === 0 ? -6 : 1 - dia;
        inicioPeriodo = new Date(agora);
        inicioPeriodo.setDate(agora.getDate() + diff);
        inicioPeriodo.setHours(0, 0, 0, 0);
    }
    if (periodo === "mes") {
        inicioPeriodo = new Date(agora.getFullYear(), agora.getMonth(), 1);
    }
    if (periodo === "ano") {
        inicioPeriodo = new Date(agora.getFullYear(), 0, 1);
    }

    const blocosFiltrados = (blocos || []).filter(b => {
        const data = new Date(b.data);
        data.setHours(0, 0, 0, 0);
        return data >= inicioPeriodo;
    });

    const blocosMateria = blocosFiltrados.filter(b => !materiaId || b.materia_id === materiaId);

    const precisionData = blocosMateria.reverse().map((b, i) => ({
        label: `B${i + 1}`,
        value: b.percentual_acerto,
    }));

    const simuladosFiltrados = (simulados || []).filter(s => {
        const data = new Date(s.criado_em);
        data.setHours(0, 0, 0, 0);
        return data >= inicioPeriodo;
    });

    const simuladoData = simuladosFiltrados.slice(-10).map(s => ({
        label: `C${s.numero_ciclo}S${s.numero_semana}`,
        value: s.percentual_acerto,
    }));

    const statusToVariant = (status: string) =>
        status === "ACIMA"
            ? ("success" as const)
            : status === "ABAIXO"
              ? ("critical" as const)
              : status === "DENTRO"
                ? ("warning" as const)
                : ("default" as const);

    const tendenciaVariant =
        d.tendencia === "ASCENDENTE"
            ? ("success" as const)
            : d.tendencia === "DECLÍNIO"
              ? ("critical" as const)
              : ("warning" as const);

    return (
        <AppLayout>
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 mb-6 sm:mb-8">
                <div>
                    <h1 className="page-title">Painel de Comando</h1>
                    <p className="page-subtitle">Monitoramento de Performance Acadêmica</p>
                </div>

                <div className="flex gap-2 flex-wrap">
                    <select
                        value={periodo}
                        onChange={e => setPeriodo(e.target.value as Periodo)}
                        className="form-select w-auto min-w-[100px]"
                    >
                        {PERIODOS.map(p => (
                            <option key={p.value} value={p.value}>
                                {p.label}
                            </option>
                        ))}
                    </select>
                    <MateriaSelect value={materiaId} onChange={setMateriaId} className="form-select w-auto min-w-[120px]" />
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 stagger-children">
                <KpiCard
                    title="Horas Líquidas"
                    value={formatarHoras(d.horas_liquidas)}
                    meta={`${metas.horas}h`}
                    icon={Clock}
                    variant={statusToVariant(d.status_horas)}
                    subtitle={d.status_horas}
                />
                <KpiCard
                    title="Questões Resolvidas"
                    value={d.total_questoes}
                    meta={metas.questoes}
                    icon={ListChecks}
                    variant={statusToVariant(d.status_questoes)}
                    subtitle={d.status_questoes}
                />
                <KpiCard
                    title="IPR Geral"
                    value={`${d.ipr_geral}%`}
                    icon={Percent}
                    variant={d.ipr_geral >= 85 ? "success" : d.ipr_geral >= 70 ? "warning" : "critical"}
                    subtitle={
                        d.ipr_geral >= 85
                            ? "Excelente performance"
                            : d.ipr_geral >= 70
                              ? "Performance operacional"
                              : "Nível crítico (<70%)"
                    }
                />
                <KpiCard title="Tendência" value={d.tendencia} icon={TrendingUp} variant={tendenciaVariant} />
            </div>

            <CardRecomendacao d={d} />

            {/* Mission Status + Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4 mb-6">
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

            {/* IPR por Matéria */}
            <div className="mb-6">
                <PieChartMaterias data={materiasPerformance || []} />
            </div>

            {/* Redações */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                <UltimaRedacaoCard />
                <MediaRedacoesCard />
                <ProgressoRedacoesChart />
            </div>
        </AppLayout>
    );
}
