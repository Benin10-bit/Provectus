import { useMemo, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import { useBlocos, useSessoes } from "@/hooks/usePerformance";
import { useMaterias, useAssuntos } from "@/hooks/useConfiguracoes";
import { AlertTriangle, Clock, Flame, RotateCcw, Search, ShieldAlert } from "lucide-react";

type UrgencyLevel = "fresco" | "recente" | "atencao" | "critico" | "urgente";

interface RevisaoItem {
  assunto_id: string;
  assunto_nome: string;
  materia_id: string;
  materia_nome: string;
  ultima_data: Date;
  dias: number;
  total_blocos: number;
  total_sessoes: number;
  total_questoes: number;
  total_acertos: number;
  total_minutos: number;
  percentual_acerto: number;
  level: UrgencyLevel;
}

const LEVELS: Record<UrgencyLevel, {
  label: string;
  min: number;
  max: number | null;
  border: string;
  bg: string;
  text: string;
  ring: string;
  chipBg: string;
  icon: typeof Clock;
}> = {
  fresco:   { label: "Fresco",    min: 0,  max: 7,  border: "border-success/40",  bg: "bg-success/5",   text: "text-success",  ring: "ring-success/30",  chipBg: "bg-success/15",  icon: Clock },
  recente:  { label: "Recente",   min: 8,  max: 15, border: "border-accent/40",   bg: "bg-accent/5",    text: "text-accent",   ring: "ring-accent/30",   chipBg: "bg-accent/15",   icon: RotateCcw },
  atencao:  { label: "Atenção",   min: 16, max: 30, border: "border-warning/40",  bg: "bg-warning/5",   text: "text-warning",  ring: "ring-warning/30",  chipBg: "bg-warning/15",  icon: AlertTriangle },
  critico:  { label: "Crítico",   min: 31, max: 60, border: "border-orange-500/50", bg: "bg-orange-500/5", text: "text-orange-400", ring: "ring-orange-500/30", chipBg: "bg-orange-500/15", icon: ShieldAlert },
  urgente:  { label: "Urgente",   min: 61, max: null, border: "border-critical/50", bg: "bg-critical/5",  text: "text-critical", ring: "ring-critical/30", chipBg: "bg-critical/15", icon: Flame },
};

function levelFor(dias: number): UrgencyLevel {
  if (dias <= 7) return "fresco";
  if (dias <= 15) return "recente";
  if (dias <= 30) return "atencao";
  if (dias <= 60) return "critico";
  return "urgente";
}

const LEVEL_ORDER: UrgencyLevel[] = ["urgente", "critico", "atencao", "recente", "fresco"];

export default function ListaRevisaoPage() {
  const { data: blocos, isLoading: isLoadingBlocos, isError: isErrorBlocos } = useBlocos(0, 500);
  const { data: sessoes, isLoading: isLoadingSessoes, isError: isErrorSessoes } = useSessoes(0, 500);
  const { data: materias } = useMaterias();
  const { data: assuntos } = useAssuntos();

  const [busca, setBusca] = useState("");
  const [filtroLevel, setFiltroLevel] = useState<UrgencyLevel | "todos">("todos");

  const isLoading = isLoadingBlocos || isLoadingSessoes;
  const isError = isErrorBlocos || isErrorSessoes;

  const items: RevisaoItem[] = useMemo(() => {
    const temBlocos = blocos && blocos.length > 0;
    const temSessoes = sessoes && sessoes.length > 0;
    if (!temBlocos && !temSessoes) return [];

    const mMap = new Map(materias?.map(m => [m.id, m.nome]) ?? []);
    const aMap = new Map(assuntos?.map(a => [a.id, a.nome]) ?? []);

    const grupos = new Map<string, RevisaoItem>();
    const now = Date.now();

    const diasDesde = (dataStr: string) =>
      Math.floor((now - new Date(dataStr).getTime()) / (1000 * 60 * 60 * 24));

    const getOrCreate = (assunto_id: string, materia_id: string, dataStr: string) => {
      let item = grupos.get(assunto_id);
      if (!item) {
        item = {
          assunto_id,
          assunto_nome: aMap.get(assunto_id) ?? assunto_id,
          materia_id,
          materia_nome: mMap.get(materia_id) ?? materia_id,
          ultima_data: new Date(dataStr),
          dias: diasDesde(dataStr),
          total_blocos: 0,
          total_sessoes: 0,
          total_questoes: 0,
          total_acertos: 0,
          total_minutos: 0,
          percentual_acerto: 0,
          level: "fresco",
        };
        grupos.set(assunto_id, item);
      }
      return item;
    };

    const atualizaData = (item: RevisaoItem, dataStr: string) => {
      const data = new Date(dataStr);
      if (data.getTime() > item.ultima_data.getTime()) {
        item.ultima_data = data;
        item.dias = diasDesde(dataStr);
      }
    };

    // Blocos de questões
    for (const b of blocos ?? []) {
      const dataStr = b.data ?? b.criado_em;
      const item = getOrCreate(b.assunto_id, b.materia_id, dataStr);
      item.total_blocos += 1;
      item.total_questoes += b.total_questoes;
      item.total_acertos += b.total_acertos;
      atualizaData(item, dataStr);
    }

    // Sessões de estudo (teoria/questões/revisão) — também contam como contato com o assunto
    for (const s of sessoes ?? []) {
      const dataStr = s.data ?? s.criado_em;
      const item = getOrCreate(s.assunto_id, s.materia_id, dataStr);
      item.total_sessoes += 1;
      item.total_minutos += s.minutos_liquidos;
      atualizaData(item, dataStr);
    }

    const arr = Array.from(grupos.values()).map(it => ({
      ...it,
      percentual_acerto: it.total_questoes > 0 ? Math.round((it.total_acertos / it.total_questoes) * 100) : 0,
      level: levelFor(it.dias),
    }));

    arr.sort((a, b) => b.dias - a.dias);
    return arr;
  }, [blocos, sessoes, materias, assuntos]);

  const counts = useMemo(() => {
    const c: Record<UrgencyLevel, number> = { fresco: 0, recente: 0, atencao: 0, critico: 0, urgente: 0 };
    items.forEach(i => { c[i.level] += 1; });
    return c;
  }, [items]);

  const filtered = useMemo(() => {
    return items.filter(i => {
      if (filtroLevel !== "todos" && i.level !== filtroLevel) return false;
      if (busca && !`${i.assunto_nome} ${i.materia_nome}`.toLowerCase().includes(busca.toLowerCase())) return false;
      return true;
    });
  }, [items, busca, filtroLevel]);

  return (
    <AppLayout>
      <div className="page-header">
        <p className="text-[10px] tracking-[0.3em] uppercase text-accent font-mono mb-1">
          ▸ Radar de conteúdos estudados
        </p>
        <h1 className="page-title">Lista de Revisão</h1>
        <p className="page-subtitle">
          Todos os assuntos que você já estudou, ordenados por urgência de revisão.
          Qualquer bloco de questões ou sessão de estudo reinicia a contagem daquele assunto.
        </p>
      </div>

      {isLoading ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState />
      ) : items.length === 0 ? (
        <EmptyState message="Nenhum bloco ou sessão registrada ainda. Registre um estudo para começar a montar sua lista de revisão." />
      ) : (
        <>
          {/* LEGENDA / FILTROS */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mb-4">
            <button
              onClick={() => setFiltroLevel("todos")}
              className={`p-3 rounded-lg border transition-all text-left ${
                filtroLevel === "todos" ? "border-accent bg-accent/10 ring-1 ring-accent/40" : "border-border bg-card/60 hover:border-accent/30"
              }`}
            >
              <p className="text-[9px] tracking-[0.2em] uppercase text-muted-foreground font-mono">Todos</p>
              <p className="text-xl font-bold font-mono text-foreground mt-0.5">{items.length}</p>
            </button>
            {LEVEL_ORDER.map(lv => {
              const cfg = LEVELS[lv];
              const Icon = cfg.icon;
              const active = filtroLevel === lv;
              const rangeLabel = cfg.max === null ? `${cfg.min}+ dias` : `${cfg.min}-${cfg.max}d`;
              return (
                <button
                  key={lv}
                  onClick={() => setFiltroLevel(lv)}
                  className={`p-3 rounded-lg border transition-all text-left ${cfg.border} ${cfg.bg} ${
                    active ? `ring-1 ${cfg.ring}` : "hover:brightness-110"
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon className={`h-3 w-3 ${cfg.text}`} />
                    <p className={`text-[9px] tracking-[0.2em] uppercase font-mono font-bold ${cfg.text}`}>
                      {cfg.label}
                    </p>
                  </div>
                  <p className={`text-xl font-bold font-mono ${cfg.text}`}>{counts[lv]}</p>
                  <p className="text-[9px] text-muted-foreground font-mono mt-0.5">{rangeLabel}</p>
                </button>
              );
            })}
          </div>

          {/* SEARCH */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              value={busca}
              onChange={e => setBusca(e.target.value)}
              placeholder="Buscar por assunto ou matéria..."
              className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-border bg-card/80 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/30 transition"
            />
          </div>

          {/* LISTA */}
          {filtered.length === 0 ? (
            <div className="text-center py-10 text-sm text-muted-foreground">
              Nenhum assunto corresponde ao filtro atual.
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map(item => {
                const cfg = LEVELS[item.level];
                const Icon = cfg.icon;
                const totalRegistros = item.total_blocos + item.total_sessoes;
                return (
                  <div
                    key={item.assunto_id}
                    className={`relative rounded-lg border p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center gap-3 transition-all overflow-hidden hover:translate-x-0.5 ${cfg.border} ${cfg.bg}`}
                  >
                    <span className={`absolute top-0 left-0 bottom-0 w-1 ${cfg.text.replace("text-", "bg-")}`} />

                    <div className={`shrink-0 p-2 rounded-md ${cfg.chipBg}`}>
                      <Icon className={`h-4 w-4 ${cfg.text}`} />
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-bold text-foreground truncate">
                        {item.assunto_nome}
                      </p>
                      <p className="text-[11px] text-muted-foreground truncate font-mono">
                        {item.materia_nome} · {totalRegistros} registro{totalRegistros > 1 ? "s" : ""}
                        {item.total_blocos > 0 && (
                          <> · {item.total_acertos}/{item.total_questoes} ({item.percentual_acerto}%)</>
                        )}
                        {item.total_sessoes > 0 && (
                          <> · {item.total_minutos}min estudo</>
                        )}
                      </p>
                    </div>

                    <div className="flex items-center gap-4 shrink-0">
                      <div className="text-right">
                        <p className={`text-lg font-bold font-mono leading-none ${cfg.text}`}>
                          {item.dias}
                          <span className="text-[10px] text-muted-foreground ml-1">d</span>
                        </p>
                        <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                          {item.ultima_data.toLocaleDateString("pt-BR")}
                        </p>
                      </div>
                      <span className={`text-[9px] font-bold tracking-[0.2em] uppercase px-2 py-1 rounded font-mono ${cfg.chipBg} ${cfg.text}`}>
                        {cfg.label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </AppLayout>
  );
}