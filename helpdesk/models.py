
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def obtener_fecha_actual():
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="open",
        nullable=False
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=obtener_fecha_actual,
        nullable=False
    )

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=obtener_fecha_actual,
        onupdate=obtener_fecha_actual,
        nullable=False
    )

    # Relacion con prestamos
    prestamos_equipo = relationship(
        "PrestamoEquipo",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )


class PrestamoEquipo(Base):
    __tablename__ = "prestamos_equipo"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id"),
        nullable=False,
        index=True
    )

    etiqueta_equipo: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    receptor: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    devolucion_esperada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    # Estado del prestamo
    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
    )

    # Fecha real de devolucion
    devuelto_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Informacion adicional
    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    condicion_devolucion: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    entregado_por: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    recibido_por: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=obtener_fecha_actual,
        nullable=False
    )

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=obtener_fecha_actual,
        onupdate=obtener_fecha_actual,
        nullable=False
    )

    # Relacion con ticket
    ticket = relationship(
        "Ticket",
        back_populates="prestamos_equipo"
    )

    # Funcion para registrar devolucion
    def registrar_devolucion(
        self,
        recibido_por: str,
        condicion: str = "Buen estado",
        observaciones: str | None = None
    ):
        if not self.activo:
            raise ValueError("Este equipo ya fue devuelto.")

        self.activo = False
        self.devuelto_en = obtener_fecha_actual()
        self.recibido_por = recibido_por.strip()
        self.condicion_devolucion = condicion
        self.observaciones = observaciones
        self.actualizado_en = obtener_fecha_actual()

    # Consultar si el prestamo esta vencido
    @property
    def esta_vencido(self) -> bool:
        if not self.activo:
            return False

        fecha = self.devolucion_esperada

        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)

        return fecha < obtener_fecha_actual()

    # Consultar estado del prestamo
    @property
    def estado(self) -> str:
        if not self.activo:
            return "devuelto"

        if self.esta_vencido:
            return "vencido"

        return "activo"
