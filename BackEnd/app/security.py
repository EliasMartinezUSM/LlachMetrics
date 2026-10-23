"""Funciones para proteger contraseñas y firmar tokens de acceso."""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import get_settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Genera un hash Argon2id con una sal aleatoria para la contraseña."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Compara una contraseña con el hash almacenado, incluida su sal."""
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str) -> str:
    """Crea un JWT firmado cuyo asunto identifica al usuario y cuya expiración se configura en minutos."""
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": subject, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
