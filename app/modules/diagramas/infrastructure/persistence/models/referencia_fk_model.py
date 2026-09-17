from __future__ import annotations

from uuid import UUID

from sqlalchemy import Index, text
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class ReferenciaFKModel(BaseModel, table=True):
    """Modelo SQLModel de persistencia para referencias FK asociadas a una relación."""

    __tablename__ = "referencias_fk"
    __table_args__ = (
        Index("ix_referencias_fk_id_relacion", "id_relacion"),
        Index("ix_referencias_fk_id_atributo_fk", "id_atributo_fk"),
        Index("ix_referencias_fk_id_atributo_ref", "id_atributo_referenciado"),
        Index(
            "uq_referencias_fk_relacion_par_activo",
            "id_relacion",
            "id_atributo_fk",
            "id_atributo_referenciado",
            unique=True,
            sqlite_where=text("fecha_eliminacion IS NULL"),
            postgresql_where=text("fecha_eliminacion IS NULL"),
        ),
    )

    id_relacion: UUID = Field(foreign_key="relaciones.id", nullable=False)
    id_atributo_fk: UUID = Field(foreign_key="atributos.id", nullable=False)
    id_atributo_referenciado: UUID = Field(foreign_key="atributos.id", nullable=False)
    on_delete: str = Field(nullable=False, default="NO_ACTION")
    on_update: str = Field(nullable=False, default="NO_ACTION")
