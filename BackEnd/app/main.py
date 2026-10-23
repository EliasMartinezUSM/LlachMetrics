"""Aplicación FastAPI: autenticación y consulta de métricas de la flota."""

from contextlib import asynccontextmanager
from datetime import date, datetime
import logging
import re
from typing import Annotated
import unicodedata

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine, ensure_schema, get_db
from app.deps import get_current_user
from app.models import (
    DEFAULT_COMPANY,
    Driver,
    PasswordHash,
    Tire,
    Trip,
    TripVehicle,
    User,
    Vehicle,
)
from app.schemas import (
    DashboardData,
    DistanceSeriesPoint,
    FleetTripSeriesPoint,
    MeasurementIngestRequest,
    MeasurementIngestResponse,
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


# --- Ingestión de mediciones desde WhatsAPI (OCR) ---
def _normalize_label(text: str) -> str:
    """Convierte una etiqueta a minúsculas sin tildes ni signos extra para comparar claves."""
    decomposed = unicodedata.normalize("NFD", text or "")
    without_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", without_accents.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_float(raw: str | float | int | None) -> float | None:
    """Extrae un número decimal desde cadenas con unidades o formato chileno ($185.000, 112.5 PSI)."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip()
    if not text:
        return None

    match = re.search(r"[-+]?\d[\d.,]*", text)
    if not match:
        return None

    token = match.group(0)
    if "." in token and "," in token:
        if token.rfind(",") > token.rfind("."):
            token = token.replace(".", "").replace(",", ".")
        else:
            token = token.replace(",", "")
    elif re.match(r"^[-+]?\d{1,3}(\.\d{3})+$", token):
        token = token.replace(".", "")
    elif "," in token:
        if re.match(r"^[-+]?\d{1,3}(,\d{3})+$", token):
            token = token.replace(",", "")
        else:
            token = token.replace(",", ".")

    try:
        return float(token)
    except ValueError:
        return None


def _parse_int(raw: str | int | float | None) -> int | None:
    """Extrae un número entero desde cadenas o valores numéricos."""
    val = _parse_float(raw)
    if val is None:
        return None
    return int(round(val))


def _parse_date(raw: date | str | None) -> date:
    """Convierte una fecha en texto (DD/MM/YYYY o YYYY-MM-DD) a date, o usa la fecha actual."""
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", text)
        if match:
            day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if year < 100:
                year += 2000
            try:
                return date(year, month, day)
            except ValueError:
                pass
    return date.today()


def _parse_bool(raw: bool | str | int | None) -> bool | None:
    """Interpreta respuestas de estado binario como Sí/No o Agrietado/Normal."""
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return None
    norm = _normalize_label(str(raw))
    if not norm:
        return None
    if norm in {"si", "yes", "true", "1", "agrietado", "con grietas", "danado", "critico"}:
        return True
    if norm in {"no", "false", "0", "sin grietas", "normal", "bueno", "ok", "operativo"}:
        return False
    if "con grieta" in norm or "agrietad" in norm:
        return True
    if "sin grieta" in norm or norm.startswith("no "):
        return False
    return None


def _parse_axle_location(raw: str) -> tuple[int | None, str | None, str | None]:
    """Descompone expresiones como 'Eje 2 Izquierdo Exterior' en (eje, lado, posicion)."""
    norm = _normalize_label(raw)
    eje_match = re.search(r"\b(\d+)\b", norm)
    eje = int(eje_match.group(1)) if eje_match else None

    lado = None
    if "izquierd" in norm or norm in {"izq", "lh", "l"}:
        lado = "Izquierdo"
    elif "derech" in norm or norm in {"der", "rh", "r"}:
        lado = "Derecho"

    posicion = None
    if "exterior" in norm or "ext" in norm:
        posicion = "Exterior"
    elif "interior" in norm or "int" in norm:
        posicion = "Interior"

    return eje, lado, posicion


def _clean_patente(raw: str | None) -> str | None:
    """Normaliza una patente vehicular eliminando ruido y dejándola en mayúsculas."""
    if not raw:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9-]", "", raw.strip().upper())
    return cleaned or None


def _extract_normalized_payload(payload: MeasurementIngestRequest) -> dict[str, object]:
    """Combina campos estructurados y la lista flexible de pares clave-valor de WhatsAPI."""
    data: dict[str, object] = {
        "empresa": payload.empresa.strip() if payload.empresa else None,
        "patente": _clean_patente(payload.patente),
        "modelo": payload.modelo.strip() if payload.modelo else None,
        "conductor": payload.conductor.strip() if payload.conductor else None,
        "fecha": payload.fecha,
        "kilometraje": _parse_float(payload.kilometraje),
        "consumo_total": _parse_float(payload.consumo_total),
        "distancia_km": _parse_float(payload.distancia_km),
        "costo": _parse_float(payload.costo),
        "presion_inicio": _parse_float(payload.presion_inicio),
        "presion_final": _parse_float(payload.presion_final),
        "serie_neumatico": payload.serie_neumatico.strip() if payload.serie_neumatico else None,
        "id_interno": _parse_int(payload.id_interno),
        "eje": _parse_int(payload.eje),
        "lado": payload.lado.strip().capitalize() if payload.lado else None,
        "posicion": payload.posicion.strip().capitalize() if payload.posicion else None,
        "cantidad_recauchajes": _parse_int(payload.cantidad_recauchajes),
        "profundidad_surcos": _parse_float(payload.profundidad_surcos),
        "agrietado": _parse_bool(payload.agrietado),
        "kilometros_neumatico": _parse_float(payload.kilometros_neumatico),
    }

    for item in payload.campos:
        key = _normalize_label(item.label)
        val = (item.value or "").strip()
        if not key or not val:
            continue

        if any(k in key for k in ("patente", "vehiculo", "placa", "camion", "tracto")):
            if not data["patente"]:
                data["patente"] = _clean_patente(val)
        elif any(k in key for k in ("empresa", "compania", "flota", "cliente")):
            if not data["empresa"]:
                data["empresa"] = val
        elif any(k in key for k in ("modelo", "marca")):
            if not data["modelo"]:
                data["modelo"] = val
        elif any(k in key for k in ("conductor", "chofer", "responsable", "operador")):
            if not data["conductor"]:
                data["conductor"] = val
        elif "fecha" in key:
            if not data["fecha"]:
                data["fecha"] = val
        elif any(k in key for k in ("kilometros neumatico", "km neumatico", "recorrido neumatico")):
            if data["kilometros_neumatico"] is None:
                data["kilometros_neumatico"] = _parse_float(val)
        elif any(k in key for k in ("distancia", "km viaje", "kilometros viaje", "recorrido")):
            if data["distancia_km"] is None:
                data["distancia_km"] = _parse_float(val)
        elif any(k in key for k in ("kilometraje", "odometro", "kilometros", "km")):
            if data["kilometraje"] is None:
                data["kilometraje"] = _parse_float(val)
        elif any(k in key for k in ("consumo", "combustible", "litros")):
            if data["consumo_total"] is None:
                data["consumo_total"] = _parse_float(val)
        elif any(k in key for k in ("costo", "monto", "total", "valor", "importe", "precio")):
            if data["costo"] is None:
                data["costo"] = _parse_float(val)
        elif any(
            k in key
            for k in ("presion inicial", "presion inicio", "psi inicial", "presion entrada")
        ):
            if data["presion_inicio"] is None:
                data["presion_inicio"] = _parse_float(val)
        elif any(
            k in key for k in ("presion final", "presion salida", "psi final", "presion")
        ):
            if data["presion_final"] is None:
                data["presion_final"] = _parse_float(val)
        elif any(k in key for k in ("serie", "dot", "codigo neumatico")):
            if not data["serie_neumatico"]:
                data["serie_neumatico"] = val
        elif any(k in key for k in ("id interno", "codigo interno", "nro interno", "numero interno")):
            if data["id_interno"] is None:
                data["id_interno"] = _parse_int(val)
        elif any(k in key for k in ("eje", "posicion", "ubicacion", "rueda", "lado")):
            eje_val, lado_val, pos_val = _parse_axle_location(val)
            if data["eje"] is None and eje_val is not None:
                data["eje"] = eje_val
            if not data["lado"] and lado_val:
                data["lado"] = lado_val
            if not data["posicion"] and pos_val:
                data["posicion"] = pos_val
        elif "recauchaje" in key:
            if data["cantidad_recauchajes"] is None:
                data["cantidad_recauchajes"] = _parse_int(val)
        elif any(k in key for k in ("profundidad", "surco", "huella", "dibujo")):
            if data["profundidad_surcos"] is None:
                data["profundidad_surcos"] = _parse_float(val)
        elif any(k in key for k in ("agrietado", "grieta", "dano")):
            if data["agrietado"] is None:
                data["agrietado"] = _parse_bool(val)

    return data


@app.post(
    "/data/measurements",
    response_model=MeasurementIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
@app.post(
    "/data/ingest",
    response_model=MeasurementIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_measurements(
    payload: MeasurementIngestRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> MeasurementIngestResponse:
    """Registra o actualiza mediciones de vehículo, viaje y neumático extraídas desde WhatsAPI."""
    parsed = _extract_normalized_payload(payload)
    patente = parsed["patente"]
    if not isinstance(patente, str) or not patente:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "No se encontró la patente del vehículo en los campos configurados. "
                "Agrega o corrige el campo 'Patente' antes de ingresar los datos."
            ),
        )

    user_company = _user_company(current_user)
    empresa = (
        user_company
        or (str(parsed["empresa"]).strip() if parsed["empresa"] else "")
        or DEFAULT_COMPANY
    )
    fecha_medicion = _parse_date(parsed["fecha"])  # type: ignore[arg-type]

    modelo = str(parsed["modelo"]).strip() if parsed["modelo"] else None
    conductor_nombre = str(parsed["conductor"]).strip() if parsed["conductor"] else None
    kilometraje = parsed["kilometraje"] if isinstance(parsed["kilometraje"], float) else None
    consumo_total = parsed["consumo_total"] if isinstance(parsed["consumo_total"], float) else None
    distancia_km = parsed["distancia_km"] if isinstance(parsed["distancia_km"], float) else None
    costo = parsed["costo"] if isinstance(parsed["costo"], float) else None
    presion_inicio = (
        parsed["presion_inicio"] if isinstance(parsed["presion_inicio"], float) else None
    )
    presion_final = parsed["presion_final"] if isinstance(parsed["presion_final"], float) else None
    serie_neumatico = str(parsed["serie_neumatico"]).strip() if parsed["serie_neumatico"] else None
    id_interno = parsed["id_interno"] if isinstance(parsed["id_interno"], int) else None
    eje = parsed["eje"] if isinstance(parsed["eje"], int) else None
    lado = str(parsed["lado"]) if parsed["lado"] else None
    posicion = str(parsed["posicion"]) if parsed["posicion"] else None
    cantidad_recauchajes = (
        parsed["cantidad_recauchajes"] if isinstance(parsed["cantidad_recauchajes"], int) else None
    )
    profundidad_surcos = (
        parsed["profundidad_surcos"] if isinstance(parsed["profundidad_surcos"], float) else None
    )
    agrietado = parsed["agrietado"] if isinstance(parsed["agrietado"], bool) else None
    kilometros_neumatico = (
        parsed["kilometros_neumatico"]
        if isinstance(parsed["kilometros_neumatico"], float)
        else None
    )

    try:
        # 1. Crear o actualizar el Vehículo
        vehicle = db.get(Vehicle, patente)
        vehiculo_creado = False
        previous_km = float(vehicle.kilometraje) if vehicle and vehicle.kilometraje is not None else None

        if vehicle is None:
            vehiculo_creado = True
            vehicle = Vehicle(
                patente=patente,
                empresa=empresa,
                modelo=modelo or "Unidad en ruta",
                kilometraje=kilometraje if kilometraje is not None else (distancia_km or 0.0),
                consumo_total=consumo_total if consumo_total is not None else 0.0,
            )
            db.add(vehicle)
        else:
            if modelo:
                vehicle.modelo = modelo
            if not vehicle.empresa:
                vehicle.empresa = empresa
            if kilometraje is not None:
                vehicle.kilometraje = kilometraje
            elif distancia_km is not None and previous_km is not None:
                vehicle.kilometraje = round(previous_km + distancia_km, 2)
            if consumo_total is not None:
                vehicle.consumo_total = consumo_total

        db.flush()
        effective_company = vehicle.empresa or empresa

        # 2. Crear o recuperar el Conductor si viene especificado
        driver_id: int | None = None
        if conductor_nombre:
            existing_driver = db.scalar(
                select(Driver).where(
                    func.lower(Driver.nombre) == conductor_nombre.lower(),
                    Driver.empresa == effective_company,
                )
            )
            if existing_driver is None:
                existing_driver = Driver(nombre=conductor_nombre, empresa=effective_company)
                db.add(existing_driver)
                db.flush()
            driver_id = existing_driver.id

        # 3. Registrar Viaje y Viaje-Vehiculo si hay datos de viaje o presiones
        has_trip_data = any(
            v is not None
            for v in (
                presion_inicio,
                presion_final,
                distancia_km,
                costo,
                kilometraje,
                driver_id,
            )
        )
        created_trip_id: int | None = None
        if has_trip_data:
            if distancia_km is not None:
                trip_km = distancia_km
            elif (
                kilometraje is not None
                and previous_km is not None
                and kilometraje > previous_km
            ):
                trip_km = round(kilometraje - previous_km, 2)
            else:
                trip_km = kilometraje

            if presion_inicio is not None and presion_final is None:
                presion_final = presion_inicio
            elif presion_final is not None and presion_inicio is None:
                presion_inicio = presion_final

            trip = Trip(
                kilometros=trip_km,
                costo=costo,
                fecha=fecha_medicion,
                conductor=driver_id,
            )
            db.add(trip)
            db.flush()
            created_trip_id = trip.id

            trip_vehicle = TripVehicle(
                id_viaje=trip.id,
                id_vehiculo=vehicle.patente,
                presion_inicio=presion_inicio,
                presion_final=presion_final,
            )
            db.add(trip_vehicle)

        # 4. Registrar lectura de Neumático si el documento incluye métricas de neumático
        has_tire_data = any(
            v is not None
            for v in (
                profundidad_surcos,
                serie_neumatico,
                id_interno,
                cantidad_recauchajes,
                agrietado,
                kilometros_neumatico,
            )
        )
        created_tire_id: int | None = None
        if has_tire_data:
            target_eje = eje if eje is not None and eje > 0 else 1
            target_lado = lado if lado in {"Izquierdo", "Derecho"} else "Izquierdo"
            target_posicion = posicion if posicion in {"Exterior", "Interior"} else "Exterior"

            previous_tire = db.scalar(
                select(Tire)
                .where(
                    Tire.id_vehiculo == vehicle.patente,
                    Tire.eje == target_eje,
                    Tire.lado == target_lado,
                    Tire.posicion == target_posicion,
                )
                .order_by(Tire.fecha_adquisicion.desc(), Tire.id.desc())
            )

            resolved_id_interno = id_interno
            if resolved_id_interno is not None:
                resolved_id_interno = max(0, min(99999, resolved_id_interno))
            elif previous_tire and previous_tire.id_interno is not None:
                resolved_id_interno = previous_tire.id_interno
            else:
                max_internal = db.scalar(select(func.max(Tire.id_interno))) or 10000
                resolved_id_interno = min(99999, int(max_internal) + 1)

            resolved_serie = (
                serie_neumatico
                or (previous_tire.serie if previous_tire else None)
                or f"NEU-{vehicle.patente}-{resolved_id_interno}"
            )
            resolved_recauchajes = (
                cantidad_recauchajes
                if cantidad_recauchajes is not None
                else (
                    previous_tire.cantidad_recauchajes
                    if previous_tire and previous_tire.cantidad_recauchajes is not None
                    else 0
                )
            )
            resolved_tread = (
                profundidad_surcos
                if profundidad_surcos is not None
                else (
                    float(previous_tire.profundidad_surcos)
                    if previous_tire and previous_tire.profundidad_surcos is not None
                    else None
                )
            )
            resolved_cracked = (
                agrietado
                if agrietado is not None
                else (
                    bool(previous_tire.agrietado)
                    if previous_tire and previous_tire.agrietado is not None
                    else False
                )
            )
            resolved_tire_km = (
                kilometros_neumatico
                if kilometros_neumatico is not None
                else (
                    float(vehicle.kilometraje)
                    if vehicle.kilometraje is not None
                    else (
                        float(previous_tire.kilometros)
                        if previous_tire and previous_tire.kilometros is not None
                        else 0.0
                    )
                )
            )

            tire = Tire(
                id_vehiculo=vehicle.patente,
                serie=resolved_serie,
                id_interno=resolved_id_interno,
                empresa=effective_company,
                fecha_adquisicion=fecha_medicion,
                cantidad_recauchajes=resolved_recauchajes,
                profundidad_surcos=resolved_tread,
                agrietado=resolved_cracked,
                kilometros=resolved_tire_km,
                eje=target_eje,
                lado=target_lado,
                posicion=target_posicion,
            )
            db.add(tire)
            db.flush()
            created_tire_id = tire.id

        db.commit()

        resumen: dict[str, str | int | float | bool | None] = {
            "patente": vehicle.patente,
            "empresa": effective_company,
            "modelo": vehicle.modelo,
            "kilometraje": float(vehicle.kilometraje) if vehicle.kilometraje is not None else None,
            "presion_inicio": presion_inicio,
            "presion_final": presion_final,
            "profundidad_surcos": profundidad_surcos,
            "serie_neumatico": serie_neumatico,
            "costo": costo,
        }

        return MeasurementIngestResponse(
            status="ok",
            message=(
                f"Mediciones registradas correctamente para el vehículo {vehicle.patente}."
            ),
            patente=vehicle.patente,
            empresa=effective_company,
            vehiculo_creado=vehiculo_creado,
            id_conductor=driver_id,
            conductor_nombre=conductor_nombre,
            id_viaje=created_trip_id,
            id_neumatico=created_tire_id,
            resumen_mediciones={k: v for k, v in resumen.items() if v is not None},
        )
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de datos no está disponible para guardar las mediciones.",
        ) from None

