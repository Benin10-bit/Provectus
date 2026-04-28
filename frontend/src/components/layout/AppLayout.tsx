import AppSidebar from "./AppSidebar";

interface AppLayoutProps {
  children: React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-background relative">
      {/* Global background textures */}
      <div className="fixed inset-0 bg-grid-fade opacity-[0.18] pointer-events-none" aria-hidden />
      <div className="fixed inset-0 scanline opacity-50 pointer-events-none" aria-hidden />

      <AppSidebar />

      <main className="relative min-h-screen md:ml-64 transition-all duration-300 pt-14 md:pt-0">
        <div className="p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
