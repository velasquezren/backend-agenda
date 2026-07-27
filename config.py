import os

# En produccion: mysql+pymysql://usuario:password@127.0.0.1:3306/agenda?charset=utf8mb4
# Por defecto usa SQLite para poder levantar el API en local sin MySQL instalada.
DATABASE_URL = os.environ.get("AGENDA_DATABASE_URL", "sqlite:///./agenda_dev.db")

JWT_SECRET = os.environ.get("AGENDA_JWT_SECRET", "cambiame-en-produccion")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("AGENDA_JWT_EXPIRE_MINUTES", "720"))

# Origenes permitidos para el frontend Angular, separados por coma.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "AGENDA_CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
    ).split(",")
    if o.strip()
]
