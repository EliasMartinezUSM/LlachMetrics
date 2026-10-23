"""Configuración de la API cargada desde variables de entorno o `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de conexión, autenticación y acceso del frontend."""

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # Cookie HttpOnly que transporta el JWT; JavaScript del navegador no puede leerla.
    auth_cookie_name: str = "access_token"
    # Solo se envía por HTTPS. Los navegadores aceptan cookies Secure en http://localhost.
    auth_cookie_secure: bool = True
    # "lax" o "strict" requieren que frontend y API compartan sitio (por ejemplo, mediante
    # el proxy /api de Vite). "none" solo para despliegues cross-site, exige HTTPS.
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"
    )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la lista de orígenes separada por comas en una lista."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia compartida de la configuración del proceso."""
    return Settings()
