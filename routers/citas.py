from __future__ import annotations

from datetime import datetime

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from auth import LicActual
from db import get_db
from models import Cita
from schemas import CitaIn, CitaOut, CitaPatch
from services import a_evento, exigir_libre, medico_permitido, paciente_existente

router = APIRouter(prefix="/citas", tags=["citas"])


def _cargar(db: Session, cita_id: int) -> Cita:
    cita = db.scalar(
        select(Cita)
        .options(joinedload(Cita.paciente), joinedload(Cita.medico))
        .where(Cita.id == cita_id)
    )
    if cita is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada")
    return cita


@router.get("", response_model=list[CitaOut])
def listar_citas(
    lic: LicActual,
    db: Annotated[Session, Depends(get_db)],
    medico_id: Annotated[int, Query()],
    desde: Annotated[datetime, Query()],
    hasta: Annotated[datetime, Query()],
    incluir_canceladas: Annotated[bool, Query()] = False,
) -> list[CitaOut]:
    """Citas del medico que caen dentro del rango, en formato FullCalendar."""
    medico_permitido(db, lic, medico_id)

    q = (
        select(Cita)
        .options(joinedload(Cita.paciente), joinedload(Cita.medico))
        .where(Cita.medico_id == medico_id, Cita.inicio < hasta, Cita.fin > desde)
        .order_by(Cita.inicio)
    )
    if not incluir_canceladas:
        q = q.where(Cita.estado != "cancelada")
    return [a_evento(c) for c in db.scalars(q)]


@router.post("", response_model=CitaOut, status_code=status.HTTP_201_CREATED)
def crear_cita(
    datos: CitaIn, lic: LicActual, db: Annotated[Session, Depends(get_db)]
) -> CitaOut:
    medico_permitido(db, lic, datos.medico_id)
    paciente_existente(db, datos.paciente_id)
    exigir_libre(db, datos.medico_id, datos.inicio, datos.fin)

    cita = Cita(
        medico_id=datos.medico_id,
        paciente_id=datos.paciente_id,
        licenciada_id=lic.id,
        inicio=datos.inicio,
        fin=datos.fin,
        notas=datos.notas,
        estado="programada",
    )
    db.add(cita)
    db.commit()
    return a_evento(_cargar(db, cita.id))


@router.patch("/{cita_id}", response_model=CitaOut)
def editar_cita(
    cita_id: int,
    datos: CitaPatch,
    lic: LicActual,
    db: Annotated[Session, Depends(get_db)],
) -> CitaOut:
    """Mueve/edita SOLO esta cita, aunque pertenezca a una serie recurrente."""
    cita = _cargar(db, cita_id)
    medico_permitido(db, lic, cita.medico_id)

    inicio = datos.inicio or cita.inicio
    fin = datos.fin or cita.fin
    if fin <= inicio:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "`fin` debe ser posterior a `inicio`",
        )

    estado = datos.estado or cita.estado
    if estado != "cancelada":
        exigir_libre(db, cita.medico_id, inicio, fin, excluir_cita_id=cita.id)

    if datos.paciente_id is not None:
        paciente_existente(db, datos.paciente_id)
        cita.paciente_id = datos.paciente_id

    cita.inicio = inicio
    cita.fin = fin
    cita.estado = estado
    if datos.notas is not None:
        cita.notas = datos.notas

    db.commit()
    return a_evento(_cargar(db, cita.id))


@router.delete("/{cita_id}", response_model=CitaOut)
def cancelar_cita(
    cita_id: int, lic: LicActual, db: Annotated[Session, Depends(get_db)]
) -> CitaOut:
    """Soft-cancel: no borra la fila, marca estado='cancelada'."""
    cita = _cargar(db, cita_id)
    medico_permitido(db, lic, cita.medico_id)
    cita.estado = "cancelada"
    db.commit()
    return a_evento(_cargar(db, cita.id))
