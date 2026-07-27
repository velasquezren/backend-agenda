from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional



from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ESTADOS = ("programada", "cumplida", "cancelada", "no_asistio")


class Base(DeclarativeBase):
    pass


class MedicoLicenciada(Base):
    """Que licenciada puede agendar con que medico."""

    __tablename__ = "medico_licenciada"

    medico_id: Mapped[int] = mapped_column(
        ForeignKey("medico.id"), primary_key=True
    )
    licenciada_id: Mapped[int] = mapped_column(
        ForeignKey("licenciada.id"), primary_key=True
    )


class Medico(Base):
    __tablename__ = "medico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#4f46e5")
    horario_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    licenciadas: Mapped[list["Licenciada"]] = relationship(
        secondary="medico_licenciada", back_populates="medicos"
    )


class Licenciada(Base):
    __tablename__ = "licenciada"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    usuario: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    medicos: Mapped[list[Medico]] = relationship(
        secondary="medico_licenciada", back_populates="licenciadas"
    )


class Paciente(Base):
    __tablename__ = "paciente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    telefono: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class Serie(Base):
    """Patron de una serie recurrente. Las citas hijas viven en `cita`."""

    __tablename__ = "serie"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    medico_id: Mapped[int] = mapped_column(ForeignKey("medico.id"), nullable=False)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), nullable=False)
    licenciada_id: Mapped[int] = mapped_column(
        ForeignKey("licenciada.id"), nullable=False
    )
    dias_semana: Mapped[str] = mapped_column(String(20), nullable=False)  # ISO "1,3,5"
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    fecha_desde: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class Cita(Base):
    __tablename__ = "cita"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    medico_id: Mapped[int] = mapped_column(ForeignKey("medico.id"), nullable=False)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), nullable=False)
    licenciada_id: Mapped[int] = mapped_column(
        ForeignKey("licenciada.id"), nullable=False
    )
    serie_id: Mapped[Optional[int]] = mapped_column(ForeignKey("serie.id"), nullable=True)
    inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fin: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    estado: Mapped[str] = mapped_column(
        Enum(*ESTADOS, name="estado_cita"), nullable=False, default="programada"
    )
    notas: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    medico: Mapped[Medico] = relationship()
    paciente: Mapped[Paciente] = relationship()

    __table_args__ = (Index("idx_medico_rango", "medico_id", "inicio", "fin"),)
