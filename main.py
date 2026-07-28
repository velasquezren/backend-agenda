from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

import auth
from config import CORS_ORIGINS, DATABASE_URL
from routers import citas, medicos, pacientes, series

app = FastAPI(title="Agenda API", version="1.0.0")


@app.middleware("http")
async def sin_cache(request: Request, call_next):
    """Nada de esta API se guarda en cache. Por dos motivos:

    1. La agenda es dato vivo. Sin esta cabecera el navegador puede servir de
       su cache el GET /citas de siempre (misma URL) y la cita recien guardada
       no aparece hasta recargar la pagina.
    2. Son datos de pacientes y van detras de un Bearer por usuario: un CDN o
       proxy intermedio no debe guardar ni reutilizar estas respuestas.
    """
    respuesta = await call_next(request)
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(medicos.router)
app.include_router(pacientes.router)
app.include_router(citas.router)
app.include_router(series.router)


@app.get("/salud", tags=["salud"])
def salud() -> dict[str, str]:
    return {"estado": "ok", "db": DATABASE_URL.split("://", 1)[0]}
