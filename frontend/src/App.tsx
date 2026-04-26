import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import SessionForm from "./pages/SessionForm";
import BlockForm from "./pages/BlockForm";
import ExamForm from "./pages/ExamForm";
import HistoryPage from "./pages/HistoryPage";
import RedacaoList from "./pages/RedacaoList";
import RedacaoForm from "./pages/RedacaoForm";
import RedacaoDetail from "./pages/RedacaoDetail";
import NotFound from "./pages/NotFound";
import CountdownPage from "./pages/CountdownPage";
import TimerPage from "./pages/TimerPage";
import CronogramaPage from "./pages/CronogramaPage";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/sessao" element={<SessionForm />} />
          <Route path="/bloco" element={<BlockForm />} />
          <Route path="/simulado" element={<ExamForm />} />
          <Route path="/timer" element={<TimerPage />} />
          <Route path="/historico" element={<HistoryPage />} />
          <Route path="/redacoes" element={<RedacaoList />} />
          <Route path="/redacoes/nova" element={<RedacaoForm />} />
          <Route path="/redacoes/:id" element={<RedacaoDetail />} />
          <Route path="/countdown" element={<CountdownPage />} />
          <Route path="/cronograma" element={<CronogramaPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
