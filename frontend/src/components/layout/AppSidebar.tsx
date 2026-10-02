import {
    BookOpen,
    LibraryBig,
    FileBarChart,
    Heart,
    History,
    LayoutDashboard,
    ListChecks,
    Menu,
    PenTool,
    Radio,
    RotateCcw,
    Target,
    Timer,
    X,
    Zap,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

type NavItem = { to: string; icon: typeof Target; label: string; code: string };

const groups: { group: string; items: Omit<NavItem, "code">[] }[] = [
    {
        group: "Comando",
        items: [
            { to: "/", icon: LayoutDashboard, label: "Painel de Comando" },
            { to: "/estudar", icon: Zap, label: "Estudar agora" },
            { to: "/metas", icon: Target, label: "Metas" },
            { to: "/conteudos", icon: BookOpen, label: "Conteúdos" },
            { to: "/banco-questoes", icon: LibraryBig, label: "Banco de Questões" },
        ],
    },
    {
        group: "Registro",
        items: [
            { to: "/sessao", icon: BookOpen, label: "Sessão de Estudo" },
            { to: "/bloco", icon: ListChecks, label: "Bloco de Questões" },
            { to: "/simulado", icon: Target, label: "Simulado" },
            { to: "/redacoes", icon: PenTool, label: "Redações" },
            { to: "/timer", icon: Timer, label: "Timer" },
        ],
    },
    {
        group: "Análise",
        items: [
            { to: "/revisao", icon: RotateCcw, label: "Lista de Revisão" },
            { to: "/historico", icon: History, label: "Histórico" },
            { to: "/relatorio-mensal", icon: FileBarChart, label: "Relatório Mensal" },
            { to: "/countdown", icon: Heart, label: "Contagem Regressiva" },
        ],
    },
];

export const navGroups = groups.map((group, groupIndex) => ({
    ...group, items: group.items.map((item, index) => ({
        ...item, code: String(groups.slice(0, groupIndex).reduce((n, g) => n + g.items.length, 0) + index + 1).padStart(2, "0"),
    })),
}));

const quickItems: Omit<NavItem, "code">[] = [
    { to: "/estudar", icon: Zap, label: "Estudar" },
    { to: "/bloco", icon: ListChecks, label: "Bloco" },
    { to: "/timer", icon: Timer, label: "Timer" },
];

export default function AppSidebar() {
    const location = useLocation();
    const [open, setOpen] = useState(false);
    const asideRef = useRef<HTMLElement>(null);
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        if (!open) return;
        const previous = document.activeElement as HTMLElement | null;
        const focusable = () =>
            Array.from(asideRef.current?.querySelectorAll<HTMLElement>("button, a[href]") || []).filter(
                e => e.offsetParent !== null,
            );
        focusable()[0]?.focus();
        const handler = (e: KeyboardEvent) => {
            if (e.key === "Escape") setOpen(false);
            if (e.key === "Tab") {
                const nodes = focusable(),
                    first = nodes[0],
                    last = nodes[nodes.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last?.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first?.focus();
                }
            }
        };
        document.addEventListener("keydown", handler);
        return () => {
            document.removeEventListener("keydown", handler);
            previous?.focus();
        };
    }, [open]);

    useEffect(() => {
        const t = setInterval(() => setTime(new Date()), 30_000);
        return () => clearInterval(t);
    }, []);

    useEffect(() => {
        document.body.style.overflow = open ? "hidden" : "";
        return () => {
            document.body.style.overflow = "";
        };
    }, [open]);

    const horaStr = time.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    const currentLabel =
        navGroups.flatMap(g => g.items).find(i => i.to === location.pathname)?.label ?? "Provectus";

    return (
        <>
            {/* MOBILE TOPBAR */}
            <header
                className="md:hidden fixed top-0 inset-x-0 z-40 h-14 flex items-center justify-between gap-3 px-4
                         bg-sidebar/85 backdrop-blur-xl border-b border-sidebar-border"
            >
                <button
                    onClick={() => setOpen(true)}
                    aria-label="Abrir menu"
                    aria-expanded={open}
                    aria-controls="provectus-navigation"
                    className="relative p-2 -ml-2 rounded-lg press"
                >
                    <Menu size={20} className="text-foreground" />
                    <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-accent animate-pulse-glow" />
                </button>

                <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-bold tracking-[0.18em] uppercase text-foreground truncate">
                        {currentLabel}
                    </p>
                    <p className="text-[9px] tracking-[0.22em] text-accent/80 font-mono">{horaStr} · OPERACIONAL</p>
                </div>

                <img src="/logo.avif" alt="Provectus" className="h-8 w-8 rounded-md ring-1 ring-accent/30" />
            </header>

            {/* MOBILE OVERLAY */}
            <div
                onClick={() => setOpen(false)}
                className={`fixed inset-0 bg-background/80 backdrop-blur-md z-40 md:hidden transition-opacity duration-300
          ${open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"}`}
            />

            {/* SIDEBAR / PAINEL MOBILE */}
            <aside
                ref={asideRef}
                id="provectus-navigation"
                aria-label="Menu principal"
                className={`
          provectus-sidebar fixed left-0 top-0 z-50 h-screen w-[86%] max-w-[320px] md:w-64
          border-r border-sidebar-border bg-sidebar/95 backdrop-blur-xl flex flex-col
          transition-[transform,opacity] duration-300 ease-out
          ${open ? "translate-x-0 opacity-100" : "-translate-x-full opacity-0 invisible md:visible md:opacity-100"}
          md:translate-x-0 overflow-hidden
        `}
            >
                <div className="absolute inset-0 bg-grid-fade opacity-40 pointer-events-none" aria-hidden />
                <div className="absolute inset-0 scanline opacity-60 pointer-events-none" aria-hidden />

                {/* HEADER */}
                <div className="sidebar-brand relative flex items-center justify-between gap-3 px-5 py-4 border-b border-sidebar-border">
                    <div className="flex items-center gap-3 min-w-0">
                        <img src="/logo.avif" alt="Provectus" className="h-11 w-11 rounded-md ring-1 ring-accent/25" />
                        <div className="min-w-0">
                            <h1 className="text-lg font-bold tracking-[0.08em] text-foreground">Provectus</h1>
                            <p className="text-[9px] tracking-[0.2em] text-muted-foreground uppercase leading-tight font-mono">
                                Performance EsPCEx
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={() => setOpen(false)}
                        aria-label="Fechar menu"
                        className="md:hidden p-1.5 rounded-md hover:bg-sidebar-accent press"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* STATUS + ATALHOS (mobile) */}
                <div className="relative md:hidden px-3 pt-3 space-y-2">
                    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-accent/25 bg-accent/5">
                        <Radio className="h-3 w-3 text-accent animate-pulse-glow" />
                        <span className="text-[9px] tracking-[0.25em] uppercase text-accent/90 font-bold">
                            Operacional
                        </span>
                        <span className="ml-auto text-[10px] font-mono text-muted-foreground">{horaStr}</span>
                    </div>

                    <div className="grid grid-cols-3 gap-2">
                        {quickItems.map((q, i) => (
                            <NavLink
                                key={q.to}
                                to={q.to}
                                onClick={() => setOpen(false)}
                                style={{ animationDelay: `${i * 60}ms` }}
                                className="animate-scale-in press flex flex-col items-center gap-1 rounded-lg border border-border/70
                                           bg-secondary/40 py-3 text-[10px] font-mono uppercase tracking-[0.12em]
                                           text-muted-foreground hover:border-accent/50 hover:text-accent transition-colors"
                            >
                                <q.icon className="h-4 w-4" />
                                {q.label}
                            </NavLink>
                        ))}
                    </div>
                </div>

                {/* NAV */}
                <nav className="sidebar-navigation relative flex-1 px-3 py-5 space-y-5 overflow-y-auto">
                    {navGroups.map(group => (
                        <div key={group.group} className="space-y-1">
                            <p className="nav-group-label px-3 pb-2 text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                                {group.group}
                            </p>
                            {group.items.map((item, idx) => {
                                const isActive = location.pathname === item.to || (item.to !== "/" && location.pathname.startsWith(`${item.to}/`));
                                return (
                                    <NavLink
                                        key={item.to}
                                        to={item.to}
                                        onClick={() => setOpen(false)}
                                        style={{ animationDelay: `${idx * 30}ms` }}
                                        className={`nav-entry group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                                            animate-slide-in-left transition-all duration-200 press
                                            ${
                                                isActive
                                                    ? "nav-entry-active text-foreground"
                                                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground hover:translate-x-1"
                                            }`}
                                    >
                                        {isActive && (
                                            <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] bg-accent rounded-r" />
                                        )}
                                        <item.icon
                                            className={`h-4 w-4 shrink-0 transition-transform duration-200
                                                ${isActive ? "scale-110" : "group-hover:scale-110 group-hover:text-accent"}`}
                                        />
                                        <span className="truncate flex-1">{item.label}</span>
                                        <span
                                            className={`text-[9px] font-mono tracking-wider opacity-60
                                                ${isActive ? "text-accent" : "text-muted-foreground group-hover:text-accent"}`}
                                        >
                                            {item.code}
                                        </span>
                                    </NavLink>
                                );
                            })}
                        </div>
                    ))}
                </nav>

                {/* FOOTER */}
                <div className="relative px-5 py-3 border-t border-sidebar-border">
                    <div className="flex items-center justify-between">
                        <p className="text-[9px] text-muted-foreground tracking-[0.18em] uppercase font-mono">
                            EsPCEx · Sistema Tático
                        </p>
                        <span className="text-[9px] font-mono text-accent/80">v3.0</span>
                    </div>
                </div>
            </aside>
        </>
    );
}
