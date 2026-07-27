from __future__ import annotations

from typing import Annotated


from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import LicActual
from db import get_db
from models import Medico, MedicoLicenciada
from schemas import MedicoOut

router = APIRouter(prefix="/medicos", tags=["medicos"])


@router.get("", response_model=list[MedicoOut])
def listar_medicos(
    lic: LicActual, db: Annotated[Session, Depends(get_db)]
) -> list[Medico]:
    """Solo los medicos con los que esta licenciada puede agendar."""
    q = (
        select(Medico)
        .join(MedicoLicenciada, MedicoLicenciada.medico_id == Medico.id)
        .where(MedicoLicenciada.licenciada_id == lic.id, Medico.activo.is_(True))
        .order_by(Medico.nombre)
    )
    return list(db.scalars(q))
