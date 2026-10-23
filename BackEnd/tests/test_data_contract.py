import os
from pathlib import Path
import sys
import unittest
from datetime import date
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-for-production")

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import (
    app,
    ingest_measurements,
    read_summary,
    read_tire_readings,
    read_vehicles,
)
from app.models import Base, Driver, Tire, Trip, TripVehicle, User, Vehicle
from app.schemas import DocumentFieldItem, MeasurementIngestRequest


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
        self.assertIn("/data/measurements", routes)
        self.assertIn("/data/ingest", routes)

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

    def test_ingest_measurements_from_whatsapi_fields_creates_and_updates_records(self) -> None:
        test_engine = create_engine("sqlite://")
        Base.metadata.create_all(bind=test_engine)
        session_factory = sessionmaker(bind=test_engine)

        with session_factory() as db:
            payload = MeasurementIngestRequest(
                documento="inspeccion_neumaticos_ot842.png",
                campos=[
                    DocumentFieldItem(label="Empresa", value="Logistica Sierra"),
                    DocumentFieldItem(label="Fecha", value="22/10/2026"),
                    DocumentFieldItem(label="Patente / Vehículo", value="KRTW-42"),
                    DocumentFieldItem(label="Modelo", value="Volvo FH 500"),
                    DocumentFieldItem(label="Conductor", value="Roberto Soto"),
                    DocumentFieldItem(label="Kilometraje", value="148320 km"),
                    DocumentFieldItem(label="Serie Neumático", value="MICH-88412"),
                    DocumentFieldItem(label="ID Interno", value="40512"),
                    DocumentFieldItem(label="Eje", value="Eje 2 Izquierdo Exterior"),
                    DocumentFieldItem(label="Recauchajes", value="1"),
                    DocumentFieldItem(label="Presión Inicial", value="112.5 PSI"),
                    DocumentFieldItem(label="Presión Final", value="116.2 PSI"),
                    DocumentFieldItem(label="Profundidad Surcos", value="11.4 mm"),
                    DocumentFieldItem(label="Agrietado", value="No"),
                    DocumentFieldItem(label="Costo Total", value="$185.000"),
                ],
            )

            response = ingest_measurements(payload=payload, db=db, current_user=None)

            self.assertEqual(response.status, "ok")
            self.assertEqual(response.patente, "KRTW-42")
            self.assertEqual(response.empresa, "Logistica Sierra")
            self.assertTrue(response.vehiculo_creado)
            self.assertIsNotNone(response.id_conductor)
            self.assertIsNotNone(response.id_viaje)
            self.assertIsNotNone(response.id_neumatico)

            vehicles = read_vehicles(db)
            self.assertEqual(len(vehicles), 1)
            self.assertEqual(vehicles[0].patente, "KRTW-42")
            self.assertEqual(vehicles[0].modelo, "Volvo FH 500")
            self.assertEqual(float(vehicles[0].kilometraje or 0), 148320.0)
            self.assertEqual(float(vehicles[0].presion_inicio or 0), 112.5)
            self.assertEqual(float(vehicles[0].presion_final or 0), 116.2)
            self.assertEqual(float(vehicles[0].profundidad_surcos_media or 0), 11.4)

            tires = read_tire_readings(db)
            self.assertEqual(len(tires), 1)
            self.assertEqual(tires[0].serie, "MICH-88412")
            self.assertEqual(tires[0].id_interno, 40512)
            self.assertEqual(tires[0].eje, 2)
            self.assertEqual(tires[0].lado, "Izquierdo")
            self.assertEqual(tires[0].posicion, "Exterior")
            self.assertFalse(tires[0].agrietado)

            # Segunda lectura para actualizar el mismo vehículo con nuevas mediciones
            update_payload = MeasurementIngestRequest(
                campos=[
                    DocumentFieldItem(label="Patente", value="KRTW-42"),
                    DocumentFieldItem(label="Fecha", value="23/10/2026"),
                    DocumentFieldItem(label="Kilometraje", value="148920 km"),
                    DocumentFieldItem(label="Presión Inicial", value="110.0 PSI"),
                    DocumentFieldItem(label="Presión Final", value="114.0 PSI"),
                    DocumentFieldItem(label="Eje", value="Eje 2 Izquierdo Exterior"),
                    DocumentFieldItem(label="Profundidad Surcos", value="10.8 mm"),
                    DocumentFieldItem(label="Agrietado", value="Sí"),
                ]
            )
            update_res = ingest_measurements(payload=update_payload, db=db, current_user=None)
            self.assertFalse(update_res.vehiculo_creado)

            updated_vehicle = read_vehicles(db)[0]
            self.assertEqual(float(updated_vehicle.kilometraje or 0), 148920.0)
            self.assertEqual(float(updated_vehicle.presion_final or 0), 114.0)
            self.assertEqual(float(updated_vehicle.profundidad_surcos_media or 0), 10.8)
            self.assertEqual(updated_vehicle.neumaticos_agrietados, 1)

        test_engine.dispose()

    def test_ingest_measurements_rejects_missing_patente(self) -> None:
        test_engine = create_engine("sqlite://")
        Base.metadata.create_all(bind=test_engine)
        session_factory = sessionmaker(bind=test_engine)

        with session_factory() as db:
            payload = MeasurementIngestRequest(
                campos=[DocumentFieldItem(label="Fecha", value="22/10/2026")]
            )
            with self.assertRaises(HTTPException) as ctx:
                ingest_measurements(payload=payload, db=db, current_user=None)
            self.assertEqual(ctx.exception.status_code, 422)

        test_engine.dispose()


if __name__ == "__main__":
    unittest.main()
