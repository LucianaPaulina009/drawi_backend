from __future__ import annotations

from uuid import UUID

from sqlalchemy import Index
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class ClaseModel(BaseModel, table=True):
    """Modelo SQLModel de las clases ubicadas en un diagrama."""

    __tablename__ = "clases"
    __table_args__ = (Index("ix_clases_id_diagrama", "id_diagrama"),)

    id_diagrama: UUID = Field(foreign_key="diagramas.id", nullable=False)
    nombre: str = Field(nullable=False)
    posicion_x: float = Field(nullable=False)
    posicion_y: float = Field(nullable=False)
    ancho: float = Field(nullable=False)
