from __future__ import annotations

from uuid import UUID
from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.shared.infrastructure.db.base_model import BaseModel


class ProyectoFavoritoModel(BaseModel, table=True):
    """Modelo SQLModel de la tabla proyectos_favoritos."""

    __tablename__ = "proyectos_favoritos"
    __table_args__ = (
        UniqueConstraint(
            "usuario_id", "proyecto_id", name="uq_proyectos_favoritos_usuario_proyecto"
        ),
    )

    usuario_id: str = Field(foreign_key="user.id", index=True, nullable=False)
    proyecto_id: UUID = Field(foreign_key="proyectos.id", index=True, nullable=False)
