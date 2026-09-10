"""Populate the business tables from the synthetic trip dataset.

Run from BackEnd with:
    python scripts/seed_database.py

The script reuses a small deterministic pool of vehicles and drivers. By
default it appends trips and tire readings; use --reset-business-data to
replace only the business data while preserving users and password hashes.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models import Driver, Tire, Trip, TripVehicle, Vehicle


VEHICLE_COUNT = 12
DRIVER_COUNT = 8
TIRES_PER_VEHICLE = 4
TIRE_POSITIONS = (
    (1, "Izquierdo", "Exterior"),
    (1, "Derecho", "Exterior"),
    (2, "Izquierdo", "Interior"),
    (2, "Derecho", "Interior"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "synthetic.csv",
        help="Ruta al CSV de viajes (por defecto: ../../synthetic.csv)",
    )
    parser.add_argument(
        "--reset-business-data",
        action="store_true",
        help="Borra viajes, neumáticos, vehículos y conductores antes de cargar",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semilla para datos inventados")
    return parser.parse_args()


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el CSV: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        required_columns = {
            "trip_id",
            "cost_usd",
            "distance_km",
            "tread_depth_mm",
            "has_cracks",
            "pressure_start_psi",
            "pressure_end_psi",
        }
        reader = csv.DictReader(csv_file)
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Faltan columnas requeridas en el CSV: {missing}")
        return list(reader)


def clear_business_data() -> None:
    with SessionLocal.begin() as db:
        db.execute(delete(TripVehicle))
        db.execute(delete(Trip))
        db.execute(delete(Tire))
        db.execute(delete(Vehicle))
        db.execute(delete(Driver))


def get_or_create_fleet(db, random_generator: random.Random) -> tuple[list[Vehicle], list[Driver]]:
    vehicles = list(db.scalars(select(Vehicle).order_by(Vehicle.patente)).all())
    drivers = list(db.scalars(select(Driver).order_by(Driver.id)).all())

    while len(vehicles) < VEHICLE_COUNT:
        index = len(vehicles) + 1
        vehicle = Vehicle(
            patente=f"LM-{index:03d}",
            modelo=random_generator.choice(("Volvo FH", "Scania R", "Mercedes Actros")),
            kilometraje=0,
            consumo_total=0,
        )
        db.add(vehicle)
        vehicles.append(vehicle)

    while len(drivers) < DRIVER_COUNT:
        index = len(drivers) + 1
        driver = Driver(nombre=f"Conductor {index:02d}")
        db.add(driver)
        drivers.append(driver)

    db.flush()
    return vehicles[:VEHICLE_COUNT], drivers[:DRIVER_COUNT]


def add_tires(db, vehicle: Vehicle, row: dict[str, str], trip_date: date) -> None:
    for axle, side, position in TIRE_POSITIONS:
        db.add(
            Tire(
                id_vehiculo=vehicle.patente,
                fecha_adquisicion=trip_date - timedelta(days=180),
                cantidad_recauches=0,
                profundidad_surcos=float(row["tread_depth_mm"]),
                agrietado=row["has_cracks"].strip().lower() == "true",
                kilometros=float(row["distance_km"]),
                eje=axle,
                lado=side,
                posicion=position,
            )
        )


def seed(csv_path: Path, reset: bool, seed_value: int) -> tuple[int, int, int, int]:
    rows = load_rows(csv_path)
    random_generator = random.Random(seed_value)
    Base.metadata.create_all(bind=engine)
    if reset:
        clear_business_data()

    with SessionLocal.begin() as db:
        vehicles, drivers = get_or_create_fleet(db, random_generator)
        vehicle_codes = [vehicle.patente for vehicle in vehicles]
        driver_ids = [driver.id for driver in drivers]

    try:
        with SessionLocal.begin() as db:
            first_date = date.today() - timedelta(days=len(rows))
            for row_index, row in enumerate(rows):
                vehicle = db.get(Vehicle, vehicle_codes[row_index % len(vehicle_codes)])
                driver_id = driver_ids[row_index % len(driver_ids)]
                trip_date = first_date + timedelta(days=row_index)
                trip = Trip(
                    kilometros=float(row["distance_km"]),
                    costo=float(row["cost_usd"]),
                    fecha=trip_date,
                    conductor=driver_id,
                )
                db.add(trip)
                db.flush()
                db.add(
                    TripVehicle(
                        id_viaje=trip.id,
                        id_vehiculo=vehicle.patente,
                        presion_inicio=float(row["pressure_start_psi"]),
                        presion_final=float(row["pressure_end_psi"]),
                    )
                )
                add_tires(db, vehicle, row, trip_date)
                vehicle.kilometraje = float(vehicle.kilometraje or 0) + float(row["distance_km"])
                vehicle.consumo_total = float(vehicle.consumo_total or 0) + float(row["cost_usd"])
    except (SQLAlchemyError, KeyError, TypeError, ValueError) as error:
        print(
            f"Advertencia: no se cargaron los viajes ni neumáticos ({error}). "
            "Los vehículos y conductores sí fueron conservados."
        )
        return 0, len(vehicle_codes), len(driver_ids), 0

    return len(rows), len(vehicle_codes), len(driver_ids), len(rows) * TIRES_PER_VEHICLE


def main() -> None:
    args = parse_args()
    trips, vehicles, drivers, tires = seed(args.csv, args.reset_business_data, args.seed)
    mode = "reemplazados" if args.reset_business_data else "agregados"
    print(
        f"Carga completada: {trips} viajes {mode}, {tires} neumáticos, "
        f"{vehicles} vehículos y {drivers} conductores."
    )


if __name__ == "__main__":
    main()