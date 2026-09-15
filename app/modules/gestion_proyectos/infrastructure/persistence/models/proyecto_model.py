from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class ProyectoModel(BaseModel, table=True):
    """Modelo SQLModel de la tabla proyectos."""

    __tablename__ = "proyectos"
    __table_args__ = (
        UniqueConstraint("propietario_id", "slug", name="uq_proyectos_propietario_slug"),
    )

    propietario_id: str = Field(foreign_key="user.id", index=True, nullable=False)
    nombre: str = Field(max_length=40, nullable=False)
    color: str = Field(default="celeste", nullable=False)
    icono: str = Field(default="caja", nullable=False)
    slug: str = Field(index=True, nullable=False)
