import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import StudyPage from "./pages/StudyPage";
import GoalsPage from "./pages/GoalsPage";
import CoveragePage from "./pages/CoveragePage";
import ReviewPage from "./pages/ReviewPage";
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
import RelatorioMensalPage from "./pages/RelatorioMensalPage";
import ListaRevisaoPage from "./pages/ListaRevisaoPage";
import { useEffect } from "react";
import QuestionBankPage from "./pages/QuestionBankPage";
import QuestionListPage from "./pages/QuestionListPage";
import QuestionPage from "./pages/QuestionPage";
import { toast } from "sonner";

const queryClient = new QueryClient();

function MonthlyReportNotifier() {
  const navigate = useNavigate();
  useEffect(() => {
    const today = new Date();
    
    const key = `provectus:monthly-report-toast:${today.getFullYear()}-${today.getMonth() + 1}`;
    if (localStorage.getItem(key)) return;
    const t = setTimeout(() => {
      toast.success("Relatório mensal pronto", {
        description: "O relatório do mês anterior já está disponível.",
        duration: 8000,
        action: { label: "Ver agora", onClick: () => navigate("/relatorio-mensal") },
      });
      localStorage.setItem(key, "1");
    }, 800);
    return () => clearTimeout(t);
  }, [navigate]);
  return null;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <MonthlyReportNotifier />
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/estudar" element={<StudyPage />} />
          <Route path="/conteudos" element={<CoveragePage />} />
          <Route path="/banco-questoes" element={<QuestionBankPage />} />
          <Route path="/banco-questoes/questoes/:questionId" element={<QuestionPage />} />
          <Route path="/banco-questoes/listas/:id" element={<QuestionListPage />} />
          <Route path="/sessao" element={<SessionForm />} />
          <Route path="/bloco" element={<BlockForm />} />
          <Route path="/simulado" element={<ExamForm />} />
          <Route path="/timer" element={<TimerPage />} />
          <Route path="/historico" element={<HistoryPage />} />
          <Route path="/redacoes" element={<RedacaoList />} />
          <Route path="/redacoes/nova" element={<RedacaoForm />} />
          <Route path="/redacoes/:id" element={<RedacaoDetail />} />
          <Route path="/countdown" element={<CountdownPage />} />
          <Route path="/metas" element={<GoalsPage />} />
          <Route path="/relatorio-mensal" element={<RelatorioMensalPage />} />
          <Route path="/revisao" element={<ReviewPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
