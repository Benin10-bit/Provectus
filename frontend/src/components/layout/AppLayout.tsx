import { useIsFetching, useIsMutating } from "@tanstack/react-query";
import { useSurfaceResponse } from "@/components/experience/StudyUI";
import { ChevronRight, Crosshair } from "lucide-react";
import { useLocation } from "react-router-dom";
import AppSidebar, { navGroups } from "./AppSidebar";
import BackgroundAtmosphere from "@/components/experience/BackgroundAtmosphere";
import ActiveStudyIndicator from "./ActiveStudyIndicator";

interface AppLayoutProps { children: React.ReactNode; }

export default function AppLayout({ children }: AppLayoutProps) {
  const surfaceRef = useSurfaceResponse();
  const fetching = useIsFetching();
  const mutating = useIsMutating();
  const { pathname } = useLocation();
  const group = navGroups.find(g => g.items.some(i => i.to === pathname || (i.to !== "/" && pathname.startsWith(i.to + "/"))));
  const item = group?.items.find(i => i.to === pathname || (i.to !== "/" && pathname.startsWith(i.to + "/")));
  return (
    <div className="app-shell min-h-screen bg-background relative">
      <BackgroundAtmosphere />
      <a href="#conteudo" className="skip-link">Pular para o conteúdo</a>
      <AppSidebar />
      <ActiveStudyIndicator />
      <div className="network-progress" data-busy={fetching + mutating > 0} aria-hidden><span /></div>
      <main id="conteudo" tabIndex={-1} className="app-main relative min-h-screen md:ml-64 pt-14 md:pt-0">
        <header className="workspace-header hidden md:flex">
          <div className="flex items-center gap-3 min-w-0">
            <Crosshair size={15} className="text-primary shrink-0" aria-hidden />
            <span className="text-muted-foreground">{group?.group ?? "PROVECTUS"}</span>
            <ChevronRight size={13} className="text-muted-foreground" aria-hidden />
            <span className="truncate">{item?.label ?? "Performance acadêmica"}</span>
          </div>
          <span className="workspace-signature">PREPARAÇÃO <span>EsPCEx</span></span>
        </header>
        <div ref={surfaceRef} key={pathname} className="page-content p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto animate-fade-in" data-page={pathname.split("/")[1] || "dashboard"}>
          {children}
        </div>
      </main>
    </div>
  );
}
