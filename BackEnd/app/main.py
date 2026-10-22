"""Aplicación FastAPI: autenticación y consulta de métricas de la flota."""

from contextlib import asynccontextmanager
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine, ensure_schema, get_db
from app.deps import get_current_user
from app.models import DEFAULT_COMPANY, PasswordHash, Tire, Trip, TripVehicle, User, Vehicle
from app.schemas import (
    DashboardData,
    DistanceSeriesPoint,
    FleetTripSeriesPoint,
    PressureSeriesPoint,
    ReadingSummary,
    TireReading,
    TreadSeriesPoint,
    TripSeriesPoint,
    UserCreate,
    UserResponse,
    VehicleMetrics,
)
from app.security import create_access_token, hash_password, verify_password


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Crea las tablas al iniciar; permite arrancar aunque PostgreSQL no responda."""
    try:
        ensure_schema(engine)
    except SQLAlchemyError:
        logger.warning(
            "PostgreSQL no está disponible. La API arrancará, "
            "pero los endpoints que usan la base de datos devolverán 503."
        )
    yield


settings = get_settings()
app = FastAPI(title="LlachMetrics API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Estado del servicio ---
@app.get("/health")
def health_check() -> dict[str, str]:
    """Comprueba que el proceso de la API esté respondiendo."""
    return {"status": "ok"}


# --- Registro e inicio de sesión ---
@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    """Registra un usuario, guarda el hash de su contraseña y devuelve su perfil público."""
    try:
        normalized_email = user_data.email.lower()
        existing_user = db.scalar(select(User).where(User.email == normalized_email))
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado",
            )

        user = User(
            email=normalized_email,
            full_name=user_data.full_name,
            empresa=(user_data.empresa or DEFAULT_COMPANY).strip() or DEFAULT_COMPANY,
        )
        db.add(user)
        db.flush()
        db.add(PasswordHash(id=user.id, hash=hash_password(user_data.password)))
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de datos no está disponible",
        ) from None


@app.post("/auth/login", response_model=UserResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Verifica las credenciales y guarda el JWT en una cookie HttpOnly que JavaScript no puede leer."""
    try:
        user = db.scalar(
            select(User).where(User.email == form_data.username.lower())
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de datos no está disponible",
        ) from None
    if user is None or user.password is None or not verify_password(
        form_data.password, user.password.hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(str(user.id)),
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    return user


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Elimina la cookie de sesión; el navegador no permite borrarla desde JavaScript."""
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


@app.get("/auth/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Devuelve el perfil del usuario autenticado por la dependencia JWT."""
    return current_user


# --- Métricas y series históricas ---
def _user_company(current_user: User | None) -> str | None:
    """Obtiene la empresa del usuario autenticado para aislar los activos visibles."""
    if current_user is None:
        return None
    return (current_user.empresa or DEFAULT_COMPANY).strip() or DEFAULT_COMPANY


def _vehicle_metrics(
    db: Session,
    patente: str | None = None,
    empresa: str | None = None,
) -> list[VehicleMetrics]:
    """Combina vehículos, neumáticos y presiones para calcular indicadores por patente."""
    vehicle_query = select(Vehicle)
    tire_query = select(Tire)
    pressure_query = select(TripVehicle, Trip.fecha).join(Trip, Trip.id == TripVehicle.id_viaje)
    if empresa:
        vehicle_query = vehicle_query.where(Vehicle.empresa == empresa)
        tire_query = tire_query.where(Tire.empresa == empresa)
        pressure_query = pressure_query.join(
            Vehicle, Vehicle.patente == TripVehicle.id_vehiculo
        ).where(Vehicle.empresa == empresa)
    if patente:
        vehicle_query = vehicle_query.where(Vehicle.patente == patente)
        tire_query = tire_query.where(Tire.id_vehiculo == patente)
        pressure_query = pressure_query.where(TripVehicle.id_vehiculo == patente)

    vehicles = db.scalars(vehicle_query).all()
    tires = db.scalars(tire_query).all()
    pressure_rows = db.execute(pressure_query).all()
    tires_by_vehicle: dict[str, list[Tire]] = {}
    for tire in tires:
        tires_by_vehicle.setdefault(tire.id_vehiculo, []).append(tire)
    pressures_by_vehicle: dict[str, list[tuple[TripVehicle, date | None]]] = {}
    for pressure, fecha in pressure_rows:
        pressures_by_vehicle.setdefault(pressure.id_vehiculo, []).append((pressure, fecha))

    result = []
    for vehicle in vehicles:
        vehicle_tires = sorted(
            tires_by_vehicle.get(vehicle.patente, []),
            key=lambda tire: (tire.fecha_adquisicion or date.min, tire.id or 0),
        )
        vehicle_pressures = sorted(
            pressures_by_vehicle.get(vehicle.patente, []),
            key=lambda item: item[1] or date.min,
        )
        latest_pressure = vehicle_pressures[-1][0] if vehicle_pressures else None
        current_tires = {
            (tire.eje, tire.lado, tire.posicion): tire
            for tire in vehicle_tires
        }
        active_tires = list(current_tires.values())
        tread_values = [
            float(t.profundidad_surcos)
            for t in active_tires
            if t.profundidad_surcos is not None
        ]
        tire_kilometers = [
            float(t.kilometros)
            for t in active_tires
            if t.kilometros is not None
        ]
        pressure_values = [
            float(pressure_value)
            for pressure, _ in vehicle_pressures
            for pressure_value in (pressure.presion_inicio, pressure.presion_final)
            if pressure_value is not None
        ]
        result.append(
            VehicleMetrics(
                patente=vehicle.patente,
                empresa=vehicle.empresa,
                modelo=vehicle.modelo,
                viaje_actual=latest_pressure.id_viaje if latest_pressure else None,
                kilometraje=vehicle.kilometraje,
                consumo_total=vehicle.consumo_total,
                profundidad_surcos_media=(
                    round(sum(tread_values) / len(tread_values), 2)
                    if tread_values
                    else None
                ),
                kilometros_neumaticos=(
                    round(sum(tire_kilometers), 1)
                    if tire_kilometers
                    else None
                ),
                neumaticos=len(active_tires),
                neumaticos_agrietados=sum(1 for tire in active_tires if tire.agrietado),
                presion_inicio=latest_pressure.presion_inicio if latest_pressure else None,
                presion_final=latest_pressure.presion_final if latest_pressure else None,
                presion_promedio=(
                    round(sum(pressure_values) / len(pressure_values), 2)
                    if pressure_values
                    else None
                ),
            )
        )
    return result


@app.get("/data/vehicles", response_model=list[VehicleMetrics])
def read_vehicles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> list[VehicleMetrics]:
    """Lista las métricas agregadas de todos los vehículos registrados de la empresa del usuario."""
    try:
        return _vehicle_metrics(db, empresa=_user_company(current_user))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/vehicles/{patente}/series", response_model=list[TripSeriesPoint])
def read_vehicle_series(
    patente: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> list[TripSeriesPoint]:
    """Devuelve los viajes y presiones ordenados cronológicamente para una patente."""
    try:
        empresa = _user_company(current_user)
        query = (
            select(Trip, TripVehicle)
            .join(TripVehicle, TripVehicle.id_viaje == Trip.id)
            .where(TripVehicle.id_vehiculo == patente)
        )
        if empresa:
            query = query.join(Vehicle, Vehicle.patente == TripVehicle.id_vehiculo).where(
                Vehicle.empresa == empresa
            )
        rows = db.execute(query.order_by(Trip.fecha, Trip.id)).all()
        return [
            TripSeriesPoint(
                id_viaje=trip.id,
                fecha=trip.fecha,
                kilometros=trip.kilometros,
                costo=trip.costo,
                presion_inicio=trip_vehicle.presion_inicio,
                presion_final=trip_vehicle.presion_final,
            )
            for trip, trip_vehicle in rows
        ]
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/trips", response_model=list[FleetTripSeriesPoint])
def read_fleet_series(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> list[FleetTripSeriesPoint]:
    """Devuelve los viajes de todos los vehículos para construir series de flota."""
    try:
        empresa = _user_company(current_user)
        query = select(Trip, TripVehicle).join(TripVehicle, TripVehicle.id_viaje == Trip.id)
        if empresa:
            query = query.join(Vehicle, Vehicle.patente == TripVehicle.id_vehiculo).where(
                Vehicle.empresa == empresa
            )
        rows = db.execute(query.order_by(Trip.fecha, Trip.id, TripVehicle.id_vehiculo)).all()
        return [
            FleetTripSeriesPoint(
                patente=trip_vehicle.id_vehiculo,
                id_viaje=trip.id,
                fecha=trip.fecha,
                kilometros=trip.kilometros,
                costo=trip.costo,
                presion_inicio=trip_vehicle.presion_inicio,
                presion_final=trip_vehicle.presion_final,
            )
            for trip, trip_vehicle in rows
        ]
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/pressure-series", response_model=list[PressureSeriesPoint])
def read_pressure_series(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> list[PressureSeriesPoint]:
    """Devuelve las lecturas de presión final existentes, ordenadas por fecha y viaje."""
    try:
        empresa = _user_company(current_user)
        query = (
            select(Trip, TripVehicle)
            .join(TripVehicle, TripVehicle.id_viaje == Trip.id)
            .where(TripVehicle.presion_final.is_not(None))
        )
        if empresa:
            query = query.join(Vehicle, Vehicle.patente == TripVehicle.id_vehiculo).where(
                Vehicle.empresa == empresa
            )
        rows = db.execute(query.order_by(Trip.fecha, Trip.id, TripVehicle.id_vehiculo)).all()
        return [
            PressureSeriesPoint(
                id_viaje=trip.id,
                fecha=trip.fecha,
                patente=trip_vehicle.id_vehiculo,
                presion_final=trip_vehicle.presion_final,
            )
            for trip, trip_vehicle in rows
        ]
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/distance-series", response_model=list[DistanceSeriesPoint])
def read_distance_series(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> list[DistanceSeriesPoint]:
    """Calcula acumulados cronológicos de distancia para la flota y cada vehículo."""
    try:
        empresa = _user_company(current_user)
        query = (
            select(Trip, TripVehicle)
            .join(TripVehicle, TripVehicle.id_viaje == Trip.id)
            .where(Trip.kilometros.is_not(None))
        )
        if empresa:
            query = query.join(Vehicle, Vehicle.patente == TripVehicle.id_vehiculo).where(
                Vehicle.empresa == empresa
            )
        rows = db.execute(query.order_by(Trip.fecha, Trip.id, TripVehicle.id_vehiculo)).all()
        fleet_total = 0.0
        vehicle_totals: dict[str, float] = {}
        result = []
        for trip, trip_vehicle in rows:
            patente = trip_vehicle.id_vehiculo
            distance = float(trip.kilometros or 0)
            fleet_total += distance
            vehicle_totals[patente] = vehicle_totals.get(patente, 0) + distance
            result.append(
                DistanceSeriesPoint(
                    id_viaje=trip.id,
                    fecha=trip.fecha,
                    patente=patente,
                    kilometros_acumulados=fleet_total,
                    kilometros_acumulados_vehiculo=vehicle_totals[patente],
                )
            )
        return result
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/tread-series", response_model=list[TreadSeriesPoint])
def read_tread_series(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> list[TreadSeriesPoint]:
    """Devuelve la profundidad de surcos registrada por neumático y fecha de adquisición."""
    try:
        empresa = _user_company(current_user)
        query = select(Tire)
        if empresa:
            query = query.where(Tire.empresa == empresa)
        tires = db.scalars(query.order_by(Tire.fecha_adquisicion, Tire.id)).all()
        return [
            TreadSeriesPoint(
                id=tire.id,
                fecha=tire.fecha_adquisicion,
                patente=tire.id_vehiculo,
                profundidad_surcos=tire.profundidad_surcos,
            )
            for tire in tires
        ]
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/tires", response_model=list[TireReading])
def read_tire_readings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> list[TireReading]:
    """Expone los datos persistidos de cada neumático para filtros y tablas del frontend."""
    try:
        empresa = _user_company(current_user)
        query = select(Tire)
        if empresa:
            query = query.where(Tire.empresa == empresa)
        tires = db.scalars(
            query.order_by(
                Tire.id_vehiculo,
                Tire.eje,
                Tire.lado,
                Tire.posicion,
                Tire.fecha_adquisicion,
                Tire.id,
            )
        ).all()
        return [
            TireReading(
                id=tire.id,
                id_interno=tire.id_interno,
                serie=tire.serie,
                empresa=tire.empresa,
                patente=tire.id_vehiculo,
                fecha_adquisicion=tire.fecha_adquisicion,
                cantidad_recauchajes=tire.cantidad_recauchajes,
                eje=tire.eje,
                lado=tire.lado,
                posicion=tire.posicion,
                profundidad_surcos=tire.profundidad_surcos,
                agrietado=tire.agrietado,
                kilometros=tire.kilometros,
            )
            for tire in tires
        ]
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/readings", response_model=ReadingSummary)
def read_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> ReadingSummary:
    """Calcula totales y promedios globales de viajes, presiones y neumáticos."""
    try:
        empresa = _user_company(current_user)
        trip_query = select(
            func.coalesce(func.sum(Trip.kilometros), 0),
            func.coalesce(func.sum(Trip.costo), 0),
        )
        pressure_query = select(
            func.avg(TripVehicle.presion_inicio),
            func.avg(TripVehicle.presion_final),
        )
        tread_query = select(func.avg(Tire.profundidad_surcos))
        vehicle_count_query = select(func.count(Vehicle.patente))
        distinct_tire_count_query = select(func.count(func.distinct(Tire.id_interno)))
        tire_count_query = select(func.count(Tire.id))

        if empresa:
            trip_query = (
                trip_query.join(TripVehicle, TripVehicle.id_viaje == Trip.id)
                .join(Vehicle, Vehicle.patente == TripVehicle.id_vehiculo)
                .where(Vehicle.empresa == empresa)
            )
            pressure_query = (
                pressure_query.join(Vehicle, Vehicle.patente == TripVehicle.id_vehiculo)
                .where(Vehicle.empresa == empresa)
            )
            tread_query = tread_query.where(Tire.empresa == empresa)
            vehicle_count_query = vehicle_count_query.where(Vehicle.empresa == empresa)
            distinct_tire_count_query = distinct_tire_count_query.where(Tire.empresa == empresa)
            tire_count_query = tire_count_query.where(Tire.empresa == empresa)

        trip_totals = db.execute(trip_query).one()
        pressure_averages = db.execute(pressure_query).one()
        tread_average = db.scalar(tread_query)
        distinct_tire_count = db.scalar(distinct_tire_count_query) or 0
        return ReadingSummary(
            kilometros_totales=trip_totals[0],
            costo_total=trip_totals[1],
            presion_inicio_media=pressure_averages[0],
            presion_final_media=pressure_averages[1],
            profundidad_surcos_media=tread_average,
            vehiculos=db.scalar(vehicle_count_query) or 0,
            neumaticos=distinct_tire_count or (db.scalar(tire_count_query) or 0),
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/dashboard", response_model=DashboardData)
def read_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> DashboardData:
    """Agrupa el resumen global y las métricas por vehículo en una respuesta."""
    return DashboardData(
        summary=read_summary(db, current_user),
        vehicles=read_vehicles(db, current_user),
    )
