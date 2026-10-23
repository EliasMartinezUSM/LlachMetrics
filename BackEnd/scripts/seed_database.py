"""Populate the business tables from the synthetic trip dataset.

Run from BackEnd with:
    python scripts/seed_database.py

The script reuses a small deterministic pool of vehicles and drivers, and
simulates the full life cycle of each of a vehicle's 4 tires (wear,
cracking, retreading, and eventual replacement) as trips are processed in
chronological order. Periodic tread-depth inspection snapshots are persisted
in the Neumatico table so time-series charts have rich historical trajectories.

By default it appends trips and tire readings; use --reset-business-data to
replace only the business data while preserving users and password hashes.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.database import ensure_schema
from app.models import DEFAULT_COMPANY, Driver, Tire, Trip, TripVehicle, Vehicle


VEHICLE_COUNT = 12
DRIVER_COUNT = 8
TIRES_PER_VEHICLE = 4
TRIPS_PER_DAY = 4
INTERNAL_TIRE_ID_BASE = 10000
TIRE_MANUFACTURER_PREFIXES = ("MICH", "BRID", "CONT", "GOOD", "PIRE")
TIRE_POSITIONS = (
    (1, "Izquierdo", "Exterior"),
    (1, "Derecho", "Exterior"),
    (2, "Izquierdo", "Interior"),
    (2, "Derecho", "Interior"),
)

# --- Parametros del ciclo de vida de un neumatico ---
TREAD_NEW_MM = 16.0                    # profundidad de un neumatico nuevo
TREAD_RETREAD_MM = 14.2                # profundidad tras un recauchaje (banda nueva, carcasa usada)
TREAD_MIN_MM = 3.2                     # profundidad minima antes de requerir recauchaje/reemplazo
MAX_RECAUCHAJES = 3                    # recauchajes permitidos antes de dar de baja el neumatico
WEAR_RATE_RANGE_MM_PER_KM = (0.00028, 0.00035)  # desgaste por km, varia por neumatico
CRACK_TREAD_THRESHOLD_MM = 6.2         # solo se agrieta cuando la banda ya presenta desgaste importante
CRACK_PROB_WHEN_WORN = 0.06            # probabilidad de agrietarse por viaje bajo el umbral


@dataclass
class MountedTireState:
    id_vehiculo: str
    empresa: str
    serie: str
    id_interno: int
    eje: int
    lado: str
    posicion: str
    cantidad_recauchajes: int
    profundidad_surcos: float
    agrietado: bool
    kilometros: float
    wear_rate: float
    trip_step: int = 0
    last_recorded_date: date | None = None


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
    parser.add_argument(
        "--database-name",
        "--name",
        dest="database_name",
        help="Base de datos alternativa a la indicada en DATABASE_URL",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semilla para datos inventados")
    return parser.parse_args()


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el CSV: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        required_columns = {"cost_usd", "distance_km", "pressure_start_psi", "pressure_end_psi"}
        reader = csv.DictReader(csv_file)
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Faltan columnas requeridas en el CSV: {missing}")
        return list(reader)


def clear_business_data(session_factory: sessionmaker) -> None:
    with session_factory.begin() as db:
        db.execute(delete(TripVehicle))
        db.execute(delete(Trip))
        db.execute(delete(Tire))
        db.execute(delete(Vehicle))
        db.execute(delete(Driver))


def get_or_create_fleet(
    db,
    random_generator: random.Random,
    empresa: str = DEFAULT_COMPANY,
) -> tuple[list[Vehicle], list[Driver]]:
    vehicles = list(
        db.scalars(
            select(Vehicle)
            .where(Vehicle.empresa == empresa)
            .order_by(Vehicle.patente)
        ).all()
    )
    drivers = list(
        db.scalars(
            select(Driver)
            .where(Driver.empresa == empresa)
            .order_by(Driver.id)
        ).all()
    )

    while len(vehicles) < VEHICLE_COUNT:
        index = len(vehicles) + 1
        vehicle = Vehicle(
            patente=f"LM-{index:03d}",
            modelo=random_generator.choice(("Volvo FH", "Scania R", "Mercedes Actros")),
            kilometraje=0,
            consumo_total=0,
            empresa=empresa,
        )
        db.add(vehicle)
        vehicles.append(vehicle)

    while len(drivers) < DRIVER_COUNT:
        index = len(drivers) + 1
        driver = Driver(nombre=f"Conductor {index:02d}", empresa=empresa)
        db.add(driver)
        drivers.append(driver)

    db.flush()
    return vehicles[:VEHICLE_COUNT], drivers[:DRIVER_COUNT]


class TireLifecycle:
    """Mantiene en memoria el neumatico activo de cada posicion de cada
    vehiculo y simula su desgaste, agrietamiento, recauchaje y reemplazo a
    medida que se procesan los viajes en orden cronologico, guardando
    mediciones periodicas de profundidad de surcos en la tabla Neumatico.
    """

    def __init__(self, db, random_generator: random.Random, empresa: str = DEFAULT_COMPANY):
        self.db = db
        self.rng = random_generator
        self.empresa = empresa
        self.active: dict[tuple[str, int, str, str], MountedTireState] = {}
        current_max = db.scalar(select(func.max(Tire.id_interno)))
        self.next_internal_id = max(
            INTERNAL_TIRE_ID_BASE + 1,
            (int(current_max) + 1) if current_max is not None else (INTERNAL_TIRE_ID_BASE + 1),
        )
        self.snapshots_recorded = 0

    def _next_internal_number(self) -> int:
        internal_id = min(99999, self.next_internal_id)
        self.next_internal_id += 1
        return internal_id

    def _new_serial_number(self, acquired_on: date, internal_id: int) -> str:
        prefix = self.rng.choice(TIRE_MANUFACTURER_PREFIXES)
        batch_digits = self.rng.randint(1000, 9999)
        return f"{prefix}-{acquired_on.strftime('%Y%m')}-{batch_digits}-{internal_id:05d}"

    def _record_snapshot(self, state: MountedTireState, measured_on: date) -> None:
        if state.last_recorded_date == measured_on:
            return
        state.last_recorded_date = measured_on
        tire_row = Tire(
            id_vehiculo=state.id_vehiculo,
            serie=state.serie,
            id_interno=state.id_interno,
            empresa=state.empresa,
            fecha_adquisicion=measured_on,
            cantidad_recauchajes=state.cantidad_recauchajes,
            profundidad_surcos=round(state.profundidad_surcos, 2),
            agrietado=state.agrietado,
            kilometros=round(state.kilometros, 1),
            eje=state.eje,
            lado=state.lado,
            posicion=state.posicion,
        )
        self.db.add(tire_row)
        self.snapshots_recorded += 1

    def _mount_tire(
        self,
        vehicle: Vehicle,
        eje: int,
        lado: str,
        posicion: str,
        mounted_on: date,
        initial_tread: float | None = None,
        initial_retreads: int = 0,
        wear_rate: float | None = None,
    ) -> MountedTireState:
        internal_id = self._next_internal_number()
        tread = (
            initial_tread
            if initial_tread is not None
            else self.rng.uniform(TREAD_NEW_MM - 0.35, TREAD_NEW_MM + 0.35)
        )
        rate = (
            wear_rate
            if wear_rate is not None
            else self.rng.uniform(*WEAR_RATE_RANGE_MM_PER_KM)
        )
        state = MountedTireState(
            id_vehiculo=vehicle.patente,
            empresa=vehicle.empresa or self.empresa,
            serie=self._new_serial_number(mounted_on, internal_id),
            id_interno=internal_id,
            eje=eje,
            lado=lado,
            posicion=posicion,
            cantidad_recauchajes=initial_retreads,
            profundidad_surcos=round(tread, 2),
            agrietado=False,
            kilometros=0.0,
            wear_rate=rate,
            trip_step=0,
        )
        key = (vehicle.patente, eje, lado, posicion)
        self.active[key] = state
        self._record_snapshot(state, mounted_on)
        return state

    def ensure_tires(self, vehicle: Vehicle, trip_date: date, vehicle_idx: int) -> None:
        """Crea los 4 neumaticos iniciales de un vehiculo desfasando su desgaste inicial."""
        for pos_idx, (eje, lado, posicion) in enumerate(TIRE_POSITIONS):
            key = (vehicle.patente, eje, lado, posicion)
            if key not in self.active:
                # Desfase inicial por posicion y vehiculo para tener curvas distintas
                initial_tread = TREAD_NEW_MM - pos_idx * 1.8 - (vehicle_idx % 3) * 0.45
                # Las primeras 3 posiciones duran todo el horizonte con 2-3 recauchajes;
                # la 4ta posicion parte con 1 recauchaje previo para ejemplificar reemplazos.
                initial_retreads = 1 if pos_idx == 3 else 0
                wear_rate = (
                    self.rng.uniform(0.00028, 0.00032)
                    if pos_idx < 3
                    else self.rng.uniform(0.00033, 0.00036)
                )
                mounted_on = trip_date - timedelta(days=pos_idx + 1)
                self._mount_tire(
                    vehicle,
                    eje,
                    lado,
                    posicion,
                    mounted_on,
                    initial_tread=initial_tread,
                    initial_retreads=initial_retreads,
                    wear_rate=wear_rate,
                )

    def apply_wear(
        self,
        vehicle: Vehicle,
        distance_km: float,
        trip_date: date,
        is_recent_window: bool,
    ) -> None:
        for pos_idx, (eje, lado, posicion) in enumerate(TIRE_POSITIONS):
            key = (vehicle.patente, eje, lado, posicion)
            state = self.active[key]
            state.trip_step += 1

            state.kilometros += distance_km
            jitter = self.rng.uniform(-0.015, 0.015)
            state.profundidad_surcos = max(
                2.5,
                state.profundidad_surcos - state.wear_rate * distance_km + jitter,
            )

            if (
                not state.agrietado
                and state.profundidad_surcos < CRACK_TREAD_THRESHOLD_MM
                and self.rng.random() < CRACK_PROB_WHEN_WORN
            ):
                state.agrietado = True

            needs_service = state.profundidad_surcos <= TREAD_MIN_MM or (
                state.agrietado and state.profundidad_surcos <= 4.2
            )

            if needs_service:
                # Registrar la medicion desgastada justo el dia previo a entrar a taller
                pre_service_date = trip_date - timedelta(days=1)
                self._record_snapshot(state, pre_service_date)

                if state.cantidad_recauchajes < MAX_RECAUCHAJES:
                    state.cantidad_recauchajes += 1
                    state.profundidad_surcos = round(
                        self.rng.uniform(TREAD_RETREAD_MM - 0.35, TREAD_RETREAD_MM + 0.35),
                        2,
                    )
                    state.agrietado = False
                    self._record_snapshot(state, trip_date)
                else:
                    self._mount_tire(vehicle, eje, lado, posicion, trip_date)
                continue

            # Frecuencia de muestreo: cada 2 viajes del vehiculo en ventana reciente
            # (1 medicion cada 6 dias por neumatico), y cada 5 viajes en historial previo.
            sample_interval = 2 if is_recent_window else 5
            if (state.trip_step + pos_idx) % sample_interval == 0:
                self._record_snapshot(state, trip_date)


def seed(
    csv_path: Path,
    reset: bool,
    seed_value: int,
    database_name: str | None = None,
) -> tuple[int, int, int, int]:
    rows = load_rows(csv_path)
    default_empresa = (
        (rows[0].get("empresa") or DEFAULT_COMPANY).strip()
        if rows
        else DEFAULT_COMPANY
    ) or DEFAULT_COMPANY
    random_generator = random.Random(seed_value)
    database_url = make_url(get_settings().database_url)
    if database_name:
        database_url = database_url.set(database=database_name)

    engine = create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        ensure_schema(engine)
        if reset:
            clear_business_data(session_factory)

        with session_factory.begin() as db:
            vehicles, drivers = get_or_create_fleet(db, random_generator, empresa=default_empresa)
            vehicle_codes = [vehicle.patente for vehicle in vehicles]
            driver_ids = [driver.id for driver in drivers]

        tire_updates = 0
        try:
            with session_factory.begin() as db:
                lifecycle = TireLifecycle(db, random_generator, empresa=default_empresa)

                total_days = max(1, (len(rows) - 1) // TRIPS_PER_DAY)
                first_date = date.today() - timedelta(days=total_days)
                recent_cutoff_index = max(0, len(rows) - (480 * TRIPS_PER_DAY))

                for row_index, row in enumerate(rows):
                    row_empresa = (row.get("empresa") or default_empresa).strip() or default_empresa
                    vehicle_idx = row_index % len(vehicle_codes)
                    vehicle = db.get(Vehicle, vehicle_codes[vehicle_idx])
                    if vehicle.empresa is None:
                        vehicle.empresa = row_empresa
                    driver_id = driver_ids[row_index % len(driver_ids)]
                    trip_date = first_date + timedelta(days=row_index // TRIPS_PER_DAY)
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

                    lifecycle.ensure_tires(vehicle, trip_date, vehicle_idx)
                    lifecycle.apply_wear(
                        vehicle,
                        distance_km,
                        trip_date,
                        is_recent_window=(row_index >= recent_cutoff_index),
                    )

                    vehicle.kilometraje = round(float(vehicle.kilometraje or 0) + distance_km, 1)
                    vehicle.consumo_total = round(
                        float(vehicle.consumo_total or 0) + float(row["cost_usd"]),
                        2,
                    )

                tire_updates = lifecycle.snapshots_recorded
        except (SQLAlchemyError, KeyError, TypeError, ValueError) as error:
            print(
                f"Advertencia: no se cargaron los viajes ni neumaticos ({error}). "
                "Los vehiculos y conductores si fueron conservados."
            )
            return 0, len(vehicle_codes), len(driver_ids), 0

        return len(rows), len(vehicle_codes), len(driver_ids), tire_updates
    finally:
        engine.dispose()


def main() -> None:
    args = parse_args()
    trips, vehicles, drivers, tire_updates = seed(
        args.csv,
        args.reset_business_data,
        args.seed,
        args.database_name,
    )
    mode = "reemplazados" if args.reset_business_data else "agregados"
    database_label = f" en '{args.database_name}'" if args.database_name else ""
    print(
        f"Carga completada{database_label}: {trips} viajes {mode}, "
        f"{tire_updates} mediciones de neumaticos registradas, "
        f"{vehicles} vehiculos y {drivers} conductores."
    )


if __name__ == "__main__":
    main()
