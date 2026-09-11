import unittest

from app.main import app
from app.models import Base


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


if __name__ == "__main__":
    unittest.main()