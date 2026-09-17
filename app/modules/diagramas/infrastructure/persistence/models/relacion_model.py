from __future__ import annotations

from uuid import UUID

from sqlalchemy import Index
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class RelacionModel(BaseModel, table=True):
    """Modelo SQLModel de persistencia para relaciones UML en un diagrama."""

    __tablename__ = "relaciones"
    __table_args__ = (
        Index("ix_relaciones_id_diagrama", "id_diagrama"),
        Index("ix_relaciones_id_clase_origen", "id_clase_origen"),
        Index("ix_relaciones_id_clase_destino", "id_clase_destino"),
    )

    id_diagrama: UUID = Field(foreign_key="diagramas.id", nullable=False)
    id_clase_origen: UUID = Field(foreign_key="clases.id", nullable=False)
    id_clase_destino: UUID = Field(foreign_key="clases.id", nullable=False)
    tipo_relacion: str = Field(nullable=False)
    cardinalidad_origen: str = Field(nullable=False)
    cardinalidad_destino: str = Field(nullable=False)
    conector_origen: str = Field(nullable=False)
    conector_destino: str = Field(nullable=False)
