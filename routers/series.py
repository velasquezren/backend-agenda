from __future__ import annotations

from datetime import datetime, timedelta

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from auth import LicActual
from db import get_db
from models import Cita, Serie
from schemas import SerieIn, SerieResultado
from services import a_evento, buscar_solapamiento, medico_permitido, paciente_existente

router = APIRouter(prefix="/series", tags=["series"])

# Tope de seguridad para no generar series absurdas por un typo en fecha_hasta.
MAX_DIAS = 366


@router.post("", response_model=SerieResultado, status_code=status.HTTP_201_CREATED)
def crear_serie(
    datos: SerieIn, lic: LicActual, db: Annotated[Session, Depends(get_db)]
) -> SerieResultado:
    """Crea la serie y genera sus citas hijas.

    Las fechas que chocan con otra cita del medico se omiten y se devuelven
    en `conflictos` (no se aborta toda la serie).
    """
    medico_permitido(db, lic, datos.medico_id)
    paciente_existente(db, datos.paciente_id)

    fecha_hasta = min(datos.fecha_hasta, datos.fecha_desde + timedelta(days=MAX_DIAS))
    dias = set(datos.dias_semana)

    serie = Serie(
        medico_id=datos.medico_id,
        paciente_id=datos.paciente_id,
        licenciada_id=lic.id,
        dias_semana=",".join(str(d) for d in sorted(dias)),
        hora_inicio=datos.hora_inicio,
        hora_fin=datos.hora_fin,
        fecha_desde=datos.fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    db.add(serie)
    db.flush()  # necesitamos serie.id para las citas hijas

    creadas: list[Cita] = []
    conflictos: list[datetime] = []
    dia = datos.fecha_desde
    while dia <= fecha_hasta:
        if dia.isoweekday() in dias:
            inicio = datetime.combine(dia, datos.hora_inicio)
            fin = datetime.combine(dia, datos.hora_fin)
            # Ojo: comparar tambien contra las citas de esta misma serie ya
            # encoladas, que todavia no estan en la base.
            choca = buscar_solapamiento(db, datos.medico_id, inicio, fin) or any(
                c.inicio < fin and c.fin > inicio for c in creadas
            )
            if choca:
                conflictos.append(inicio)
            else:
                cita = Cita(
                    medico_id=datos.medico_id,
                    paciente_id=datos.paciente_id,
                    licenciada_id=lic.id,
                    serie_id=serie.id,
                    inicio=inicio,
                    fin=fin,
                    notas=datos.notas,
                    estado="programada",
                )
                db.add(cita)
                creadas.append(cita)
        dia += timedelta(days=1)

    db.commit()
    for cita in creadas:
        db.refresh(cita)

    return SerieResultado(
        serie_id=serie.id,
        creadas=[a_evento(c) for c in creadas],
        conflictos=conflictos,
    )
