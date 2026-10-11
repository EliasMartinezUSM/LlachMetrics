import os
import unittest
from datetime import date
from unittest.mock import Mock

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-for-production")

from app.main import app, read_tire_readings
from app.models import Base, Tire


class DataContractTests(unittest.TestCase):
    def test_business_tables_are_mapped(self) -> None:
        expected_tables = {
            "Neumatico",
            "Vehiculo",
            "Viaje-Vehiculo",
            "Viaje",
            "Conductor",
        }

        self.assertTrue(expected_tables.issubset(Base.metadata.tables))

        self.assertEqual(
            set(Base.metadata.tables["Vehiculo"].columns.keys()),
            {"Patente", "Kilometraje", "Modelo", "Consumo total"},
        )
        self.assertEqual(
            set(Base.metadata.tables["Neumatico"].columns.keys()),
            {
                "id",
                "id_vehiculo",
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


if __name__ == "__main__":
    unittest.main()