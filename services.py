"""Reglas de negocio compartidas por los routers."""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Cita, Licenciada, Medico, MedicoLicenciada, Paciente
from schemas import CitaOut, CitaProps


def medico_permitido(db: Session, lic: Licenciada, medico_id: int) -> Medico:
    """El medico existe, esta activo y la lic tiene permiso para agendarle."""
    medico = db.get(Medico, medico_id)
    if medico is None or not medico.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medico no encontrado")

    permiso = db.scalar(
        select(MedicoLicenciada).where(
            MedicoLicenciada.medico_id == medico_id,
            MedicoLicenciada.licenciada_id == lic.id,
        )
    )
    if permiso is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No tienes permiso para agendar con este medico",
        )
    return medico


def paciente_existente(db: Session, paciente_id: int) -> Paciente:
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente no encontrado")
    return paciente


def buscar_solapamiento(
    db: Session,
    medico_id: int,
    inicio: datetime,
    fin: datetime,
    excluir_cita_id: int | None = None,
) -> Cita | None:
    """Regla dura: un medico no puede tener dos citas encimadas.

    Dos rangos se solapan si `inicio < otro.fin` y `fin > otro.inicio`.
    Las canceladas no cuentan.
    """
    q = select(Cita).where(
        Cita.medico_id == medico_id,
        Cita.estado != "cancelada",
        Cita.inicio < fin,
        Cita.fin > inicio,
    )
    if excluir_cita_id is not None:
        q = q.where(Cita.id != excluir_cita_id)
    return db.scalars(q.limit(1)).first()


def exigir_libre(
    db: Session,
    medico_id: int,
    inicio: datetime,
    fin: datetime,
    excluir_cita_id: int | None = None,
) -> None:
    """Lanza 409 con el detalle de la cita en conflicto si el hueco esta ocupado."""
    choque = buscar_solapamiento(db, medico_id, inicio, fin, excluir_cita_id)
    if choque is None:
        return
    raise HTTPException(
        status.HTTP_409_CONFLICT,
        {
            "mensaje": "Ese horario ya esta ocupado",
            "cita_id": choque.id,
            "inicio": choque.inicio.isoformat(),
            "fin": choque.fin.isoformat(),
            "paciente": choque.paciente.nombre,
        },
    )


def a_evento(cita: Cita) -> CitaOut:
    """Convierte una cita al formato de evento de FullCalendar."""
    cancelada = cita.estado == "cancelada"
    return CitaOut(
        id=str(cita.id),
        title=cita.paciente.nombre,
        start=cita.inicio,
        end=cita.fin,
        color="#9ca3af" if cancelada else cita.medico.color,
        extendedProps=CitaProps(
            citaId=cita.id,
            medicoId=cita.medico_id,
            pacienteId=cita.paciente_id,
            pacienteNombre=cita.paciente.nombre,
            licenciadaId=cita.licenciada_id,
            serieId=cita.serie_id,
            estado=cita.estado,
            notas=cita.notas,
        ),
    )
