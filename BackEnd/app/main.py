from contextlib import asynccontextmanager
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, engine, get_db
from app.deps import get_current_user
from app.models import PasswordHash, Tire, Trip, TripVehicle, User, Vehicle
from app.schemas import (
    DashboardData,
    FleetTripSeriesPoint,
    ReadingSummary,
    Token,
    TripSeriesPoint,
    UserCreate,
    UserResponse,
    VehicleMetrics,
)
from app.security import create_access_token, hash_password, verify_password


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
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


@app.post("/auth/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
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
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)))


@app.get("/auth/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


def _vehicle_metrics(db: Session, patente: str | None = None) -> list[VehicleMetrics]:
    vehicle_query = select(Vehicle)
    tire_query = select(Tire)
    pressure_query = select(TripVehicle, Trip.fecha).join(Trip, Trip.id == TripVehicle.id_viaje)
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
        vehicle_tires = tires_by_vehicle.get(vehicle.patente, [])
        vehicle_pressures = sorted(
            pressures_by_vehicle.get(vehicle.patente, []),
            key=lambda item: item[1] or date.min,
        )
        latest_pressure = vehicle_pressures[-1][0] if vehicle_pressures else None
        tread_values = [t.profundidad_surcos for t in vehicle_tires if t.profundidad_surcos is not None]
        tire_kilometers = [t.kilometros for t in vehicle_tires if t.kilometros is not None]
        result.append(
            VehicleMetrics(
                patente=vehicle.patente,
                modelo=vehicle.modelo,
                kilometraje=vehicle.kilometraje,
                consumo_total=vehicle.consumo_total,
                profundidad_surcos_media=(sum(tread_values) / len(tread_values) if tread_values else None),
                kilometros_neumaticos=sum(tire_kilometers) if tire_kilometers else None,
                neumaticos_agrietados=sum(1 for tire in vehicle_tires if tire.agrietado),
                presion_inicio=latest_pressure.presion_inicio if latest_pressure else None,
                presion_final=latest_pressure.presion_final if latest_pressure else None,
            )
        )
    return result


@app.get("/data/vehicles", response_model=list[VehicleMetrics])
def read_vehicles(db: Annotated[Session, Depends(get_db)]) -> list[VehicleMetrics]:
    try:
        return _vehicle_metrics(db)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/vehicles/{patente}/series", response_model=list[TripSeriesPoint])
def read_vehicle_series(
    patente: str, db: Annotated[Session, Depends(get_db)]
) -> list[TripSeriesPoint]:
    try:
        rows = db.execute(
            select(Trip, TripVehicle)
            .join(TripVehicle, TripVehicle.id_viaje == Trip.id)
            .where(TripVehicle.id_vehiculo == patente)
            .order_by(Trip.fecha, Trip.id)
        ).all()
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
) -> list[FleetTripSeriesPoint]:
    try:
        rows = db.execute(
            select(Trip, TripVehicle)
            .join(TripVehicle, TripVehicle.id_viaje == Trip.id)
            .order_by(Trip.fecha, Trip.id, TripVehicle.id_vehiculo)
        ).all()
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


@app.get("/data/readings", response_model=ReadingSummary)
def read_summary(db: Annotated[Session, Depends(get_db)]) -> ReadingSummary:
    try:
        trip_totals = db.execute(
            select(func.coalesce(func.sum(Trip.kilometros), 0), func.coalesce(func.sum(Trip.costo), 0))
        ).one()
        pressure_averages = db.execute(
            select(func.avg(TripVehicle.presion_inicio), func.avg(TripVehicle.presion_final))
        ).one()
        tread_average = db.scalar(select(func.avg(Tire.profundidad_surcos)))
        return ReadingSummary(
            kilometros_totales=trip_totals[0],
            costo_total=trip_totals[1],
            presion_inicio_media=pressure_averages[0],
            presion_final_media=pressure_averages[1],
            profundidad_surcos_media=tread_average,
            vehiculos=db.scalar(select(func.count(Vehicle.patente))) or 0,
            neumaticos=db.scalar(select(func.count(Tire.id))) or 0,
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible") from None


@app.get("/data/dashboard", response_model=DashboardData)
def read_dashboard(db: Annotated[Session, Depends(get_db)]) -> DashboardData:
    return DashboardData(summary=read_summary(db), vehicles=read_vehicles(db))
