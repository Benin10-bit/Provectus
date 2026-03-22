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
  Menu,
  X
} from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/sessao", icon: BookOpen, label: "Sessão de Estudo" },
  { to: "/bloco", icon: ListChecks, label: "Bloco de Questões" },
  { to: "/simulado", icon: Target, label: "Simulado" },
  { to: "/redacoes", icon: PenTool, label: "Redações" },
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
        className="md:hidden fixed top-4 left-4 z-50 p-2 rounded-md bg-primary text-primary-foreground"
      >
        <Menu size={20} />
      </button>

      {/* OVERLAY MOBILE */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
        />
      )}

      <aside
        className={`
        fixed left-0 top-0 z-50 h-screen w-64 border-r border-border bg-sidebar flex flex-col
        transform transition-transform duration-300
        ${open ? "translate-x-0" : "-translate-x-full"}
        md:translate-x-0
      `}
      >
        {/* HEADER */}
        <div className="flex items-center justify-between gap-3 px-6 py-5 border-b border-border">
          <div className="flex items-center gap-3">
            <img src="/logo.avif" alt="Provectus" className="h-14 w-14 mt-1 text-accent" />
            <div>
              <h1 className="text-lg font-bold tracking-widest uppercase">
                Provectus
              </h1>
              <p className="text-[10px] tracking-[0.25em] text-muted-foreground uppercase">
                Sistema de Performance EsPCEx
              </p>
            </div>
          </div>

          <button
            onClick={() => setOpen(false)}
            className="md:hidden"
          >
            <X size={18} />
          </button>
        </div>

        {/* NAV */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.to;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-primary text-primary-foreground hud-glow"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* FOOTER */}
        <div className="px-6 py-4 border-t border-border">
          <p className="text-[10px] text-muted-foreground tracking-wider uppercase">
            EsPCEx • Sistema Tático
          </p>
        </div>
      </aside>
    </>
  );
}