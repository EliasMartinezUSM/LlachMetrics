"""
Generate synthetic CSV files for the full fleet/tire database schema shown
in the ER diagram: Conductor, Vehiculo, Neumatico, Viaje, and
Viaje-Vehiculo (the `user` / `pwd_hash` auth tables are intentionally
skipped - they aren't business data).

This is fully standalone: no SQLAlchemy, no database connection, no
dependency on seed_database.py. It builds the tables in memory with
pandas/numpy, simulating trips in chronological order per vehicle so that
tire wear, cracking, retreading, and eventual replacement produce a
realistic multi-record tire history in neumaticos.csv.

Run:
    python generate_database_csvs.py

Output (in OUTPUT_DIR):
    conductores.csv
    vehiculos.csv
    neumaticos.csv
    viajes.csv
    viaje_vehiculo.csv
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ---- Config ----
SEED = 42
OUTPUT_DIR = Path("./csv_data")  # change this to wherever you want the CSVs written

N_VEHICLES = 12
N_DRIVERS = 8
TRIPS_PER_VEHICLE = 500          # ~500 trips/vehicle -> several retread cycles per tire
N_TRIPS = N_VEHICLES * TRIPS_PER_VEHICLE

TIRE_POSITIONS = (
    (1, "Izquierdo", "Exterior"),
    (1, "Derecho", "Exterior"),
    (2, "Izquierdo", "Interior"),
    (2, "Derecho", "Interior"),
)

# --- Tire life-cycle parameters ---
TREAD_NEW_MM = 16.0
TREAD_RETREAD_MM = 14.0
TREAD_MIN_MM = 3.0
MAX_RECAUCHAJES = 3
WEAR_RATE_RANGE_MM_PER_KM = (0.00005, 0.00009)
CRACK_BASE_PROB = 0.01
CRACK_WEAR_FACTOR = 0.05
RETREAD_ON_CRACK_PROB = 0.3

rng = random.Random(SEED)
np_rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------------
# Tire life-cycle simulator (plain dicts, no ORM / no DB)
# ---------------------------------------------------------------------
class TireLifecycle:
    def __init__(self):
        self._next_id = 1
        self.active: dict[tuple[str, int, str, str], dict] = {}
        self.wear_rate: dict[tuple[str, int, str, str], float] = {}
        self.finished: list[dict] = []  # tires that were fully replaced

    def _new_tire(self, patente: str, eje: int, lado: str, posicion: str, acquired_on: date) -> dict:
        tire = {
            "id": self._next_id,
            "id_vehiculo": patente,
            "fecha_adquisicion": acquired_on,
            "cantidad_recauchajes": 0,
            "profundidad_surcos": round(rng.uniform(TREAD_NEW_MM - 0.5, TREAD_NEW_MM + 0.5), 2),
            "agrietado": False,
            "kilometros": 0.0,
            "eje": eje,
            "lado": lado,
            "posicion": posicion,
        }
        self._next_id += 1
        key = (patente, eje, lado, posicion)
        self.active[key] = tire
        self.wear_rate[key] = rng.uniform(*WEAR_RATE_RANGE_MM_PER_KM)
        return tire

    def ensure_tires(self, patente: str, trip_date: date) -> None:
        """Create the initial 4 tires the first time a vehicle is used."""
        for eje, lado, posicion in TIRE_POSITIONS:
            key = (patente, eje, lado, posicion)
            if key not in self.active:
                acquired_on = trip_date - timedelta(days=rng.randint(30, 400))
                self._new_tire(patente, eje, lado, posicion, acquired_on)

    def apply_wear(self, patente: str, distance_km: float, trip_date: date) -> None:
        for eje, lado, posicion in TIRE_POSITIONS:
            key = (patente, eje, lado, posicion)
            tire = self.active[key]
            rate = self.wear_rate[key]

            tire["kilometros"] += distance_km
            tire["profundidad_surcos"] = max(0.5, tire["profundidad_surcos"] - rate * distance_km)

            wear_fraction = 1 - (tire["profundidad_surcos"] / TREAD_NEW_MM)
            crack_prob = CRACK_BASE_PROB + CRACK_WEAR_FACTOR * wear_fraction
            if not tire["agrietado"] and rng.random() < crack_prob:
                tire["agrietado"] = True

            needs_service = tire["profundidad_surcos"] <= TREAD_MIN_MM or (
                tire["agrietado"] and rng.random() < RETREAD_ON_CRACK_PROB
            )
            if not needs_service:
                continue

            if tire["cantidad_recauchajes"] < MAX_RECAUCHAJES:
                # Recauchaje: se renueva la banda, se conserva la carcasa
                tire["cantidad_recauchajes"] += 1
                tire["profundidad_surcos"] = round(
                    rng.uniform(TREAD_RETREAD_MM - 0.5, TREAD_RETREAD_MM + 0.5), 2
                )
                tire["agrietado"] = False
            else:
                # Baja definitiva: se archiva el neumatico agotado y se compra uno nuevo
                self.finished.append(dict(tire))
                self._new_tire(patente, eje, lado, posicion, trip_date)

    def all_records(self) -> list[dict]:
        """Finished (replaced) tires + whatever is still active at the end."""
        return self.finished + list(self.active.values())


def main() -> None:
    # ---- 1. Conductor ----
    conductores = [{"id": i, "nombre": f"Conductor {i:02d}"} for i in range(1, N_DRIVERS + 1)]

    # ---- 2. Vehiculo (kilometraje/consumo_total accumulate as trips run) ----
    vehiculos: dict[str, dict] = {}
    for i in range(1, N_VEHICLES + 1):
        patente = f"LM-{i:03d}"
        vehiculos[patente] = {
            "patente": patente,
            "modelo": rng.choice(("Volvo FH", "Scania R", "Mercedes Actros")),
            "kilometraje": 0.0,
            "consumo_total": 0.0,
        }
    vehicle_codes = list(vehiculos.keys())

    # ---- Trip-level random variables (vectorized) ----
    distance_km_arr = np.round(np_rng.gamma(shape=3.0, scale=80.0, size=N_TRIPS) + 20, 1)
    distance_km_arr = np.clip(distance_km_arr, 20, 1500)

    cost_per_km_arr = np_rng.normal(loc=0.85, scale=0.12, size=N_TRIPS)
    fixed_overhead_arr = np_rng.normal(loc=25, scale=5, size=N_TRIPS)
    cost_usd_arr = np.round(distance_km_arr * cost_per_km_arr + fixed_overhead_arr, 2)
    cost_usd_arr = np.clip(cost_usd_arr, 10, None)

    pressure_start_arr = np.round(np_rng.normal(loc=110, scale=6, size=N_TRIPS), 1)
    heat_gain_arr = distance_km_arr * np_rng.uniform(0.005, 0.02, size=N_TRIPS)
    minor_leak_arr = np_rng.uniform(0, 1.5, size=N_TRIPS)
    pressure_end_arr = np.round(pressure_start_arr + heat_gain_arr - minor_leak_arr, 1)

    first_date = date.today() - timedelta(days=N_TRIPS)

    # ---- 3, 4, 5. Simulate trips -> Viaje, Viaje-Vehiculo, Neumatico wear ----
    lifecycle = TireLifecycle()
    viajes: list[dict] = []
    viaje_vehiculo: list[dict] = []

    for row_index in range(N_TRIPS):
        patente = vehicle_codes[row_index % len(vehicle_codes)]
        driver_id = conductores[row_index % len(conductores)]["id"]
        trip_date = first_date + timedelta(days=row_index)
        distance_km = float(distance_km_arr[row_index])
        cost_usd = float(cost_usd_arr[row_index])

        trip_id = row_index + 1
        viajes.append({
            "id": trip_id,
            "kilometros": distance_km,
            "costo": cost_usd,
            "fecha": trip_date,
            "conductor": driver_id,
        })
        viaje_vehiculo.append({
            "id_viaje": trip_id,
            "id_vehiculo": patente,
            "presion_inicio": float(pressure_start_arr[row_index]),
            "presion_final": float(pressure_end_arr[row_index]),
        })

        lifecycle.ensure_tires(patente, trip_date)
        lifecycle.apply_wear(patente, distance_km, trip_date)

        vehiculos[patente]["kilometraje"] += distance_km
        vehiculos[patente]["consumo_total"] += cost_usd

    # ---- Build DataFrames and save ----
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df_conductores = pd.DataFrame(conductores)
    df_vehiculos = pd.DataFrame(vehiculos.values())
    df_neumaticos = pd.DataFrame(lifecycle.all_records()).sort_values("id").reset_index(drop=True)
    df_viajes = pd.DataFrame(viajes)
    df_viaje_vehiculo = pd.DataFrame(viaje_vehiculo)

    tables = {
        "conductores.csv": df_conductores,
        "vehiculos.csv": df_vehiculos,
        "neumaticos.csv": df_neumaticos,
        "viajes.csv": df_viajes,
        "viaje_vehiculo.csv": df_viaje_vehiculo,
    }
    for filename, df in tables.items():
        df.to_csv(OUTPUT_DIR / filename, index=False)

    print("Saved:")
    for filename, df in tables.items():
        print(f"  {filename}: {len(df)} rows")


if __name__ == "__main__":
    main()
