import { NavLink, useLocation } from "react-router-dom";
import { useState } from "react";
import {
  LayoutDashboard,
  BookOpen,
  ListChecks,
  Target,
  History,
  PenTool,
  Heart,
  Timer,
  CalendarDays,
  Menu,
  X
} from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/sessao", icon: BookOpen, label: "Sessão de Estudo" },
  { to: "/bloco", icon: ListChecks, label: "Bloco de Questões" },
  { to: "/simulado", icon: Target, label: "Simulado" },
  { to: "/redacoes", icon: PenTool, label: "Redações" },
  { to: "/cronograma", icon: CalendarDays, label: "Cronograma" },
  { to: "/timer", icon: Timer, label: "Timer" },
  { to: "/historico", icon: History, label: "Histórico" },
  { to: "/countdown", icon: Heart, label: "Contagem Regressiva" },
];

export default function AppSidebar() {
  const location = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* BOTÃO MOBILE */}
      <button
        onClick={() => setOpen(true)}
        className="md:hidden fixed top-4 left-4 z-50 p-2.5 rounded-lg bg-card border border-border text-foreground shadow-lg backdrop-blur-sm active:scale-95 transition-transform"
      >
        <Menu size={18} />
      </button>

      {/* OVERLAY MOBILE */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden animate-fade-in"
        />
      )}

      <aside
        className={`
        fixed left-0 top-0 z-50 h-screen w-64 border-r border-border bg-sidebar flex flex-col
        transform transition-transform duration-300 ease-out
        ${open ? "translate-x-0" : "-translate-x-full"}
        md:translate-x-0
      `}
      >
        {/* HEADER */}
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <img src="/logo.avif" alt="Provectus" className="h-12 w-12 rounded-md" />
            <div>
              <h1 className="text-base font-bold tracking-widest uppercase text-foreground">
                Provectus
              </h1>
              <p className="text-[9px] tracking-[0.2em] text-muted-foreground uppercase leading-tight">
                Sistema de Performance EsPCEx
              </p>
            </div>
          </div>

          <button
            onClick={() => setOpen(false)}
            className="md:hidden p-1 rounded-md hover:bg-sidebar-accent transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* NAV */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.to;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setOpen(false)}
                className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-primary text-primary-foreground hud-glow"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`}
              >
                <item.icon className={`h-4 w-4 shrink-0 transition-transform duration-200 ${!isActive ? "group-hover:scale-110" : ""}`} />
                <span className="truncate">{item.label}</span>
                {isActive && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-foreground/60" />
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* FOOTER */}
        <div className="px-5 py-3 border-t border-border">
          <p className="text-[9px] text-muted-foreground tracking-wider uppercase">
            EsPCEx • Sistema Tático
          </p>
        </div>
      </aside>
    </>
  );
}
