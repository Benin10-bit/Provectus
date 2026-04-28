import {
    BookOpen,
    CalendarDays,
    FileBarChart,
    Heart,
    History,
    LayoutDashboard,
    ListChecks,
    Menu,
    PenTool,
    Radio,
    Target,
    Timer,
    X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

const navItems = [
    { to: "/", icon: LayoutDashboard, label: "Dashboard", code: "01" },
    { to: "/sessao", icon: BookOpen, label: "Sessão de Estudo", code: "02" },
    { to: "/bloco", icon: ListChecks, label: "Bloco de Questões", code: "03" },
    { to: "/simulado", icon: Target, label: "Simulado", code: "04" },
    { to: "/redacoes", icon: PenTool, label: "Redações", code: "05" },
    { to: "/cronograma", icon: CalendarDays, label: "Cronograma", code: "06" },
    { to: "/timer", icon: Timer, label: "Timer", code: "07" },
    { to: "/historico", icon: History, label: "Histórico", code: "08" },
    { to: "/relatorio-mensal", icon: FileBarChart, label: "Relatório Mensal", code: "09" },
    { to: "/countdown", icon: Heart, label: "Contagem Regressiva", code: "10" },
];

export default function AppSidebar() {
    const location = useLocation();
    const [open, setOpen] = useState(false);
    const [time, setTime] = useState(new Date());

    // Live clock for the sidebar HUD
    useEffect(() => {
        const t = setInterval(() => setTime(new Date()), 30_000);
        return () => clearInterval(t);
    }, []);

    // Lock body scroll when mobile drawer is open
    useEffect(() => {
        if (open) document.body.style.overflow = "hidden";
        else document.body.style.overflow = "";
        return () => {
            document.body.style.overflow = "";
        };
    }, [open]);

    const horaStr = time.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

    return (
        <>
            {/* MOBILE TOPBAR — substitui o botão flutuante */}
            <header
                className="md:hidden fixed top-0 inset-x-0 z-40 h-14 flex items-center justify-between px-4
                         bg-sidebar/90 backdrop-blur-md border-b border-sidebar-border"
            >
                <button
                    onClick={() => setOpen(true)}
                    aria-label="Abrir menu"
                    className="relative p-2 -ml-2 rounded-lg active:scale-95 transition-transform"
                >
                    <Menu size={20} className="text-foreground" />
                    <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-accent animate-pulse-glow" />
                </button>
                <div className="flex items-center gap-2">
                    <img src="/logo.avif" alt="Provectus" className="h-8 w-8 rounded-md ring-1 ring-accent/30" />
                    <div className="leading-tight">
                        <p className="text-[11px] font-bold tracking-[0.2em] uppercase text-foreground">Provectus</p>
                        <p className="text-[8px] tracking-[0.2em] text-accent/80 font-mono">{horaStr} · LIVE</p>
                    </div>
                </div>
                <span className="w-9" /> {/* spacer for symmetry */}
            </header>

            {/* MOBILE OVERLAY */}
            <div
                onClick={() => setOpen(false)}
                className={`fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden transition-opacity duration-300
          ${open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"}`}
            />

            {/* SIDEBAR */}
            <aside
                className={`
          fixed left-0 top-0 z-50 h-screen w-[78%] max-w-[300px] md:w-64
          border-r border-sidebar-border bg-sidebar flex flex-col
          transform transition-transform duration-300 ease-out
          ${open ? "translate-x-0" : "-translate-x-full"}
          md:translate-x-0
          overflow-hidden
        `}
            >
                {/* Background decorative grid */}
                <div className="absolute inset-0 bg-grid-fade opacity-40 pointer-events-none" />
                {/* Animated scan line (mobile drawer feel) */}
                <div
                    className={`absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent
                      pointer-events-none animate-scan ${open ? "block md:hidden" : "hidden"}`}
                />

                {/* HEADER */}
                <div className="relative flex items-center justify-between gap-3 px-5 py-4 border-b border-sidebar-border">
                    <div className="flex items-center gap-3">
                        <img src="/logo.avif" alt="Provectus" className="h-12 w-12 rounded-md" />
                        <div>
                            <h1 className="text-base font-bold tracking-widest uppercase text-foreground">Provectus</h1>
                            <p className="text-[9px] tracking-[0.2em] text-muted-foreground uppercase leading-tight">
                                Sistema de Performance EsPCEx
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={() => setOpen(false)}
                        aria-label="Fechar menu"
                        className="md:hidden p-1.5 rounded-md hover:bg-sidebar-accent active:scale-90 transition"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* STATUS BAR (mobile-only highlight) */}
                <div className="relative md:hidden mx-3 mt-3 px-3 py-2 rounded-md border border-accent/25 bg-accent/5 flex items-center gap-2">
                    <Radio className="h-3 w-3 text-accent animate-pulse-glow" />
                    <span className="text-[9px] tracking-[0.25em] uppercase text-accent/90 font-bold">Operacional</span>
                    <span className="ml-auto text-[10px] font-mono text-muted-foreground">{horaStr}</span>
                </div>

                {/* NAV */}
                <nav className="relative flex-1 px-3 py-3 mt-1 space-y-1 overflow-y-auto">
                    {navItems.map((item, idx) => {
                        const isActive = location.pathname === item.to;
                        return (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                onClick={() => setOpen(false)}
                                style={{ animationDelay: `${idx * 35}ms` }}
                                className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                            transition-all duration-200 animate-slide-in-left
                  ${
                      isActive
                          ? "bg-primary/95 text-primary-foreground hud-glow"
                          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground hover:translate-x-0.5"
                  }`}
                            >
                                {/* active marker bar */}
                                {isActive && (
                                    <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 bg-accent rounded-r" />
                                )}

                                <item.icon
                                    className={`h-4 w-4 shrink-0 transition-transform duration-200
                    ${isActive ? "scale-110" : "group-hover:scale-110 group-hover:text-accent"}`}
                                />
                                <span className="truncate flex-1">{item.label}</span>

                                <span
                                    className={`text-[9px] font-mono tracking-wider opacity-60
                  ${isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-accent"}`}
                                >
                                    {item.code}
                                </span>

                                {isActive && (
                                    <span className="ml-1 w-1.5 h-1.5 rounded-full bg-primary-foreground/70 animate-pulse-glow" />
                                )}
                            </NavLink>
                        );
                    })}
                </nav>

                {/* FOOTER */}
                <div className="relative px-5 py-3 border-t border-sidebar-border">
                    <div className="flex items-center justify-between">
                        <p className="text-[9px] text-muted-foreground tracking-wider uppercase">
                            EsPCEx · Sistema Tático
                        </p>
                        <span className="text-[9px] font-mono text-accent/80">v2.0</span>
                    </div>
                </div>
            </aside>
        </>
    );
}
