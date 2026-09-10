"""Populate the business tables from the synthetic trip dataset.

Run from BackEnd with:
    python scripts/seed_database.py

The script reuses a small deterministic pool of vehicles and drivers, and
simulates the full life cycle of each of a vehicle's 4 tires (wear,
cracking, retreading, and eventual replacement) as trips are processed in
chronological order. This produces a Neumatico table with realistic
multi-retread histories instead of a brand-new set of 4 tire rows on every
single trip, which is what the original version did.

By default it appends trips and tire readings; use --reset-business-data to
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

# --- Parametros del ciclo de vida de un neumatico ---
TREAD_NEW_MM = 16.0                    # profundidad de un neumatico nuevo
TREAD_RETREAD_MM = 14.0                # profundidad tras un recauchaje (banda nueva, carcasa usada)
TREAD_MIN_MM = 3.0                     # profundidad minima antes de requerir recauchaje/reemplazo
MAX_RECAUCHAJES = 3                    # recauchajes permitidos antes de dar de baja el neumatico
WEAR_RATE_RANGE_MM_PER_KM = (0.00005, 0.00009)  # desgaste por km, varia por neumatico
CRACK_BASE_PROB = 0.01                 # probabilidad base de agrietamiento por viaje
CRACK_WEAR_FACTOR = 0.05               # probabilidad extra segun desgaste acumulado
RETREAD_ON_CRACK_PROB = 0.3            # prob. de forzar recauchaje si ya esta agrietado


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
        help="Borra viajes, neumaticos, vehiculos y conductores antes de cargar",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semilla para datos inventados")
    return parser.parse_args()


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el CSV: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        # tread_depth_mm / has_cracks ya no son obligatorias: el desgaste de
        # los neumaticos ahora se simula internamente a lo largo del tiempo,
        # en vez de leerse fila a fila desde el CSV.
        required_columns = {"cost_usd", "distance_km", "pressure_start_psi", "pressure_end_psi"}
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


class TireLifecycle:
    """Mantiene en memoria el neumatico activo de cada posicion de cada
    vehiculo y simula su desgaste, agrietamiento, recauchaje y reemplazo a
    medida que se procesan los viajes en orden cronologico.

    - Cada posicion (eje, lado, posicion) de cada vehiculo empieza con un
      neumatico nuevo.
    - Cada viaje desgasta la banda de rodamiento segun la distancia recorrida.
    - Al llegar a la profundidad minima (o, con cierta probabilidad, al
      agrietarse) el neumatico se recauchea: se resetea la profundidad y se
      incrementa `cantidad_recauchajes`.
    - Tras agotar los recauchajes permitidos, el neumatico se da de baja y se
      crea uno nuevo para esa posicion, dejando en la tabla el historial
      completo del neumatico anterior.
    """

    def __init__(self, db, random_generator: random.Random):
        self.db = db
        self.rng = random_generator
        self.active: dict[tuple[str, int, str, str], Tire] = {}
        self.wear_rate: dict[tuple[str, int, str, str], float] = {}

    def _new_tire(self, vehicle: Vehicle, eje: int, lado: str, posicion: str, acquired_on: date) -> Tire:
        tire = Tire(
            id_vehiculo=vehicle.patente,
            fecha_adquisicion=acquired_on,
            cantidad_recauchajes=0,
            profundidad_surcos=round(self.rng.uniform(TREAD_NEW_MM - 0.5, TREAD_NEW_MM + 0.5), 2),
            agrietado=False,
            kilometros=0.0,
            eje=eje,
            lado=lado,
            posicion=posicion,
        )
        self.db.add(tire)
        self.db.flush()
        key = (vehicle.patente, eje, lado, posicion)
        self.active[key] = tire
        self.wear_rate[key] = self.rng.uniform(*WEAR_RATE_RANGE_MM_PER_KM)
        return tire

    def ensure_tires(self, vehicle: Vehicle, trip_date: date) -> None:
        """Crea los 4 neumaticos iniciales de un vehiculo la primera vez que se usa."""
        for eje, lado, posicion in TIRE_POSITIONS:
            key = (vehicle.patente, eje, lado, posicion)
            if key not in self.active:
                # Neumatico comprado entre 30 y 400 dias antes de su primer viaje registrado
                acquired_on = trip_date - timedelta(days=self.rng.randint(30, 400))
                self._new_tire(vehicle, eje, lado, posicion, acquired_on)

    def apply_wear(self, vehicle: Vehicle, distance_km: float, trip_date: date) -> None:
        for eje, lado, posicion in TIRE_POSITIONS:
            key = (vehicle.patente, eje, lado, posicion)
            tire = self.active[key]
            rate = self.wear_rate[key]

            tire.kilometros = float(tire.kilometros or 0) + distance_km
            tire.profundidad_surcos = max(0.5, float(tire.profundidad_surcos) - rate * distance_km)

            wear_fraction = 1 - (tire.profundidad_surcos / TREAD_NEW_MM)
            crack_prob = CRACK_BASE_PROB + CRACK_WEAR_FACTOR * wear_fraction
            if not tire.agrietado and self.rng.random() < crack_prob:
                tire.agrietado = True

            needs_service = tire.profundidad_surcos <= TREAD_MIN_MM or (
                tire.agrietado and self.rng.random() < RETREAD_ON_CRACK_PROB
            )
            if not needs_service:
                continue

            if tire.cantidad_recauchajes < MAX_RECAUCHAJES:
                # Recauchaje: se renueva la banda de rodamiento, se conserva la carcasa
                tire.cantidad_recauchajes += 1
                tire.profundidad_surcos = round(
                    self.rng.uniform(TREAD_RETREAD_MM - 0.5, TREAD_RETREAD_MM + 0.5), 2
                )
                tire.agrietado = False
            else:
                # Baja definitiva: se compra un neumatico nuevo para esa posicion
                self._new_tire(vehicle, eje, lado, posicion, trip_date)


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

    tire_updates = 0
    try:
        with SessionLocal.begin() as db:
            lifecycle = TireLifecycle(db, random_generator)

            first_date = date.today() - timedelta(days=len(rows))
            for row_index, row in enumerate(rows):
                vehicle = db.get(Vehicle, vehicle_codes[row_index % len(vehicle_codes)])
                driver_id = driver_ids[row_index % len(driver_ids)]
                trip_date = first_date + timedelta(days=row_index)
                distance_km = float(row["distance_km"])

                trip = Trip(
                    kilometros=distance_km,
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

                lifecycle.ensure_tires(vehicle, trip_date)
                lifecycle.apply_wear(vehicle, distance_km, trip_date)
                tire_updates += TIRES_PER_VEHICLE

                vehicle.kilometraje = float(vehicle.kilometraje or 0) + distance_km
                vehicle.consumo_total = float(vehicle.consumo_total or 0) + float(row["cost_usd"])
    except (SQLAlchemyError, KeyError, TypeError, ValueError) as error:
        print(
            f"Advertencia: no se cargaron los viajes ni neumaticos ({error}). "
            "Los vehiculos y conductores si fueron conservados."
        )
        return 0, len(vehicle_codes), len(driver_ids), 0

    return len(rows), len(vehicle_codes), len(driver_ids), tire_updates


def main() -> None:
    args = parse_args()
    trips, vehicles, drivers, tire_updates = seed(args.csv, args.reset_business_data, args.seed)
    mode = "reemplazados" if args.reset_business_data else "agregados"
    print(
        f"Carga completada: {trips} viajes {mode}, {tire_updates} actualizaciones de neumaticos "
        f"(desgaste/recauchaje/reemplazo), {vehicles} vehiculos y {drivers} conductores."
    )


if __name__ == "__main__":
    main()
