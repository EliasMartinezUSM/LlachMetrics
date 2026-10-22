import os
from pathlib import Path
import sys
import unittest
from datetime import date
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-for-production")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, read_summary, read_tire_readings, read_vehicles
from app.models import Base, Driver, Tire, Trip, TripVehicle, User, Vehicle


class DataContractTests(unittest.TestCase):
    def test_business_tables_are_mapped(self) -> None:
        expected_tables = {
            "user",
            "Neumatico",
            "Vehiculo",
            "Viaje-Vehiculo",
            "Viaje",
            "Conductor",
        }

        self.assertTrue(expected_tables.issubset(Base.metadata.tables))

        self.assertEqual(
            set(Base.metadata.tables["user"].columns.keys()),
            {"id", "email", "full_name", "empresa"},
        )
        self.assertEqual(
            set(Base.metadata.tables["Vehiculo"].columns.keys()),
            {"Patente", "Kilometraje", "Modelo", "Consumo total", "Empresa"},
        )
        self.assertEqual(
            set(Base.metadata.tables["Conductor"].columns.keys()),
            {"id", "Nombre", "Empresa"},
        )
        self.assertEqual(
            set(Base.metadata.tables["Neumatico"].columns.keys()),
            {
                "id",
                "id_vehiculo",
                "Serie",
                "id_interno",
                "Empresa",
                "Fecha adquisicion",
                "Cantidad recauchajes",
                "Profundidad surcos",
                "Agrietado",
                "Kilometros",
                "Eje",
                "Lado",
                "Posicion",
            },
        )
        self.assertEqual(
            set(Base.metadata.tables["Viaje"].columns.keys()),
            {"id", "Kilometros", "Costo", "Fecha", "Conductor"},
        )
        self.assertEqual(
            set(Base.metadata.tables["Viaje-Vehiculo"].columns.keys()),
            {"id_viaje", "id_vehiculo", "presion inicio", "presion final"},
        )

    def test_data_routes_are_registered(self) -> None:
        routes = {route.path for route in app.routes}

        self.assertIn("/data/dashboard", routes)
        self.assertIn("/data/readings", routes)
        self.assertIn("/data/vehicles", routes)
        self.assertIn("/data/trips", routes)
        self.assertIn("/data/tires", routes)
        self.assertIn("/data/pressure-series", routes)
        self.assertIn("/data/distance-series", routes)
        self.assertIn("/data/tread-series", routes)
        self.assertIn("/data/vehicles/{patente}/series", routes)

    def test_tire_endpoint_returns_all_persisted_tire_fields(self) -> None:
        tire = Tire(
            id=1,
            id_interno=10001,
            serie="MICH-202501-4821-10001",
            empresa="Logistica Sierra",
            id_vehiculo="LM-001",
            fecha_adquisicion=date(2025, 1, 15),
            cantidad_recauchajes=2,
            profundidad_surcos=8.5,
            agrietado=True,
            kilometros=12500,
            eje=1,
            lado="Izquierdo",
            posicion="Exterior",
        )
        db = Mock()
        db.scalars.return_value.all.return_value = [tire]

        result = read_tire_readings(db)[0]

        self.assertEqual(
            result.model_dump(),
            {
                "id": 1,
                "id_interno": 10001,
                "serie": "MICH-202501-4821-10001",
                "empresa": "Logistica Sierra",
                "patente": "LM-001",
                "fecha_adquisicion": date(2025, 1, 15),
                "cantidad_recauchajes": 2,
                "eje": 1,
                "lado": "Izquierdo",
                "posicion": "Exterior",
                "profundidad_surcos": 8.5,
                "agrietado": True,
                "kilometros": 12500,
            },
        )

    def test_company_isolation_filters_vehicles_tires_and_summary(self) -> None:
        test_engine = create_engine("sqlite://")
        Base.metadata.create_all(bind=test_engine)
        session_factory = sessionmaker(bind=test_engine)

        with session_factory() as db:
            db.add_all(
                [
                    Vehicle(
                        patente="LM-001",
                        modelo="Volvo FH",
                        kilometraje=1000,
                        consumo_total=450,
                        empresa="Logistica Sierra",
                    ),
                    Vehicle(
                        patente="OT-999",
                        modelo="Scania R",
                        kilometraje=2000,
                        consumo_total=900,
                        empresa="Transporte Norte",
                    ),
                    Driver(id=1, nombre="Conductor 01", empresa="Logistica Sierra"),
                    Driver(id=2, nombre="Conductor 02", empresa="Transporte Norte"),
                    Tire(
                        id=1,
                        id_vehiculo="LM-001",
                        serie="MICH-202501-1111-10001",
                        id_interno=10001,
                        empresa="Logistica Sierra",
                        profundidad_surcos=12.0,
                    ),
                    Tire(
                        id=2,
                        id_vehiculo="OT-999",
                        serie="BRID-202501-2222-20001",
                        id_interno=20001,
                        empresa="Transporte Norte",
                        profundidad_surcos=9.0,
                    ),
                    Trip(id=1, kilometros=300, costo=150, fecha=date(2025, 2, 1), conductor=1),
                    Trip(id=2, kilometros=700, costo=350, fecha=date(2025, 2, 2), conductor=2),
                    TripVehicle(id_viaje=1, id_vehiculo="LM-001", presion_inicio=100, presion_final=98),
                    TripVehicle(id_viaje=2, id_vehiculo="OT-999", presion_inicio=110, presion_final=108),
                ]
            )
            db.commit()

            sierra_user = User(id=1, email="op@sierra.cl", empresa="Logistica Sierra")
            norte_user = User(id=2, email="op@norte.cl", empresa="Transporte Norte")

            sierra_vehicles = read_vehicles(db, sierra_user)
            norte_vehicles = read_vehicles(db, norte_user)
            sierra_tires = read_tire_readings(db, sierra_user)
            sierra_summary = read_summary(db, sierra_user)

            self.assertEqual([v.patente for v in sierra_vehicles], ["LM-001"])
            self.assertEqual([v.patente for v in norte_vehicles], ["OT-999"])
            self.assertEqual([t.id_interno for t in sierra_tires], [10001])
            self.assertEqual(sierra_summary.vehiculos, 1)
            self.assertEqual(sierra_summary.neumaticos, 1)
            self.assertEqual(float(sierra_summary.kilometros_totales), 300.0)

        test_engine.dispose()


if __name__ == "__main__":
    unittest.main()