import DashboardKpis from "@/components/dashboard/DashboardKpis";
import { SectionHeading, ActionArrow } from "@/components/experience/StudyUI";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { request } from "@/lib/api";
import { getNow } from "@/lib/study";
import type {
  BlocoQuestoesResponse,
  SimuladoSemanalResponse,
} from "@/lib/types";
import CardRecomendacao from "@/components/dashboard/CardRecomendacao";
import {
  WeeklyGoals,
  StudySuggestions,
} from "@/components/dashboard/WeeklyGoals";
import MissionStatus from "@/components/dashboard/MissionStatus";
import PerformanceChart from "@/components/dashboard/PerformanceChart";
import PieChartMaterias from "@/components/dashboard/PieChartMaterias";
import {
  MediaRedacoesCard,
  ProgressoRedacoesChart,
  UltimaRedacaoCard,
} from "@/components/dashboard/RedacaoCards";
import { MateriaSelect } from "@/components/form/Selectors";
import AppLayout from "@/components/layout/AppLayout";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useAssuntos } from "@/hooks/useConfiguracoes";
import {
  useBlocos,
  useDashboard,
  useMateriasPerformance,
  useSimulados,
} from "@/hooks/usePerformance";
import type { Periodo } from "@/lib/types";
import { formatarHoras } from "@/lib/utils";
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

  const {
    data: dashboard,
    isLoading,
    isError,
  } = useDashboard(periodo, materiaId);
  const suggestion = useQuery({
    queryKey: ["estudos", "agora"],
    queryFn: getNow,
  });
  const series = useQuery({
    queryKey: ["performance", "series", periodo, materiaId],
    queryFn: () =>
      request<{
        blocos: BlocoQuestoesResponse[];
        simulados: SimuladoSemanalResponse[];
      }>(
        `/api/v1/estudos/series?periodo=${periodo}${materiaId ? `&materia_id=${materiaId}` : ""}`,
      ),
  });
  const blocos = series.data?.blocos,
    simulados = series.data?.simulados;
  const { data: materiasPerformance, isLoading: materiasLoading } =
    useMateriasPerformance(periodo);
  const { data: assuntos } = useAssuntos();

  const getAssuntoNome = (id: string) =>
    assuntos?.find((a) => a.id === id)?.nome ?? id;

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

  if (!dashboard)
    return (
      <AppLayout>
        <ErrorState message="Painel sem dados no momento." />
      </AppLayout>
    );

  const d = dashboard;

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

  const blocosFiltrados = blocos || []; // Período já delimitado pela API no fuso de estudo.

  const blocosMateria = blocosFiltrados.filter(
    (b) => !materiaId || b.materia_id === materiaId,
  );

  const precisionData = blocosMateria.reverse().map((b, i) => ({
    label: `B${i + 1}`,
    value: b.percentual_acerto,
  }));

  const simuladosFiltrados = simulados || [];

  const simuladoData = simuladosFiltrados
    .slice(0, 10)
    .reverse()
    .map((s) => ({
      label: `C${s.numero_ciclo}S${s.numero_semana}`,
      value: s.percentual_acerto,
    }));

  return (
    <AppLayout>
      {/* Header */}
      <div className="dashboard-heading page-header flex flex-col xl:flex-row xl:items-end xl:justify-between gap-5">
        <div>
          <p className="page-eyebrow">ESTUDOS & PERFORMANCE</p>
          <h1 className="page-title">Painel de Comando</h1>
          
        </div>

        <div className="dashboard-filters flex gap-2 flex-wrap">
          <select
            aria-label="Período do dashboard"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value as Periodo)}
            className="form-select w-auto min-w-[100px]"
          >
            {PERIODOS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
          <MateriaSelect
            value={materiaId}
            onChange={setMateriaId}
            className="form-select w-auto min-w-[120px]"
          />
        </div>
      </div>

      <DashboardKpis d={d} period={periodo} materia={materiaId}/>

      <SectionHeading number="01" title="Sua semana" description="Execução do plano e pontos que pedem atenção." />
      <div className="dashboard-overview">
        <div className="dashboard-goals-column"><WeeklyGoals /></div>
        <MissionStatus academic={d.status_academico} academicVariant={d.variante_academica} details={d.assuntos_criticos_detalhes} context={d.criticidade_contexto} status={d.status_missao} variant={d.variante_missao} tendencia={d.tendencia} assuntosCriticos={d.assuntos_criticos.map(getAssuntoNome)} />
      </div>
      <div className="dashboard-action-grid">
        <div className="tac-card next-session dashboard-next">
          <div><p className="page-eyebrow">PRÓXIMA AÇÃO</p>
            <h2>{suggestion.data?.recomendacao ? `${suggestion.data.recomendacao.materia} · ${suggestion.data.recomendacao.assunto}` : "Ciclo aguardando definição"}</h2>
            <p className="text-sm text-muted-foreground mt-3">{suggestion.data?.recomendacao?.tarefa ?? "Retome seu ciclo com matéria, assunto e atividade definidos."}</p>
          </div>
          <Link to="/estudar" className="btn-tactical inline-flex">Estudar agora <ActionArrow /></Link>
        </div>
        <CardRecomendacao d={d} materia={materiaId} />
      </div>
      {series.isError && <ErrorState message="Falha ao carregar as séries dos gráficos." />}
      <SectionHeading number="02" title="Evolução" description="Observe sua precisão ao longo das tentativas." />
      {/* Linha 2 — Gráficos */}
      <div className="bento mb-4 sm:mb-6 stagger-children">
        <div className="bento-3">
          <PerformanceChart
            title="Precisão por Bloco (até 100 recentes)"
            data={precisionData}
            type="line"
            color="hsl(var(--accent))"
            unit="%"
          />
        </div>
        <div className="bento-3">
          <PerformanceChart
            title="Simulados globais (10 recentes)"
            data={simuladoData}
            type="bar"
            color="hsl(var(--olive))"
            unit="%"
          />
        </div>
      </div>

      <SectionHeading number="03" title="Mapa de desempenho" description="Amostra e precisão por matéria para orientar sua leitura." />
      {/* IPR por Matéria */}
      <div className="mb-4 sm:mb-6">
        <PieChartMaterias data={materiasPerformance || []} />
      </div>

      {/* Redações */}
      <StudySuggestions />
      <SectionHeading number="04" title="Desempenho em redação" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 stagger-children">
        <UltimaRedacaoCard />
        <MediaRedacoesCard />
        <ProgressoRedacoesChart />
      </div>
    </AppLayout>
  );
}
