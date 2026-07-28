"""Prueba de humo del API contra una SQLite temporal.

    .venv/bin/python smoke_test.py

Cubre las reglas duras: permiso lic<->medico, no-solapamiento (409),
soft-cancel y generacion de series con conflictos.
"""

import os
import sys
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["AGENDA_DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

import seed  # noqa: E402
from main import app  # noqa: E402

fallos: list[str] = []


def check(nombre: str, condicion: bool, extra: str = "") -> None:
    marca = "ok  " if condicion else "FALLO"
    print(f"  [{marca}] {nombre}{'  -> ' + extra if extra and not condicion else ''}")
    if not condicion:
        fallos.append(nombre)


seed.main()
c = TestClient(app)

# --- auth ---
r = c.post("/auth/login", json={"usuario": "lic1", "password": "cambiar123"})
check("login correcto", r.status_code == 200, r.text)
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

check(
    "login con password mala -> 401",
    c.post("/auth/login", json={"usuario": "lic1", "password": "x"}).status_code == 401,
)
check("sin token -> 401", c.get("/medicos").status_code == 401)

# Sin esto, el navegador sirve de su cache el GET /citas de siempre y la cita
# recien guardada no aparece hasta recargar la pagina.
check(
    "las respuestas van con Cache-Control: no-store",
    r.headers.get("cache-control") == "no-store",
    str(dict(r.headers)),
)

# --- medicos ---
r = c.get("/medicos", headers=H)
medicos = r.json()
check("lic1 ve solo sus 2 medicos", len(medicos) == 2, str(medicos))
m1 = medicos[0]["id"]
prohibido = next(
    m["id"]
    for m in c.get(
        "/medicos",
        headers={
            "Authorization": "Bearer "
            + c.post(
                "/auth/login", json={"usuario": "admin", "password": "cambiar123"}
            ).json()["access_token"]
        },
    ).json()
    if m["id"] not in {m["id"] for m in medicos}
)

# --- pacientes ---
r = c.post("/pacientes", json={"nombre": "Paciente Prueba"}, headers=H)
check("crear paciente", r.status_code == 201, r.text)
pac = r.json()["id"]
check(
    "buscar paciente por nombre parcial",
    any(p["id"] == pac for p in c.get("/pacientes?q=prueb", headers=H).json()),
)

# --- citas ---
base = {"medico_id": m1, "paciente_id": pac}
r = c.post(
    "/citas",
    json={**base, "inicio": "2026-08-03T09:00:00", "fin": "2026-08-03T10:00:00"},
    headers=H,
)
check("crear cita", r.status_code == 201, r.text)
cita1 = int(r.json()["extendedProps"]["citaId"])
check("evento trae color del medico", r.json()["color"] == medicos[0]["color"])
check("evento trae nombre del paciente", r.json()["title"] == "Paciente Prueba")

r = c.post(
    "/citas",
    json={**base, "inicio": "2026-08-03T09:30:00", "fin": "2026-08-03T10:30:00"},
    headers=H,
)
check("cita encimada -> 409", r.status_code == 409, r.text)

r = c.post(
    "/citas",
    json={**base, "inicio": "2026-08-03T10:00:00", "fin": "2026-08-03T11:00:00"},
    headers=H,
)
check("cita pegada (fin == inicio) si se permite", r.status_code == 201, r.text)
cita2 = int(r.json()["extendedProps"]["citaId"])

r = c.post(
    "/citas",
    json={
        "medico_id": prohibido,
        "paciente_id": pac,
        "inicio": "2026-08-03T15:00:00",
        "fin": "2026-08-03T16:00:00",
    },
    headers=H,
)
check("agendar con medico no permitido -> 403", r.status_code == 403, r.text)

r = c.post(
    "/citas",
    json={**base, "inicio": "2026-08-03T12:00:00", "fin": "2026-08-03T11:00:00"},
    headers=H,
)
check("fin antes que inicio -> 422", r.status_code == 422)

# --- mover ---
r = c.patch(
    f"/citas/{cita1}",
    json={"inicio": "2026-08-03T14:00:00", "fin": "2026-08-03T15:00:00"},
    headers=H,
)
check("mover cita a hueco libre", r.status_code == 200, r.text)

r = c.patch(
    f"/citas/{cita1}",
    json={"inicio": "2026-08-03T10:15:00", "fin": "2026-08-03T11:15:00"},
    headers=H,
)
check("mover cita encima de otra -> 409", r.status_code == 409, r.text)

r = c.patch(f"/citas/{cita1}", json={"notas": "trae estudios"}, headers=H)
check(
    "editar solo notas no dispara falso 409",
    r.status_code == 200 and r.json()["extendedProps"]["notas"] == "trae estudios",
    r.text,
)

# --- soft cancel ---
r = c.delete(f"/citas/{cita2}", headers=H)
check(
    "cancelar es soft",
    r.status_code == 200 and r.json()["extendedProps"]["estado"] == "cancelada",
    r.text,
)
r = c.post(
    "/citas",
    json={**base, "inicio": "2026-08-03T10:00:00", "fin": "2026-08-03T11:00:00"},
    headers=H,
)
check("el hueco de una cancelada queda libre", r.status_code == 201, r.text)

# --- listar ---
r = c.get(
    f"/citas?medico_id={m1}&desde=2026-08-03T00:00:00&hasta=2026-08-04T00:00:00",
    headers=H,
)
eventos = r.json()
check("listar citas del dia", r.status_code == 200 and len(eventos) == 2, r.text)
check(
    "las canceladas no salen por defecto",
    all(e["extendedProps"]["estado"] != "cancelada" for e in eventos),
)
r = c.get(
    f"/citas?medico_id={m1}&desde=2026-08-03T00:00:00"
    "&hasta=2026-08-04T00:00:00&incluir_canceladas=true",
    headers=H,
)
check("incluir_canceladas=true las trae", len(r.json()) == 3, r.text)

# --- series ---
r = c.post(
    "/series",
    json={
        "medico_id": m1,
        "paciente_id": pac,
        "dias_semana": [1, 3, 5],  # lunes, miercoles, viernes
        "hora_inicio": "08:00:00",
        "hora_fin": "09:00:00",
        "fecha_desde": "2026-08-03",  # lunes
        "fecha_hasta": "2026-08-16",  # dos semanas -> 6 fechas
    },
    headers=H,
)
check("crear serie", r.status_code == 201, r.text)
res = r.json()
check(
    "serie genera 6 citas sin conflicto",
    len(res["creadas"]) == 6 and res["conflictos"] == [],
    str(res),
)
check(
    "las citas de la serie llevan serie_id",
    all(e["extendedProps"]["serieId"] == res["serie_id"] for e in res["creadas"]),
)

r = c.post(
    "/series",
    json={
        "medico_id": m1,
        "paciente_id": pac,
        "dias_semana": [1],
        "hora_inicio": "08:30:00",  # choca con la serie anterior
        "hora_fin": "09:30:00",
        "fecha_desde": "2026-08-03",
        "fecha_hasta": "2026-08-16",
    },
    headers=H,
)
res = r.json()
check(
    "serie que choca reporta conflictos y no crea esas fechas",
    r.status_code == 201 and res["creadas"] == [] and len(res["conflictos"]) == 2,
    str(res),
)

r = c.post(
    "/series",
    json={
        "medico_id": m1,
        "paciente_id": pac,
        "dias_semana": [2],  # martes
        "hora_inicio": "08:00:00",
        "hora_fin": "12:00:00",  # 4h: dos martes seguidos no chocan entre si
        "fecha_desde": "2026-09-01",
        "fecha_hasta": "2026-09-15",
    },
    headers=H,
)
check("serie en fechas libres", len(r.json()["creadas"]) == 3, r.text)

# --- domingos: la clinica no atiende ---
r = c.post(
    "/citas",
    json={**base, "inicio": "2026-08-09T10:00:00", "fin": "2026-08-09T11:00:00"},
    headers=H,
)  # 2026-08-09 es domingo
check("cita en domingo -> 422", r.status_code == 422, r.text)

r = c.patch(
    f"/citas/{cita1}",
    json={"inicio": "2026-08-09T10:00:00", "fin": "2026-08-09T11:00:00"},
    headers=H,
)
check("mover una cita a domingo -> 422", r.status_code == 422, r.text)

r = c.post(
    "/series",
    json={
        "medico_id": m1,
        "paciente_id": pac,
        "dias_semana": [5, 7],  # viernes y domingo
        "hora_inicio": "10:00:00",
        "hora_fin": "11:00:00",
        "fecha_desde": "2026-11-02",
        "fecha_hasta": "2026-11-30",
    },
    headers=H,
)
check("serie que incluye domingo -> 422", r.status_code == 422, r.text)

r = c.post(
    "/citas",
    json={**base, "inicio": "2026-08-08T10:00:00", "fin": "2026-08-08T11:00:00"},
    headers=H,
)  # sabado si se atiende
check("el sabado sigue permitido", r.status_code == 201, r.text)

# mover una cita de la serie afecta solo esa
serie = c.post(
    "/series",
    json={
        "medico_id": m1,
        "paciente_id": pac,
        "dias_semana": [4],
        "hora_inicio": "16:00:00",
        "hora_fin": "17:00:00",
        "fecha_desde": "2026-10-01",
        "fecha_hasta": "2026-10-31",
    },
    headers=H,
).json()
hija = int(serie["creadas"][0]["extendedProps"]["citaId"])
c.patch(
    f"/citas/{hija}",
    json={"inicio": "2026-10-01T18:00:00", "fin": "2026-10-01T19:00:00"},
    headers=H,
)
otras = c.get(
    f"/citas?medico_id={m1}&desde=2026-10-01T00:00:00&hasta=2026-11-01T00:00:00",
    headers=H,
).json()
movidas = [e for e in otras if e["start"].endswith("18:00:00")]
sin_mover = [e for e in otras if e["start"].endswith("16:00:00")]
check(
    "mover una cita de la serie no mueve las demas",
    len(movidas) == 1 and len(sin_mover) == len(serie["creadas"]) - 1,
    f"movidas={len(movidas)} sin_mover={len(sin_mover)}",
)

os.unlink(_tmp.name)
print()
if fallos:
    print(f"{len(fallos)} FALLO(S): {fallos}")
    sys.exit(1)
print("Todas las pruebas pasaron.")
