from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app import configurações

from .database import engine, Base
from .routes.router import router


# ==========================================================
# LIFECYCLE CONTROLADO (STARTUP / SHUTDOWN)
# ==========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Controla inicialização e encerramento da aplicação.
    Garante que o banco esteja acessível antes de subir a API.
    """

    try:
        Base.metadata.create_all(bind=engine)
        print("✔ Banco de dados sincronizado.")
    except OperationalError as e:
        print("✖ Falha ao conectar no banco.")
        raise e

    yield

    print("🛑 Encerrando Provectus.")


# ==========================================================
# METADADOS DA API
# ==========================================================

DESCRIPTION = """
## 🎖️ Provectus — Sistema Estratégico de Performance EsPCEx

Plataforma de controle disciplinado voltada para candidatos da EsPCEx.

### Objetivos do Sistema

- Monitoramento de horas líquidas
- Controle de volume de questões
- Cálculo do IPR (Índice de Performance Real)
- Identificação de assuntos críticos (<70%)
- Análise de tendência e execução estratégica

Provectus não é um app de estudos.
É um sistema de execução estratégica rumo à aprovação.
"""


app = FastAPI(
    title="Provectus - EsPCEx Performance System",
    version="2.0.0",
    description=DESCRIPTION,
    contact={
        "name": "Equipe Provectus",
    },
    lifespan=lifespan,
)


# ==========================================================
# CORS CONFIGURÁVEL
# ==========================================================

ALLOWED_ORIGINS = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
# ROTAS
# ==========================================================

app.include_router(router, prefix="/api/v1")
app.include_router(configurações.router)


# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.get(
    "/health",
    tags=["Infraestrutura"],
    summary="Health Check",
    description="Verifica se o sistema está operacional."
)
def health_check():
    return {"status": "ok"}