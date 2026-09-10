"""
Generate a larger synthetic trip dataset to seed the full relational schema
(Vehiculo, Conductor, Neumatico, Viaje, Viaje-Vehiculo).

This produces one row per trip: cost, distance, and tire pressure readings.
Vehicle/driver assignment and tire life-cycle simulation (wear, cracking,
retreading, and eventual replacement) are now handled inside
seed_database.py as it loads this file in chronological order - keeping the
tire life-cycle logic there lets a single physical tire accumulate history
(and multiple recauchajes) across many trips instead of being recreated
from scratch every trip, as the original version did.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(seed=42)

# Match the fleet size seed_database.py creates by default (VEHICLE_COUNT).
N_VEHICLES = 12
TRIPS_PER_VEHICLE = 500  # ~500 trips/vehicle gives each tire several retread cycles
N_TRIPS = N_VEHICLES * TRIPS_PER_VEHICLE

# ---- Core trip variables ----
trip_id = np.arange(1, N_TRIPS + 1)

# Distance per trip (km) - right-skewed: mostly short/medium hauls, some long hauls
distance_km = np.round(RNG.gamma(shape=3.0, scale=80.0, size=N_TRIPS) + 20, 1)
distance_km = np.clip(distance_km, 20, 1500)

# Cost of trip (USD): base rate per km + fuel/toll noise + fixed overhead per trip
cost_per_km = RNG.normal(loc=0.85, scale=0.12, size=N_TRIPS)
fixed_overhead = RNG.normal(loc=25, scale=5, size=N_TRIPS)
cost_usd = np.round(distance_km * cost_per_km + fixed_overhead, 2)
cost_usd = np.clip(cost_usd, 10, None)

# Tire pressure (psi): typical heavy truck tires run ~100-120 psi cold
pressure_start_psi = np.round(RNG.normal(loc=110, scale=6, size=N_TRIPS), 1)
heat_gain = distance_km * RNG.uniform(0.005, 0.02, size=N_TRIPS)
minor_leak = RNG.uniform(0, 1.5, size=N_TRIPS)
pressure_end_psi = np.round(pressure_start_psi + heat_gain - minor_leak, 1)

# tread_depth_mm / has_cracks are kept only for quick exploratory use.
# seed_database.py no longer reads them to populate Neumatico: tire wear,
# cracking, and retreading are simulated there as a stateful process across
# each vehicle's trip history, which is what makes the resulting Neumatico
# table useful for modeling "best moment to retread".
tread_depth_mm = np.round(RNG.uniform(1.5, 18.0, size=N_TRIPS), 2)
crack_prob = np.clip(0.55 - (tread_depth_mm / 18.0) * 0.5, 0.03, 0.6)
has_cracks = RNG.random(N_TRIPS) < crack_prob

df = pd.DataFrame({
    "trip_id": trip_id,
    "cost_usd": cost_usd,
    "distance_km": distance_km,
    "tread_depth_mm": tread_depth_mm,
    "has_cracks": has_cracks,
    "pressure_start_psi": pressure_start_psi,
    "pressure_end_psi": pressure_end_psi,
})

output_path = "synthetic.csv"
df.to_csv(output_path, index=False)
print(f"Saved {len(df)} rows to {output_path}")
print(df.head())
