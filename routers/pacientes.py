from __future__ import annotations

from typing import Annotated


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import LicActual
from db import get_db
from models import Paciente
from schemas import PacienteIn, PacienteOut

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


@router.get("", response_model=list[PacienteOut])
def buscar_pacientes(
    lic: LicActual,
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str, Query(max_length=160)] = "",
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Paciente]:
    consulta = select(Paciente).order_by(Paciente.nombre).limit(limite)
    termino = q.strip()
    if termino:
        consulta = consulta.where(Paciente.nombre.ilike(f"%{termino}%"))
    return list(db.scalars(consulta))


@router.post("", response_model=PacienteOut, status_code=status.HTTP_201_CREATED)
def crear_paciente(
    datos: PacienteIn, lic: LicActual, db: Annotated[Session, Depends(get_db)]
) -> Paciente:
    paciente = Paciente(**datos.model_dump())
    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    return paciente
