import { useLocation } from "react-router-dom";
import { useEffect } from "react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="tac-card text-center max-w-md mx-4 p-10">
        <h1 className="mb-4 text-6xl font-bold">404</h1>
        <p className="mb-4 text-xl text-muted-foreground">Página não encontrada</p>
        <a href="/" className="btn-tactical inline-flex">
          Voltar ao painel
        </a>
      </div>
    </div>
  );
};

export default NotFound;
