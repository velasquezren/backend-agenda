from __future__ import annotations

"""Crea las tablas y carga datos minimos de arranque.


    python seed.py

Es idempotente: si ya existe un medico o una licenciada con ese nombre/usuario,
no lo duplica.
"""

from sqlalchemy import select

from auth import hash_password
from db import SessionLocal, engine
from models import Base, Licenciada, Medico, MedicoLicenciada, Paciente

MEDICOS = [
    ("Dr. Uno", "#4f46e5", "L-V 08:00-14:00"),
    ("Dra. Dos", "#059669", "L-V 14:00-20:00"),
    ("Dr. Tres", "#d97706", "M-J-S 09:00-15:00"),
]

# usuario, nombre, password, indices de MEDICOS con los que puede agendar
LICENCIADAS = [
    ("lic1", "Licenciada Uno", "cambiar123", [0, 1]),
    ("lic2", "Licenciada Dos", "cambiar123", [1, 2]),
    ("admin", "Coordinacion", "cambiar123", [0, 1, 2]),
]

PACIENTES = ["Ana Perez", "Luis Gomez", "Maria Ruiz"]


def main() -> None:
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        medicos = []
        for nombre, color, horario in MEDICOS:
            m = db.scalar(select(Medico).where(Medico.nombre == nombre))
            if m is None:
                m = Medico(nombre=nombre, color=color, horario_ref=horario)
                db.add(m)
                db.flush()
            medicos.append(m)

        for usuario, nombre, password, idx_medicos in LICENCIADAS:
            lic = db.scalar(select(Licenciada).where(Licenciada.usuario == usuario))
            if lic is None:
                lic = Licenciada(
                    nombre=nombre,
                    usuario=usuario,
                    password_hash=hash_password(password),
                )
                db.add(lic)
                db.flush()
            for i in idx_medicos:
                ligado = db.get(MedicoLicenciada, (medicos[i].id, lic.id))
                if ligado is None:
                    db.add(
                        MedicoLicenciada(medico_id=medicos[i].id, licenciada_id=lic.id)
                    )

        for nombre in PACIENTES:
            if db.scalar(select(Paciente).where(Paciente.nombre == nombre)) is None:
                db.add(Paciente(nombre=nombre))

        db.commit()

    print("Listo. Usuarios: " + ", ".join(u for u, *_ in LICENCIADAS))
    print("Password inicial de todas: cambiar123  <-- cambiala antes de produccion")


if __name__ == "__main__":
    main()
