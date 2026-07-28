from __future__ import annotations

from datetime import date, datetime, time

from typing import Annotated, Literal, Optional


from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EstadoCita = Literal["programada", "cumplida", "cancelada", "no_asistio"]


# ---------- auth ----------


class LoginIn(BaseModel):
    usuario: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LicenciadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    usuario: str


# ---------- medicos ----------


class MedicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    color: str
    horario_ref: Optional[str] = None


# ---------- pacientes ----------


class PacienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    telefono: Optional[str] = None
    notas: Optional[str] = None


class PacienteIn(BaseModel):
    nombre: Annotated[str, Field(min_length=1, max_length=160)]
    telefono: Annotated[Optional[str], Field(max_length=40)] = None
    notas: Annotated[Optional[str], Field(max_length=500)] = None

    @field_validator("nombre")
    @classmethod
    def _limpiar(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacio")
        return v


# ---------- citas ----------


class CitaIn(BaseModel):
    medico_id: int
    paciente_id: int
    inicio: datetime
    fin: datetime
    notas: Annotated[Optional[str], Field(max_length=500)] = None

    @model_validator(mode="after")
    def _rango_valido(self):
        if self.fin <= self.inicio:
            raise ValueError("`fin` debe ser posterior a `inicio`")
        return self


class CitaPatch(BaseModel):
    inicio: Optional[datetime] = None
    fin: Optional[datetime] = None
    paciente_id: Optional[int] = None
    estado: Optional[EstadoCita] = None
    notas: Annotated[Optional[str], Field(max_length=500)] = None

    @model_validator(mode="after")
    def _rango_valido(self):
        if self.inicio and self.fin and self.fin <= self.inicio:
            raise ValueError("`fin` debe ser posterior a `inicio`")
        return self


class CitaProps(BaseModel):
    """extendedProps del evento de FullCalendar."""

    citaId: int
    medicoId: int
    pacienteId: int
    pacienteNombre: str
    licenciadaId: int
    serieId: Optional[int]
    estado: EstadoCita
    notas: Optional[str]


class CitaOut(BaseModel):
    """Formato de evento de FullCalendar."""

    id: str
    title: str
    start: datetime
    end: datetime
    color: str
    extendedProps: CitaProps


# ---------- series ----------


class SerieIn(BaseModel):
    medico_id: int
    paciente_id: int
    # ISO 1=lunes .. 7=domingo; el domingo lo rechaza el validador de abajo,
    # que da mejor mensaje que un `le=6` a secas.
    dias_semana: list[Annotated[int, Field(ge=1, le=7)]]
    hora_inicio: time
    hora_fin: time
    fecha_desde: date
    fecha_hasta: date
    notas: Annotated[Optional[str], Field(max_length=500)] = None

    @model_validator(mode="after")
    def _validar(self):
        if not self.dias_semana:
            raise ValueError("Elige al menos un dia de la semana")
        if 7 in self.dias_semana:
            raise ValueError("Los domingos no se atiende")
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("`hora_fin` debe ser posterior a `hora_inicio`")
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("`fecha_hasta` debe ser posterior a `fecha_desde`")
        return self


class SerieResultado(BaseModel):
    serie_id: int
    creadas: list[CitaOut]
    conflictos: list[datetime]
