"""Entidades SQLAlchemy que representan las tablas de la base de datos."""

from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


DEFAULT_COMPANY = "Logistica Sierra"


class User(Base):
    """Cuenta de acceso; la contraseña se mantiene en la relación `PasswordHash`."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    empresa: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=DEFAULT_COMPANY, index=True
    )
    password: Mapped["PasswordHash"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class PasswordHash(Base):
    """Hash de contraseña asociado uno a uno a una cuenta de usuario."""

    __tablename__ = "pwd_hash"

    id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    hash: Mapped[str] = mapped_column(Text)
    user: Mapped[User] = relationship(back_populates="password")


class Vehicle(Base):
    """Vehículo de la flota y sus acumulados de kilometraje y consumo."""

    __tablename__ = "Vehiculo"

    patente: Mapped[str] = mapped_column("Patente", Text, primary_key=True)
    kilometraje: Mapped[float | None] = mapped_column("Kilometraje", Numeric, nullable=True)
    modelo: Mapped[str | None] = mapped_column("Modelo", Text, nullable=True)
    consumo_total: Mapped[float | None] = mapped_column("Consumo total", Numeric, nullable=True)
    empresa: Mapped[str | None] = mapped_column(
        "Empresa", Text, nullable=True, default=DEFAULT_COMPANY, index=True
    )


class Tire(Base):
    """Registro de un neumático, su posición y su estado de uso."""

    __tablename__ = "Neumatico"
    __table_args__ = (
        CheckConstraint(
            '"id_interno" >= 0 AND "id_interno" <= 99999',
            name="ck_neumatico_id_interno_5_digits",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_vehiculo: Mapped[str] = mapped_column(ForeignKey("Vehiculo.Patente"), index=True)
    serie: Mapped[str | None] = mapped_column("Serie", Text, nullable=True)
    id_interno: Mapped[int | None] = mapped_column("id_interno", Integer, nullable=True)
    empresa: Mapped[str | None] = mapped_column(
        "Empresa", Text, nullable=True, default=DEFAULT_COMPANY, index=True
    )
    fecha_adquisicion: Mapped[date | None] = mapped_column("Fecha adquisicion", Date, nullable=True)
    cantidad_recauchajes: Mapped[int | None] = mapped_column("Cantidad recauchajes", Integer, nullable=True, default=0)
    profundidad_surcos: Mapped[float | None] = mapped_column("Profundidad surcos", Numeric, nullable=True)
    agrietado: Mapped[bool | None] = mapped_column("Agrietado", Boolean, nullable=True)
    kilometros: Mapped[float | None] = mapped_column("Kilometros", Numeric, nullable=True)
    eje: Mapped[int | None] = mapped_column("Eje", Integer, nullable=True)
    lado: Mapped[str | None] = mapped_column("Lado", Text, nullable=True)
    posicion: Mapped[str | None] = mapped_column("Posicion", Text, nullable=True)


class Driver(Base):
    """Conductor asociado a los viajes registrados."""

    __tablename__ = "Conductor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str | None] = mapped_column("Nombre", Text, nullable=True)
    empresa: Mapped[str | None] = mapped_column(
        "Empresa", Text, nullable=True, default=DEFAULT_COMPANY, index=True
    )


class Trip(Base):
    """Viaje con distancia, costo, fecha y conductor asociado."""

    __tablename__ = "Viaje"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kilometros: Mapped[float | None] = mapped_column("Kilometros", Numeric, nullable=True)
    costo: Mapped[float | None] = mapped_column("Costo", Numeric, nullable=True)
    fecha: Mapped[date | None] = mapped_column("Fecha", Date, nullable=True)
    conductor: Mapped[int | None] = mapped_column(
        "Conductor", ForeignKey("Conductor.id"), nullable=True
    )


class TripVehicle(Base):
    """Relación entre un viaje y un vehículo, con sus presiones de neumáticos."""

    __tablename__ = "Viaje-Vehiculo"

    id_viaje: Mapped[int] = mapped_column(ForeignKey("Viaje.id"), primary_key=True)
    id_vehiculo: Mapped[str] = mapped_column(
        ForeignKey("Vehiculo.Patente"), primary_key=True
    )
    presion_inicio: Mapped[float | None] = mapped_column("presion inicio", Numeric, nullable=True)
    presion_final: Mapped[float | None] = mapped_column("presion final", Numeric, nullable=True)
