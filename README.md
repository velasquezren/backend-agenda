# Agenda API

Backend de la agenda de sesiones médicas de Clínica Montalvo. FastAPI + SQLAlchemy,
independiente del CRM (no comparte código ni base de datos).

Frontend: [frontend-agenda](https://github.com/velasquezren/frontend-agenda).

## Correr en local

Por defecto usa SQLite, así que no hace falta MySQL:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python seed.py
```

```bash
.venv/bin/uvicorn main:app --reload --port 8001
```

`seed.py` crea las tablas, 3 médicos, 3 licenciadas (`lic1`, `lic2`, `admin`, con
password `cambiar123`) y unos pacientes de prueba. Es idempotente.

Documentación interactiva del API: <http://127.0.0.1:8001/docs>.

## Pruebas

```bash
.venv/bin/python smoke_test.py
```

27 comprobaciones sobre una SQLite temporal: permiso lic↔médico (403),
no-solapamiento al crear y al mover (409), soft-cancel, series con conflictos, y
que mover una cita de una serie no mueve las demás.

## Reglas duras

Las valida el servidor; el cliente solo las refleja.

1. Una licenciada solo ve y agenda con **sus** médicos (`medico_licenciada`) → si no, **403**.
2. Nunca dos citas encimadas para el mismo médico → **409** con el detalle de la cita en conflicto. Sí se permite agendar fuera del horario de referencia, que es solo orientativo.
3. Mover o editar una cita de una serie afecta **solo esa** fecha.
4. Cancelar es *soft*: `estado='cancelada'`, la fila no se borra. Su hueco vuelve a quedar libre.
5. En una serie, las fechas que chocan se omiten y se devuelven en `conflictos`; el resto sí se crea.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/auth/login` | `{usuario, password}` → `{access_token}`. Todo lo demás pide Bearer. |
| `GET` | `/auth/me` | La licenciada autenticada. |
| `GET` | `/medicos` | Solo los médicos con los que puede agendar. |
| `GET` | `/pacientes?q=` | Búsqueda por nombre. |
| `POST` | `/pacientes` | Alta de paciente. |
| `GET` | `/citas?medico_id=&desde=&hasta=` | Citas del rango, ya en formato FullCalendar. |
| `POST` | `/citas` | Cita suelta. **409** si choca, **403** si el médico no es suyo. |
| `PATCH` | `/citas/{id}` | Mover/editar solo esa cita. **409** si choca. |
| `DELETE` | `/citas/{id}` | Soft-cancel. |
| `POST` | `/series` | Crea la serie y sus citas hijas → `{creadas, conflictos}`. |

## Producción

**Base de datos.** En producción apunta a MySQL con `AGENDA_DATABASE_URL`:

```bash
mysql -u root -p -e "CREATE DATABASE agenda CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
mysql -u root -p agenda < schema_mysql.sql
```

**Variables de entorno** (ver `deploy/agenda-api.service`):

| Variable | Para qué |
|---|---|
| `AGENDA_DATABASE_URL` | `mysql+pymysql://usuario:pass@127.0.0.1:3306/agenda?charset=utf8mb4` |
| `AGENDA_JWT_SECRET` | secreto de firma; mínimo 32 bytes |
| `AGENDA_CORS_ORIGINS` | origen del frontend; vacío si Apache sirve ambos desde el mismo host |

**Servicio.** `deploy/agenda-api.service` levanta uvicorn en `127.0.0.1:8001` bajo
systemd, y `deploy/apache-agenda.conf` es el fragmento de Apache que hace de
reverse proxy de `/agenda-api` → `:8001`.

Antes de desplegar: cambiar `AGENDA_JWT_SECRET` y las passwords `cambiar123` que
deja `seed.py`.

## Decisiones que se desviaron del plan original

- **`PyJWT` + `bcrypt`** en vez de `python-jose` + `passlib`. Los dos del plan
  están sin mantenimiento y `passlib` rompe en Python 3.13+ (importa el módulo
  `crypt`, que se eliminó del stdlib).
- **SQLite por defecto en local** para poder levantar el API sin MySQL instalada.
  Los modelos usan tipos genéricos de SQLAlchemy, así que las mismas tablas valen
  en los dos motores; el DDL específico de MySQL está en `schema_mysql.sql`.

## Fuera de alcance v1

Recordatorios, cobros, notas clínicas, reportes, administración de usuarios y
"mover esta y las siguientes".
