from __future__ import annotations

from uuid import UUID

from app.shared.infrastructure.db.base_model import BaseModel
from sqlalchemy import Index, text
from sqlmodel import Field


class DiagramaModel(BaseModel, table=True):
    """Modelo SQLModel de las páginas internas de un proyecto."""

    __tablename__ = "diagramas"
    __table_args__ = (
        Index("ix_diagramas_id_proyecto", "id_proyecto"),
        Index(
            "uq_diagramas_proyecto_numero_activo",
            "id_proyecto",
            "numero",
            unique=True,
            sqlite_where=text("fecha_eliminacion IS NULL"),
            postgresql_where=text("fecha_eliminacion IS NULL"),
        ),
    )

    id_proyecto: UUID = Field(foreign_key="proyectos.id", nullable=False)
    nombre: str = Field(nullable=False)
    numero: int = Field(nullable=False)
