"""
Generate a realistic synthetic fleet dataset to seed the relational schema
(Vehiculo, Conductor, Neumatico, Viaje, Viaje-Vehiculo).

Each row represents one trip assigned cyclically across the 12-vehicle fleet.
Distances, costs, tire pressures, and tread depth readings follow smooth
stateful cycles per vehicle (gradual pressure loss between maintenance
re-inflations, seasonal fuel/temperature variation, and progressive tread
wear with retreading) so time-series charts display realistic trajectories.
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

RNG = random.Random(42)

N_VEHICLES = 12
TRIPS_PER_VEHICLE = 500
N_TRIPS = N_VEHICLES * TRIPS_PER_VEHICLE
DEFAULT_EMPRESA = "Logistica Sierra"

rows: list[dict[str, object]] = [{} for _ in range(N_TRIPS)]

for v in range(N_VEHICLES):
    base_km = 190.0 + (340.0 - 190.0) * (v / max(1, N_VEHICLES - 1))
    target_psi = 111.5 + (115.5 - 111.5) * (v / max(1, N_VEHICLES - 1))

    current_cold_psi = target_psi
    leak_rate_per_trip = RNG.uniform(0.38, 0.62)

    current_tread = 16.0 - (v % 4) * 1.4
    retreads = 0
    wear_per_km = RNG.uniform(0.00026, 0.00034)
    cracked = False

    for s in range(TRIPS_PER_VEHICLE):
        row_idx = v + s * N_VEHICLES

        # Smooth seasonal & operational demand wave for trip distance
        seasonal_km = 45.0 * math.sin(2.0 * math.pi * s / 90.0 + v * 0.4)
        route_variation = 25.0 * math.cos(2.0 * math.pi * s / 28.0 + v * 0.7)
        noise_km = RNG.gauss(0.0, 18.0)
        dist = min(680.0, max(65.0, base_km + seasonal_km + route_variation + noise_km))
        dist = round(dist, 1)

        # Smooth fuel/operational cost index over time
        fuel_rate = (
            0.84
            + 0.07 * math.sin(2.0 * math.pi * s / 120.0)
            + RNG.gauss(0.0, 0.025)
        )
        fixed_fee = 26.0 + 3.0 * math.sin(2.0 * math.pi * s / 60.0 + v)
        cost = round(max(35.0, dist * fuel_rate + fixed_fee), 2)

        # Stateful tire pressure cycle: gradual air loss between maintenance checks + ambient wave
        ambient_delta = 1.6 * math.sin(2.0 * math.pi * s / 75.0 + v * 0.3)
        start_reading = round(current_cold_psi + ambient_delta + RNG.gauss(0.0, 0.35), 1)
        thermal_gain = 2.2 + (dist / 180.0) * 1.35 + RNG.gauss(0.0, 0.3)
        end_reading = round(start_reading + thermal_gain, 1)

        current_cold_psi -= leak_rate_per_trip + RNG.uniform(-0.08, 0.12)
        if current_cold_psi < 101.5:
            # Preventive maintenance re-inflation back to target cold pressure
            current_cold_psi = target_psi + RNG.uniform(-0.6, 0.8)
            leak_rate_per_trip = RNG.uniform(0.38, 0.62)

        # Stateful tread wear and retreading cycle
        current_tread = max(3.0, current_tread - dist * wear_per_km)
        if not cracked and current_tread < 6.5 and RNG.random() < 0.08:
            cracked = True
        tread_val = round(current_tread, 2)
        crack_val = cracked

        if current_tread <= 3.3:
            if retreads < 3:
                retreads += 1
                current_tread = RNG.uniform(13.8, 14.4)
                cracked = False
            else:
                retreads = 0
                current_tread = RNG.uniform(15.7, 16.3)
                cracked = False
                wear_per_km = RNG.uniform(0.00026, 0.00034)

        rows[row_idx] = {
            "trip_id": row_idx + 1,
            "empresa": DEFAULT_EMPRESA,
            "cost_usd": cost,
            "distance_km": dist,
            "tread_depth_mm": tread_val,
            "has_cracks": crack_val,
            "pressure_start_psi": start_reading,
            "pressure_end_psi": end_reading,
        }

output_path = Path(__file__).resolve().parent / "synthetic.csv"
fieldnames = [
    "trip_id",
    "empresa",
    "cost_usd",
    "distance_km",
    "tread_depth_mm",
    "has_cracks",
    "pressure_start_psi",
    "pressure_end_psi",
]
with output_path.open("w", newline="", encoding="utf-8") as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved {len(rows)} rows to {output_path.name}")
for sample in rows[:5]:
    print(sample)
