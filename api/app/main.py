from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from .database import engine
from .routes.router import router
from . import configurações
from .planner import router as planner_router
from .goals import router as goals_router
from .question_bank import router as question_bank_router

@asynccontextmanager
async def lifespan(app):
    # Schema writes only through the ordered migration command, after backup.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield

app = FastAPI(title="Provectus — Estudos", version="2.2.0", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1,http://localhost:8080,http://127.0.0.1:8080").split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
    allow_methods=["GET","POST","PUT","PATCH","DELETE"],allow_headers=["Content-Type"])

@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409, content={"detail":"Registro conflitante ou referência inválida. Confira os campos e tente novamente."})

app.include_router(router,prefix="/api/v1")
app.include_router(configurações.router)
app.include_router(planner_router)
app.include_router(goals_router)
app.include_router(question_bank_router)

@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.execute(text("SELECT id FROM tb_planejamento WHERE id=1"))
            conn.execute(text("SELECT id FROM tb_config_metas WHERE id=1"))
    except Exception:
        raise HTTPException(503,"Banco indisponível.")
    return {"status":"ok","version":"2.2.0"}
