from datetime import date, datetime, time
from typing import Annotated, Literal

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
    horario_ref: str | None = None


# ---------- pacientes ----------


class PacienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    telefono: str | None = None
    notas: str | None = None


class PacienteIn(BaseModel):
    nombre: Annotated[str, Field(min_length=1, max_length=160)]
    telefono: Annotated[str | None, Field(max_length=40)] = None
    notas: Annotated[str | None, Field(max_length=500)] = None

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
    notas: Annotated[str | None, Field(max_length=500)] = None

    @model_validator(mode="after")
    def _rango_valido(self):
        if self.fin <= self.inicio:
            raise ValueError("`fin` debe ser posterior a `inicio`")
        return self


class CitaPatch(BaseModel):
    inicio: datetime | None = None
    fin: datetime | None = None
    paciente_id: int | None = None
    estado: EstadoCita | None = None
    notas: Annotated[str | None, Field(max_length=500)] = None

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
    serieId: int | None
    estado: EstadoCita
    notas: str | None


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
    dias_semana: list[Annotated[int, Field(ge=1, le=7)]]  # ISO 1=lunes .. 7=domingo
    hora_inicio: time
    hora_fin: time
    fecha_desde: date
    fecha_hasta: date
    notas: Annotated[str | None, Field(max_length=500)] = None

    @model_validator(mode="after")
    def _validar(self):
        if not self.dias_semana:
            raise ValueError("Elige al menos un dia de la semana")
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("`hora_fin` debe ser posterior a `hora_inicio`")
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("`fecha_hasta` debe ser posterior a `fecha_desde`")
        return self


class SerieResultado(BaseModel):
    serie_id: int
    creadas: list[CitaOut]
    conflictos: list[datetime]
