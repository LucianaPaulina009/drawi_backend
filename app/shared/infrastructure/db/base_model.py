import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class BaseModel(SQLModel):
    """
    Modelo base de persistencia para SQLModel.
    Todas las tablas del sistema heredarán de aquí.

    Campos incluidos:
    - id            → UUID v4 generado automáticamente (PK)
    - fecha_creacion      → fecha de creación (UTC con zona horaria)
    - fecha_actualizacion → fecha de última actualización (se actualiza en cada UPDATE)
    - fecha_eliminacion   → fecha de eliminación lógica (nullable)
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fecha_creacion: datetime = Field(
        default_factory=ahora_utc,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    fecha_actualizacion: datetime = Field(
        default_factory=ahora_utc,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"onupdate": ahora_utc},
    )
    fecha_eliminacion: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )

    def eliminar_logicamente(self) -> None:
        """Marca el registro como inactivo y registra la fecha de eliminación."""
        momento_actual = ahora_utc()
        self.fecha_eliminacion = momento_actual
        self.fecha_actualizacion = momento_actual

    def restaurar(self) -> None:
        """Restaura un registro eliminado lógicamente."""
        self.fecha_eliminacion = None
        self.fecha_actualizacion = ahora_utc()
