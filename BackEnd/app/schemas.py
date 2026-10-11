from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VehicleMetrics(BaseModel):
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
    id: int
    patente: str
    eje: int | None = None
    lado: str | None = None
    posicion: str | None = None
    profundidad_surcos: float | None = None


class PressureSeriesPoint(BaseModel):
    id_viaje: int
    fecha: date | None = None
    patente: str
    presion_final: float | None = None


class DistanceSeriesPoint(BaseModel):
    id_viaje: int
    fecha: date | None = None
    patente: str
    kilometros_acumulados: float = 0
    kilometros_acumulados_vehiculo: float = 0


class TreadSeriesPoint(BaseModel):
    id: int
    fecha: date | None = None
    patente: str
    profundidad_surcos: float | None = None


class TripSeriesPoint(BaseModel):
    id_viaje: int
    fecha: date | None = None
    kilometros: float | None = None
    costo: float | None = None
    presion_inicio: float | None = None
    presion_final: float | None = None


class FleetTripSeriesPoint(TripSeriesPoint):
    patente: str


class ReadingSummary(BaseModel):
    kilometros_totales: float = 0
    costo_total: float = 0
    presion_inicio_media: float | None = None
    presion_final_media: float | None = None
    profundidad_surcos_media: float | None = None
    vehiculos: int = 0
    neumaticos: int = 0


class DashboardData(BaseModel):
    summary: ReadingSummary
    vehicles: list[VehicleMetrics]
