from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import auth
from config import CORS_ORIGINS, DATABASE_URL
from routers import citas, medicos, pacientes, series

app = FastAPI(title="Agenda API", version="1.0.0")

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
