"""Motor de PostgreSQL, sesiones SQLAlchemy y dependencia para rutas."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


settings = get_settings()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base común para las entidades mapeadas con SQLAlchemy."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Entrega una sesión por petición y la cierra al terminar la respuesta."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
