"""Esquemas Pydantic para validar solicitudes y serializar respuestas HTTP."""

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Datos validados para registrar una cuenta nueva."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class UserResponse(BaseModel):
    """Datos públicos de usuario; nunca expone el hash de contraseña."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None


class Token(BaseModel):
    """Token Bearer devuelto al iniciar sesión correctamente."""

    access_token: str
    token_type: str = "bearer"


class VehicleMetrics(BaseModel):
    """Indicadores agregados de un vehículo para el panel de flota."""

    patente: str
    modelo: str | None = None
    viaje_actual: int | None = None
    kilometraje: float | None = None
    consumo_total: float | None = None
    profundidad_surcos_media: float | None = None
    kilometros_neumaticos: float | None = None
    neumaticos: int = 0
    neumaticos_agrietados: int = 0
    presion_inicio: float | None = None
    presion_final: float | None = None
    presion_promedio: float | None = None
    recomendacion: str = "Pendiente de análisis"


class TireReading(BaseModel):
    """Campos persistidos de un neumático expuestos al cliente."""

    id: int
    patente: str
    fecha_adquisicion: date | None = None
    cantidad_recauchajes: int | None = None
    eje: int | None = None
    lado: str | None = None
    posicion: str | None = None
    profundidad_surcos: float | None = None
    agrietado: bool | None = None
    kilometros: float | None = None


class PressureSeriesPoint(BaseModel):
    """Lectura de presión final de un vehículo en un viaje."""

    id_viaje: int
    fecha: date | None = None
    patente: str
    presion_final: float | None = None


class DistanceSeriesPoint(BaseModel):
    """Distancia acumulada a nivel de flota y por vehículo."""

    id_viaje: int
    fecha: date | None = None
    patente: str
    kilometros_acumulados: float = 0
    kilometros_acumulados_vehiculo: float = 0


class TreadSeriesPoint(BaseModel):
    """Punto histórico de profundidad de surcos de un neumático."""

    id: int
    fecha: date | None = None
    patente: str
    profundidad_surcos: float | None = None


class TripSeriesPoint(BaseModel):
    """Datos de viaje y presiones asociados a un vehículo."""

    id_viaje: int
    fecha: date | None = None
    kilometros: float | None = None
    costo: float | None = None
    presion_inicio: float | None = None
    presion_final: float | None = None


class FleetTripSeriesPoint(TripSeriesPoint):
    """Punto de viaje que incluye la patente para series de toda la flota."""

    patente: str


class ReadingSummary(BaseModel):
    """Totales y promedios globales usados como resumen de lecturas."""

    kilometros_totales: float = 0
    costo_total: float = 0
    presion_inicio_media: float | None = None
    presion_final_media: float | None = None
    profundidad_surcos_media: float | None = None
    vehiculos: int = 0
    neumaticos: int = 0


class DashboardData(BaseModel):
    """Respuesta combinada del resumen general y métricas por vehículo."""

    summary: ReadingSummary
    vehicles: list[VehicleMetrics]
