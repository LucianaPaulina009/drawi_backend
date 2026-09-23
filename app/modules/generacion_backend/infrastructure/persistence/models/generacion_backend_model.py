from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text
from sqlmodel import Field, SQLModel


class GeneracionBackendModel(SQLModel, table=True):
    """Modelo SQLModel de persistencia para metadatos de generaciones de backend."""

    __tablename__ = "generaciones_backend"
    __table_args__ = (
        Index("ix_generaciones_backend_id_diagrama", "id_diagrama"),
        Index("ix_generaciones_backend_id_usuario", "id_usuario"),
        Index("ix_generaciones_backend_fecha_generacion", "fecha_generacion"),
        Index("ix_generaciones_backend_estado", "estado"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    id_diagrama: UUID = Field(foreign_key="diagramas.id", nullable=False)
    id_usuario: str = Field(nullable=False)
    estado: str = Field(nullable=False, default="validando")
    version_plantilla: str = Field(nullable=False, default="1.0.0")
    fecha_generacion: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    detalle_error: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
