"""Create the PostgreSQL database configured in BackEnd/.env.

Run from BackEnd with:
    python scripts/create_database.py

Use --name to create a different database, for example for a temporary test.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.database import ensure_schema
import app.models  # noqa: F401 - registra todas las tablas en Base.metadata


def initialize_database_schema(database_name: str) -> None:
    target_url = make_url(get_settings().database_url).set(database=database_name)
    target_engine = create_engine(
        target_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )
    try:
        ensure_schema(target_engine)
    finally:
        target_engine.dispose()


def create_database(database_name: str | None = None) -> bool:
    configured_url = make_url(get_settings().database_url)
    target_name = database_name or configured_url.database
    if not target_name:
        raise ValueError("La URL de conexión no especifica el nombre de la base de datos.")

    connection_options = {
        "host": configured_url.host,
        "port": configured_url.port,
        "user": configured_url.username,
        "password": configured_url.password,
        "dbname": "postgres",
        **configured_url.query,
    }

    created = False
    with psycopg.connect(**connection_options, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_name,))
            if cursor.fetchone():
                print(f"La base de datos '{target_name}' ya existe.")
            else:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_name)))
                created = True

    initialize_database_schema(target_name)
    if created:
        print(f"Base de datos '{target_name}' creada e inicializada correctamente.")
    else:
        print(f"Esquema de '{target_name}' verificado y actualizado correctamente.")
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        help="Nombre alternativo de la base de datos (por defecto, el de DATABASE_URL)",
    )
    args = parser.parse_args()

    try:
        create_database(args.name)
    except (psycopg.Error, SQLAlchemyError, ValueError) as error:
        print(f"No se pudo crear la base de datos: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())