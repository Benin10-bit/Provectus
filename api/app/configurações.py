from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app import schemas, services
from app.database import get_db


router = APIRouter(
    prefix="/configuracoes",
    tags=["Configurações"]
)

# =========================
# MATÉRIAS
# =========================

@router.get(
    "/materias",
    response_model=List[schemas.MateriaResponse],
    summary="Listar matérias"
)
def listar_materias(db: Session = Depends(get_db)):
    return services.listar_materias(db)


# =========================
# ASSUNTOS
# =========================

@router.get(
    "/assuntos",
    response_model=List[schemas.AssuntoResponse],
    summary="Listar assuntos"
)
def listar_assuntos(
    materia_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db)
):
    return services.listar_assuntos(db, materia_id)


@router.get(
    "/materias/{materia_id}/assuntos",
    response_model=List[schemas.AssuntoResponse],
    summary="Listar assuntos por matéria"
)
def listar_assuntos_por_materia(
    materia_id: UUID,
    db: Session = Depends(get_db)
):
    return services.listar_assuntos_por_materia(db, materia_id)