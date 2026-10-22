"""Motor de PostgreSQL, sesiones SQLAlchemy y dependencia para rutas."""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
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


def ensure_schema(target_engine: Engine | None = None) -> None:
    """Crea las tablas e incorpora las columnas nuevas si la base ya existía."""
    active_engine = target_engine or engine
    Base.metadata.create_all(bind=active_engine)
    if active_engine.dialect.name != "postgresql":
        return

    alter_statements = (
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS empresa TEXT DEFAULT \'Logistica Sierra\'',
        'ALTER TABLE "Vehiculo" ADD COLUMN IF NOT EXISTS "Empresa" TEXT DEFAULT \'Logistica Sierra\'',
        'ALTER TABLE "Conductor" ADD COLUMN IF NOT EXISTS "Empresa" TEXT DEFAULT \'Logistica Sierra\'',
        'ALTER TABLE "Neumatico" ADD COLUMN IF NOT EXISTS "Empresa" TEXT DEFAULT \'Logistica Sierra\'',
        'ALTER TABLE "Neumatico" ADD COLUMN IF NOT EXISTS "Serie" TEXT',
        'ALTER TABLE "Neumatico" ADD COLUMN IF NOT EXISTS "id_interno" INTEGER',
        'UPDATE "user" SET empresa = \'Logistica Sierra\' WHERE empresa IS NULL',
        'UPDATE "Vehiculo" SET "Empresa" = \'Logistica Sierra\' WHERE "Empresa" IS NULL',
        'UPDATE "Conductor" SET "Empresa" = \'Logistica Sierra\' WHERE "Empresa" IS NULL',
        'UPDATE "Neumatico" SET "Empresa" = \'Logistica Sierra\' WHERE "Empresa" IS NULL',
        'UPDATE "Neumatico" SET "id_interno" = LEAST(99999, 10000 + id) WHERE "id_interno" IS NULL',
        'UPDATE "Neumatico" SET "Serie" = \'SN-\' || LPAD(id::text, 5, \'0\') WHERE "Serie" IS NULL',
    )
    with active_engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))

