"""Dependencias FastAPI para autenticar peticiones con JWT."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User


# El JWT llega en una cookie HttpOnly; auto_error=False permite responder con un 401 propio.
cookie_scheme = APIKeyCookie(name=get_settings().auth_cookie_name, auto_error=False)


def get_current_user(
    token: Annotated[str | None, Depends(cookie_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Valida el JWT de la cookie de sesión y devuelve el usuario; rechaza tokens inválidos o huérfanos."""
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise credentials_exception
        user_id = int(subject)
    except (InvalidTokenError, ValueError):
        raise credentials_exception from None

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user
