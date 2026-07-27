from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from db import get_db
from models import Licenciada
from schemas import LicenciadaOut, LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)

# bcrypt solo mira los primeros 72 bytes y revienta si le pasas mas.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode()[:_BCRYPT_MAX_BYTES], bcrypt.gensalt()
    ).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode()[:_BCRYPT_MAX_BYTES], password_hash.encode()
        )
    except ValueError:
        return False


def crear_token(lic: Licenciada) -> str:
    ahora = datetime.now(UTC)
    payload = {
        "sub": str(lic.id),
        "usuario": lic.usuario,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_lic(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> Licenciada:
    no_autorizada = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales invalidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if cred is None:
        raise no_autorizada
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        lic_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise no_autorizada from None

    lic = db.get(Licenciada, lic_id)
    if lic is None or not lic.activo:
        raise no_autorizada
    return lic


LicActual = Annotated[Licenciada, Depends(get_current_lic)]


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, db: Annotated[Session, Depends(get_db)]) -> TokenOut:
    lic = db.scalar(select(Licenciada).where(Licenciada.usuario == datos.usuario))
    if lic is None or not lic.activo or not verify_password(
        datos.password, lic.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
        )
    return TokenOut(access_token=crear_token(lic))


@router.get("/me", response_model=LicenciadaOut)
def me(lic: LicActual) -> Licenciada:
    return lic
